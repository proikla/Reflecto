# stdlib
import logging
from datetime import datetime

# local
from util.inline_keyboards import build_and_adjust
from util.delete_misc_messages import (
    delete_user_cached_messages,
    cache_message_for_deletion,
)
from util.db import db_client
from util.inline_keyboards import settings_kb
from util.log import get_logger

# third-party
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

logger = get_logger(__name__)

router = Router()


def next_midnight():
    return datetime.datetime.combine(
        datetime.date.today() + datetime.timedelta(days=1), datetime.time.min
    )


@router.message(Command("settings"))
async def command_settings_handler(message: Message, state):
    """
    Send a settings panel with buttons.
    """
    await state.clear()
    user_id = message.from_user.id

    await delete_user_cached_messages(
        message.bot, message.chat.id, user_id
    )  # it deletes user messages, but not bot ones.
    await cache_message_for_deletion(message)
    # get user interval
    user_settings = await db_client.exec(
        "select interval_hours, utc_offset, dnd_hours, language, morning_message_at_hour, summary_at_hour, custom_reminders from users where user_id = %s",
        (user_id,),
    )
    user_settings = user_settings[0]

    interval = user_settings[0]
    utc_offset = user_settings[1]
    dnd_hours = user_settings[2]
    language = user_settings[3]
    mm_hour = user_settings[4]
    summary_hour = user_settings[5]
    custom_reminders = user_settings[6]

    msg = await message.answer(
        f"""Settings: 
Interval hours: {interval}
Utc offset: {utc_offset}
Do not disturb hours: {dnd_hours}
Language: {language}
Morning messages: {f'at {mm_hour + utc_offset}' if mm_hour else 'disallowed'}
Auto-summary: {f'at {summary_hour + utc_offset}:00' if summary_hour != -1 else 'turned off'}
""",
        reply_markup=build_and_adjust(settings_kb, (3, 2)),
    )
    await cache_message_for_deletion(
        msg, user_id=message.from_user.id
    )  # specify user_id to
