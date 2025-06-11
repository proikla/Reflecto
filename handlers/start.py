# third-party
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

# local
from util.db import db_client
from util.constants import messages_to_delete
from keyboards.kb import *

router = Router()


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    response = await db_client.fetch_field(
        field="utc_offset", where_value=message.from_user.id
    )

    if not response:
        await db_client.upsert_field(
            "users",
            "user_id",
            message.from_user.id,
            target_field="utc_offset",
            target_value=None,
        )
        text = "Hi, choose your timezone please. It's essential for AI context. You can set other /settings after that."
        markup = build_and_adjust(settings_firsttime_kb, (1, 1))

    else:
        timezone_name = next(
            # get timezone name from TIMEZONES
            filter(lambda x: x[1] == int(response), TIMEZONES)
        )[0]
        text = f"Your timezone is {timezone_name} (UTC+{response}) "
        markup = build_and_adjust(timezones_kb, (3, 2))

    msg = await message.answer(text=text, reply_markup=markup)
    messages_to_delete[message.from_user.id].append(msg.message_id)
