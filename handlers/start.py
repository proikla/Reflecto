# third-party
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

# local
from util.db import db_client
from util.constants import messages_to_delete
from util.inline_keyboards import *
from handlers.help import help_handler

router = Router()


@router.message(CommandStart())
async def command_start_handler(message: Message, state) -> None:
    """
    This handler receives messages with `/start` command

    same as /help.
    """

    await help_handler(message,state)
