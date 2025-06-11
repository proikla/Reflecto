import asyncio
import logging
import random
from APIKEYS import TOKEN
from handlers.summary import get_user_summary

# from util.constants import DEFAULT_RU_REMINDERS
from util.constants import SERVER_UTC_OFFSET
from util.db import db_client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from datetime import UTC, datetime, timedelta

from util.llm_tasks import make_day_summary, prompt_deepseek
from aiogram import F, Bot, Router

router = Router()
scheduler = AsyncIOScheduler()

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
logger = logging.getLogger(__name__)


async def send_msg(user_id, summary=False, is_morning_message=False):
    """
    Send scheduled message to user.

    Params:
        user_id (int):
        summary (bool): True if the message is a summary. Forcefully generates user summary, sends it to the user.

    """

    if summary:
        text = await get_user_summary(user_id, force=True)
        await bot.send_message(user_id, f"{text[0]}")
        return

    user_data = await db_client.exec(
        "SELECT next_message, interval_hours, dnd_hours, utc_offset, custom_reminders, json_context FROM users WHERE user_id = %s",  # test TODO
        (user_id,),
        fetchall=False,
    )
    next_message, interval, dnd_hours, utc_offset, usr_reminders, context = user_data

    if is_morning_message:  # todo: get usr context working.
        # im assuming context is in JSON format #!
        loop = asyncio.get_event_loop()
        morning_message_future = loop.run_in_executor(None, prompt_deepseek, context)

        try:
            text = await morning_message_future
        except Exception as e:
            logger.exception(
                f"Caught exception '{e}' on morning message scheduled sending."
            )
        await bot.send_message(user_id, text)
        return
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
        text = random.choice(usr_reminders).format(i=interval)
    else:  # llm has generated next message based on context TODO
        await bot.send_message(user_id, next_message)
        await db_client.update_field(
            "users", "next_message", "DEFAULT", "user_id", user_id
        )
        ...

    await bot.send_message(user_id, text)


@router.startup()
async def on_startup():

    # * "set up user reminders on startup"
    scheduler.start()
    users_data = await db_client.exec(
        f"SELECT user_id, interval_hours, summary_at_hour, utc_offset, allow_morning_messages FROM users"
    )
    for id, interval, summary_hour, usr_utc_offset, allow_mm in users_data:
        # * schedule reminders
        scheduler.add_job(
            send_msg,
            IntervalTrigger(hours=interval),
            args=[id],
            id=str(id),
        )

        # * evening auto summary
        if summary_hour:
            scheduler.add_job(
                send_msg,
                CronTrigger(hour=summary_hour + SERVER_UTC_OFFSET),
                [id, True],
                id=f"S{id}",
            )
            logger.info(f"Summary scheduled for {id} at {summary_hour} UTC")

        # * schedule morning message
        if allow_mm != 0:
            if allow_mm == 24:
                allow_mm = 0
            scheduler.add_job(
                send_msg,
                CronTrigger(hour=allow_mm + SERVER_UTC_OFFSET),
                [id, False, True],
                id=f"M{id}",
            )
