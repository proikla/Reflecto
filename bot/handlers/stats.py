# stdlib
from datetime import datetime, timedelta, time
import io
import logging

import loguru

# third-party
from scipy.interpolate import PchipInterpolator
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from aiogram.types import Message
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# local
from util.db import db_client
from util.inline_keyboards import *


router = Router()
logger = loguru.logger


@router.message(Command("stats"))
async def stats_command_handler(message: Message) -> None:
    """
    /stats: fetch all (timestamp, mood) rows for this user, interpolate via PCHIP
    (for smoothing)

    User is able to specify amount of days to pull stats from: /stats <days> or /stats <month/year/all>
    """

    params = message.text.split()

    # if no parameters are specified
    if len(params) < 2:
        range_days = 0

    # todo: make this work lol
    elif params[1].isnumeric():
        range_days = int(params[1])
    else:
        match params[1].lower():
            case "all":
                range_days = 0
            case "month":
                range_days = 31
            case "year":
                range_days = 365

    await message.answer("Here are your mood stats:")

    sql = """
    SELECT entry->>'mood' AS mood,
           created_ts AS ts
    FROM entries 
    WHERE entry IS NOT NULL
      AND entry ? 'mood'
      AND user_id = %s
    """

    utc_offset_result = await db_client.fetch_field(
        "users", "utc_offset", where_value=message.from_user.id
    )
    result = await db_client.exec(sql, (message.from_user.id,))

    # if range is either not set or set to "all"
    if not range_days:
        range_days = len(result)

    # Build list of (datetime.datetime, float) and sort:
    raw_data = []
    count = 0
    for mood, dt in result:
        if count >= range_days:
            break

        raw_data.append((dt + timedelta(hours=utc_offset_result), float(mood)))
        count += 1

    raw_data.sort(key=lambda x: x[0])  # sort by full timestamp

    if not raw_data:
        await message.answer("No mood entries found.")
        return

    # Extract arrays of raw timestamps and moods:
    x_datetimes = [dt for dt, _ in raw_data]
    y_moods = [m for _, m in raw_data]

    # Convert to “seconds since epoch” for interpolation:
    x_numeric = np.array([dt.timestamp() for dt in x_datetimes])
    y_numeric = np.array(y_moods, dtype=float)

    # Build a dense 300‐point grid between min and max timestamp:
    x_smooth = np.linspace(x_numeric.min(), x_numeric.max(), 300)
    pchip = PchipInterpolator(x_numeric, y_numeric)
    y_smooth = np.clip(pchip(x_smooth), 0, 10)

    # Convert the “smooth” seconds back to datetime for plotting:
    x_smooth_dt = [datetime.fromtimestamp(ts) for ts in x_smooth]

    # * Construct “every‐other‐day” tick list
    # We want ticks at midnight on every 2nd day between start_date and end_date.
    start_date = raw_data[0][0].date()
    end_date = raw_data[-1][0].date()

    tick_dates: list[datetime] = []
    curr = start_date
    days = timedelta(days=1)
    while curr <= end_date:
        # place the tick at midnight of that day
        tick_dates.append(datetime.combine(curr, time()))
        curr += days

    # * Plotting
    # todo: fix plotting when specifying the amount of days to /stats.
    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot the smoothed curve
    ax.plot(x_smooth_dt, y_smooth, linewidth=2, label="Interpolation")
    # Also overlay the raw points (optional—but helps see exact entries)
    ax.scatter(x_datetimes, y_moods, color="black", s=10, zorder=5, label="Entries")

    ax.set_title("Mood Over Time", fontsize=14)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Mood", fontsize=12)

    ax.set_ylim(0, 10)
    ax.set_yticks(np.arange(0, 11, 1))
    ax.grid(True, linestyle="--", alpha=0.5)

    # Force ticks at every-other‐day midnight
    ax.set_xticks(tick_dates)
    # Format those ticks as MM/DD (you can add hours if desired, e.g. '%m/%d %H:%M')
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))

    fig.autofmt_xdate(rotation=45, ha="right")
    ax.legend()

    plt.tight_layout()

    # Save to buffer & send
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)

    await message.reply_photo(BufferedInputFile(buffer.read(), "photo.png"))
