# stdlib
# import logging
from datetime import UTC, datetime, timedelta

import loguru

# local
from handlers.help import help_handler
from util.inline_keyboards import build_and_adjust
from util.states import SettingsInputStates

# from util.constants import messages_to_delete
from util.db import db_client
from util.inline_keyboards import timezones_kb
from util.states import SettingsInputStates
from util.delete_misc_messages import (
    delete_user_cached_messages,
    cache_message_for_deletion,
)

# third-party
from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Router

router = Router()
logger = loguru.logger 


@router.callback_query(F.data.regexp(r"set:[a-z]+$"))
async def handle_settings(callback: CallbackQuery, state: FSMContext):
    """
    handle callback_query from /settings panel
    format of callback - 'set:{option}'
    """
    user_id = callback.from_user.id
    command, option = callback.data.split(":")
    match option:
        case "int":
            message = await callback.message.answer(
                "What interval do you want? (in hours)"
            )
            await state.set_state(SettingsInputStates.waiting_interval)
        case "dnd":
            message = await callback.message.answer(
                "What time you don't want me to disturb you in? (range from_hour-to_hour. ex: 22-7)"
            )
            await state.set_state(SettingsInputStates.waiting_dnd)
        case "lang":
            message = await callback.message.answer(
                "What language do you speak? (ru/en)"
            )
            await state.set_state(SettingsInputStates.waiting_lang)
        case "tmz":
            message = await callback.message.answer(
                f"Choose your timezone:",
                reply_markup=build_and_adjust(timezones_kb, (3, 2)),
            )

        case "cr":  # custom reminders
            usr_custom_reminders = await db_client.exec(
                "SELECT custom_reminders FROM users WHERE user_id = %s",
                (user_id,),
                fetchall=False,
            )
            logger.info(f"{usr_custom_reminders=}")
            if not usr_custom_reminders[0]:
                usr_custom_reminders = ["None"]

            message = await callback.message.answer(
                f"""
List custom reminders you'd like to add, separated by a semicolon.
Your current ones are:
<code>{'; '.join(usr_custom_reminders[0])}</code>
                                                   """
            )
            await state.set_state(SettingsInputStates.waiting_cr)
        case "mm":  # morning messages
            message = await callback.message.answer(
                f"What time do you want to get morning messages? 0 To turn off."
            )
            await state.set_state(SettingsInputStates.waiting_mm)

        case "es":  # evening summaries
            message = await callback.message.answer(
                f"What time do you want to get auto summary at? 0 if you don't want to get summaries.\nExample: 20"
            )
            await state.set_state(SettingsInputStates.waiting_es)
        case _:
            message = await callback.message.answer("Something went wrong.")

    await cache_message_for_deletion(message, user_id=callback.from_user.id)

    await callback.answer()


# format of callback - {name}:{offset}
@router.callback_query(F.data.regexp(r"[a-z]+:\d+$"))
async def set_timezone(callback: CallbackQuery, state: FSMContext):
    """
    Handle callback data from inline keyboard `kb` in the following format - {name}:{offset}. Name being the timezone name, offset is UTC offset of this zone.

    Prompt user again with the same inline keyboard.

    Returns:
        None:
    """

    #!todo prevent users from spamming this shit. maybe.

    # get timezone and offset from callback
    if not callback.data:
        return

    name, offset = callback.data.split(":")
    offset = int(offset)
    time_now = datetime.now(UTC)
    time_offset = time_now + timedelta(hours=offset)
    user_id = callback.from_user.id

    # put this data into db.
    await db_client.upsert_field(
        table="users",
        key_field="user_id",
        key_value=user_id,
        target_field="utc_offset",
        target_value=offset,
    )

    logger.info(f"Updated {user_id} in db.")

    # answer callback.
    if await state.get_state() == "SettingsInputStates:tmz_setup":
        text = f"Timezone is set! Here's what you can do with <b>Reflecto</b>:"
        help = True
        markup = None
        await state.clear()
    else:
        text = (
            f"Timezone set to {name}! It is {time_offset.strftime('%H:%M:%S')} there."
        )
        help = False
        markup = build_and_adjust(timezones_kb, (3, 2))
        logger.info(f"Trying to edit message with this markup: {markup}")
        await callback.message.edit_text(
            text,
            reply_markup=markup,
        )
        await callback.answer(f"Selected {name}")

    if help:
        await help_handler(callback.message, state, True)
