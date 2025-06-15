# stdlib
import logging
from datetime import UTC, datetime, timedelta
import calendar

# third-party
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# local
from util.db import db_client
from util.inline_keyboards import settings_firsttime_kb
from util.states import UserStates
from util.constants import messages_to_delete
from util.misc import delete_misc_messages

logger = logging.getLogger(__name__)


router = Router()


def format_entries(entries: list):
    logger.info(f"FORMATING: {entries=}")
    if entries:
        return f"{''.join([f"{entry[1]}\n{entry[0]}\n\n"  for entry in entries])}"

    return f"No entries found!"


async def get_entries_at_date(year: int, month: int, day: int, user_id: int):
    year, month, day, user_id = map(int, (year, month, day, user_id))
    timestamp = datetime(year, month, day)
    sql = """
SELECT entry->>'entry', created_ts::time FROM entries WHERE user_id = %s AND created_ts::date = %s;
"""
    logger.info(f"GETTING ENTRIES AT {year,month,day, user_id} with {timestamp}")
    return await db_client.exec(sql, (user_id, timestamp))


async def get_inline_calendar_markup(message: Message, month, year):  #! make it async!!
    weekday, num_days = calendar.monthrange(int(year), int(month))
    days_keyboard = [
        [
            InlineKeyboardButton(
                text=str(day),
                callback_data=f"{year}/{month}/{day}/{message.message_id}",
            )
            for day in range(row, row + 8 if row + 8 < num_days + 1 else num_days + 1)
        ]
        for row in range(1, num_days + 1, 8)
    ]
    builder = InlineKeyboardBuilder(days_keyboard).row(
        InlineKeyboardButton(
            text="<", callback_data=f"{year}/{month}/32/{message.message_id}"
        ),
        InlineKeyboardButton(
            text=f"{month}/{year}",
            callback_data=f"{year}/{month}/33/{message.message_id}",
        ),
        InlineKeyboardButton(
            text=">", callback_data=f"{year}/{month}/34/{message.message_id}"
        ),
    )
    return builder.as_markup()


@router.message(Command("entries"))
async def entries_command_handler(message: Message, state: FSMContext):
    """
    Handle /entries command, send interactive inline keyboard to choose entry OR wait for user to type the date instead.
    """
    usr_utc_offset = await db_client.fetch_field(
        field="utc_offset", where_value=message.from_user.id
    )

    day, year, month = (
        (datetime.now(UTC) + timedelta(hours=usr_utc_offset))
        .strftime("%d:%Y:%m")
        .split(":")
    )

    await state.set_state(UserStates.choosing_entry)  #!

    await message.answer(
        f"Choose date or write it yourself like this: {day}/{month}/{year}",
        reply_markup=await get_inline_calendar_markup(message, month, year),
    )


@router.message(F.text.regexp(r"\d{2}/\d{2}/(?:\d{2}|\d{4})$"))
async def handle_date_message(message: Message, state: FSMContext):
    "If the user has used /entries command and is writing date themselves."

    if (
        await state.get_state() == "UserStates:choosing_entry"
    ):  # ? maybe i dont need this state check at all.
        await message.answer("You wrote a date!")
        day, month, year = message.text.split("/")
        if len(year) == 2:
            year = "20" + year

        entries = await get_entries_at_date(year, month, day, message.from_user.id)
        """
        entries[0] - entry text
        entries[1] - entry time
        """
        logger.info(f"{entries=}")
        await message.answer(format_entries(entries))
        # await state.clear()
    else:
        await message.answer("You wrote a date but youre not choosing an entry.")


@router.callback_query(
    F.data.regexp(r"\d+/\d+/\d+/\d+")
)  # ? maybe add message.id to callback so i can change the message.
async def handle_callback(callback: CallbackQuery, state: FSMContext):
    "Called when user presses buttons."

    if not callback.data:
        return

    # delete junk messages: #? maybe not delete but change it
    await delete_misc_messages(callback.message, callback.from_user.id)

    data = callback.data.split("/")
    year, month, day, message_id = map(int, data)
    if day == 32:  # BACK button "<"
        if month - 1 < 1:
            month = 12
            year -= 1
        else:
            month -= 1

        await callback.message.edit_reply_markup(
            str(message_id),
            await get_inline_calendar_markup(callback.message, month, year),
        )

    elif day == 34:  # FORWARD button ">"
        if month + 1 > 12:
            month = 1
            year += 1
        else:
            month += 1

        await callback.message.edit_reply_markup(
            str(message_id),
            await get_inline_calendar_markup(callback.message, month, year),
        )

    else:
        entries = await get_entries_at_date(year, month, day, callback.from_user.id)
        messages_to_delete[callback.from_user.id].append(
            await callback.message.answer(format_entries(entries))
        )

    await callback.answer()
