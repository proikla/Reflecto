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
from handlers.scheduling import router as scheduling_router

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
    dp.include_router(scheduling_router)
    # lowest priority goes to journal.
    dp.include_router(journal_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
