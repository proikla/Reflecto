# stdlib
import logging

# third-party
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import Command

# local
from util.db import db_client
from keyboards.kb import settings_firsttime_kb
from util.utils import SettingsInputStates, InSettingsInputStates

logger = logging.getLogger(__name__)


router = Router()


@router.callback_query(InSettingsInputStates())
async def process_user_states(message: Message, state: FSMContext):
    if await state.get_state() == "InSettingsInputStates:tmz_setup":
        await message.answer(
            "Great. Now, you can set other settings up at /settings. If you need more help - use /help."
        )
        await state.clear()


@router.message(Command("help", "start"))
async def help_handler(message: Message, state: FSMContext, is_set=False):
    description = f"""
<b>Reflecto</b> is your personal AI assistant that helps you reflect efficiently while tracking your productivity.
Here's a couple of things Reflecto can do:
- help you make plans for today in the morning
- provide a conveinient and safe way to reflect
- make sure you stay focused by reminding you to write entries
- track your productivity and mood (/stats)
- automatic daily summary generation at the end of the day

<b>Commands:</b>
/help - display this message.
/summary - generate today's summary.
/settings - display settings.
/stats all|month|year - plot a graph of your mood and productivity, also can take number of days as a parameter.
"""
    if not is_set:
        response = await db_client.fetch_field(
            field="utc_offset", where_value=message.from_user.id
        )
    else:
        response = True
    # logger.info(response)
    # if the user is using Reflecto for the first time, prompt them to change TMZ
    if not response:
        markup = settings_firsttime_kb
        description = f"<b>Reflecto</b> is a conveinient way to reflect and track your productivity.\nPlease set your Timezone below to get started."
        await state.set_state(SettingsInputStates.tmz_setup)
    else:
        markup = None

    await message.answer(description, reply_markup=markup)
