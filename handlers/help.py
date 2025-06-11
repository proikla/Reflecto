# stdlib
import logging

# third-party
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import Command

# local
logger = logging.getLogger(__name__)

router = Router()


# ? /about maybe
@router.message(Command("help"))
async def help_handler(message: Message, state: FSMContext):
    description = f"""
<b>Reflecto</b> is your personal AI assistant that helps you reflect efficiently while tracking your productivity.
Here's a couple of things Reflecto can do:
- help you make plans for today in the morning
- provide a conveinient and safe way to reflect
- make sure you stay focused by reminding you to write entries
- track your productivity and mood (/stats)
- automatic daily summary generation at the end of the day
"""

    await message.answer(description)
