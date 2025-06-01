# stdlib
import datetime
import logging
import asyncio
import os
import random
import sys
import matplotlib.pyplot as plt
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# third-party
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# local
import APIKEYS
from util.db import db_client
from handlers.settings import router as settings_router
from handlers.start import router as start_router
from handlers.journal import router as journal_router
from handlers.stats import router as stats_router
from handlers.summary import router as summary_router

logger = logging.getLogger(__name__)
dp = Dispatcher()
TOKEN = APIKEYS.token


bot = Bot(token=TOKEN, default=DefaultBotProperties(
    parse_mode=ParseMode.HTML))


commands = [
    BotCommand(command='start', description='Get started'),
    BotCommand(command='settings', description='Configure the bot'),
    BotCommand(command='stats', description='get your mood stats'),
    BotCommand(command='summary', description='Make a summary of your day.')
]

scheduler = AsyncIOScheduler()


def next_midnight():
    return datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=1), datetime.time.min)


DEFAULT_RU_REMINDERS = ['Пожалуйста, сделайте запись.',
                        'Не забудь сделать запись!', 'Я жду запись от тебя ;)', 'Сделаешь запись? Ты мне сказал тебе надо напоминать каждые {i} часа.']


async def send_msg(user_id):
    "Send user a reminder message."
    #TODO: do not send messages in user DND hours.


    res = await db_client.exec("SELECT next_message, interval_hours FROM users WHERE user_id = %s", (user_id,))
    next_message, interval = res[0]
    if next_message == 'DEFAULT':
        text = random.choice(DEFAULT_RU_REMINDERS).format(i=interval)
    else:
        # todo
        # update to default again, but send this custom reminder.
        ...

    await bot.send_message(user_id, text)


@dp.startup()
async def on_startup():
    "set up user reminders on startup"
    scheduler.start()
    users = await db_client.exec(f"SELECT user_id, interval_hours FROM users")
    for user, interval in users:
        scheduler.add_job(send_msg, IntervalTrigger(hours=interval), args=[
                          user])
        logger.info(f"{user}, {interval}")


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    # register commands
    await bot.set_my_commands(commands)

    # And the run events dispatching
    await db_client.init()
    # highest priority goes to commands.
    dp.include_router(settings_router)
    dp.include_router(start_router)
    dp.include_router(stats_router)
    dp.include_router(summary_router)
    # lowest priority goes to journal.
    dp.include_router(journal_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
