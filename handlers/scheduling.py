import logging
import random
from APIKEYS import TOKEN
from util.constants import DEFAULT_RU_REMINDERS
from util.db import db_client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from datetime import UTC, datetime, timedelta

from aiogram import F, Bot, Router

router = Router()
scheduler = AsyncIOScheduler()

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
logger = logging.getLogger(__name__)


async def send_msg(user_id):
    "Send user a reminder message."

    res = await db_client.exec(
        "SELECT next_message, interval_hours, dnd_hours, utc_offset FROM users WHERE user_id = %s",
        (user_id,),
    )
    next_message, interval, dnd_hours, utc_offset = res[0]

    # prevent sending messages at DND hours.
    if dnd_hours:
        # dnd_hours = str(dnd_hours)
        logger.info(f"{dnd_hours=}")
        dnd_from, dnd_to = [
            int(i) for i in str(dnd_hours).split("-")
        ]  # get user dnd hours
        current_hour = int(
            (datetime.now(UTC) + timedelta(hours=utc_offset)).strftime("%H")
        )

        # if current hour is in range of user's DND hours:
        if dnd_to > current_hour or current_hour > dnd_from:
            return

    # pick message to send for a user as a reminder.
    if next_message == "DEFAULT":
        text = random.choice(DEFAULT_RU_REMINDERS).format(i=interval)
    else:
        # if not default, it means LLM set it. [TODO]
        # update to default again, but send this custom reminder.
        ...

    await bot.send_message(user_id, text)


@router.startup()
async def on_startup():
    "set up user reminders on startup"
    scheduler.start()
    users = await db_client.exec(f"SELECT user_id, interval_hours FROM users")
    for user, interval in users:
        scheduler.add_job(
            send_msg,
            IntervalTrigger(hours=interval),
            args=[user],
            id=str(user),
        )
        logger.info(f"{user}, {interval}")
