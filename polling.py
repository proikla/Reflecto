# stdlib
import logging
import asyncio
import os
import sys

# third-party
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# local
import APIKEYS
from util.db import db_client
from util.log import get_logger
from handlers.settings.settings import router as settings_router
from handlers.start import router as start_router
from handlers.journal import router as journal_router
from handlers.stats import router as stats_router
from handlers.summary import router as summary_router
from handlers.scheduling import router as scheduling_router
from handlers.help import router as help_router
from handlers.entries import router as entries_router
from handlers.settings.callbacks import router as settings_callback_router
from handlers.settings.fsm import router as settings_fsm_router

logger = get_logger(__name__)
dp = Dispatcher()
TOKEN = APIKEYS.token


bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


commands = [
    BotCommand(command="start", description="get started."),
    BotCommand(command="settings", description="configure the bot."),
    BotCommand(command="stats", description="get your mood stats."),
    BotCommand(command="summary", description="make a summary of your day."),
    BotCommand(command="help", description="learn what can you do with Reflecto."),
    BotCommand(command="entries", description="view your entries"),
]
#! HUGE REFACTOR!! PLEASE!! ALL OF IT!!!

# todo add "random" or "adaptive" interval.
# todo add option to remove reminders at all
# todo add time of reminder in context. If next_message is going to be generated, it will take into account the time that the message will be generated on.
# todo weekday routine tasks:

"""
Things that are always planned to a certain day.
i.e:
Monday - gym (-> Morning OR next_message be smth like: "are you at the gym already?")
Tuesday - singing
Wednesday - None
...
"""
# todo: Once a week (or during the summary) gather all data from a specific weekday and analyze it to confirm the pattern (^) or not.
# todo rework deleting misc messages
# todo: add "processed" tag to an entry. Will be useful when entries are proccessed in a bunch.
# todo: fix negative values in summary_at_hour #!
# todo: refactor
# todo: inline kb when choosing hours in /settings


async def main() -> None:
    # register commands
    await bot.set_my_commands(commands)

    # And the run events dispatching
    await db_client.init()
    # highest priority goes to commands.
    dp.include_router(settings_fsm_router)
    dp.include_router(settings_callback_router)
    dp.include_router(settings_router)
    dp.include_router(start_router)
    dp.include_router(stats_router)
    dp.include_router(summary_router)
    dp.include_router(scheduling_router)
    dp.include_router(help_router)
    dp.include_router(entries_router)

    # lowest priority goes to journal.
    dp.include_router(journal_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
