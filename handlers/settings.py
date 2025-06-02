from apscheduler.triggers.interval import IntervalTrigger
import asyncio

import apscheduler
import apscheduler.schedulers
from keyboards.kb import build_and_adjust
from util.constants import messages_to_delete
from collections import defaultdict
from datetime import UTC, datetime, timedelta
import re
from aiogram.filters.base import Filter
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from util.constants import SUPPORTED_LANGUAGES
from util.db import db_client
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging
from handlers.scheduling import scheduler
from keyboards.kb import settings_kb, settings_firsttime_kb, timezones_kb
from handlers.scheduling import send_msg

# from polling import scheduler


class Form(StatesGroup):
    waiting_interval = State()
    waiting_dnd = State()
    waiting_tmz = State()
    waiting_lang = State()


class InForm(Filter):
    async def __call__(self, message: Message, state: FSMContext):
        curr = await state.get_state()
        return curr is not None and curr.startswith("Form:")


logger = logging.getLogger(__name__)

router = Router()


def next_midnight():
    return datetime.datetime.combine(
        datetime.date.today() + datetime.timedelta(days=1), datetime.time.min
    )


@router.message(InForm(), F.text)
async def process_fsm(message: Message, state: FSMContext):
    """
    Handle messages with FSMContext present, meaning, messages that wait for a value from user. Used to configure settings.
    """
    user_id = message.from_user.id
    # get name of the state
    curr = await state.get_state()  # Form:name_of_the_state
    curr = curr[5:]

    # delete user answer
    messages_to_delete[user_id].append(message.message_id)
    # * Handle different states.
    match curr:
        case "waiting_interval":
            if not message.text.isnumeric():
                msg = await message.reply(
                    "Please send me the interval you want in hours."
                )

            else:
                interval = int(message.text)
                # update user interval
                await db_client.update_field(
                    "users", "interval_hours", message.text, "user_id", user_id
                )

                # update reminder interval for user.
                job = scheduler.get_job(str(user_id))
                if job:
                    scheduler.remove_job(str(user_id))
                    scheduler.add_job(
                        func=send_msg,
                        trigger=IntervalTrigger(hours=interval),
                        args=job.args,
                        kwargs=job.kwargs,
                        id=str(user_id),
                        replace_existing=True,
                    )
                    logger.info(f"UPDATED {user_id} JOB!")

                msg = None  # set msg to none, as no reply to delete in the future was generated.

        case "waiting_dnd":
            if not re.search(r"\b\d{1,2}-\d{1,2}$", message.text):
                msg = await message.reply(
                    "Please ensure your range is valid. Like this: 22-7. (Meaning, i won't disturb you from 22:00 to 7:00) "
                )
            else:
                await db_client.update_field(
                    "users", "dnd_hours", message.text, "user_id", message.from_user.id
                )
                logger.info(f"updated dnd")
                msg = None

        case "waiting_lang":
            if not message.text in SUPPORTED_LANGUAGES:
                msg = await message.reply("It's not a valid language. Choose en or ru.")
            else:
                await db_client.update_field(
                    "users", "language", message.text, "user_id", message.from_user.id
                )
                logger.info(f"Updated language for {message.from_user.id}")
                msg = None

        case "waiting_tmz":
            ...

        case _:
            msg = await message.answer("Something went wrong!")

    if not msg:
        msg = message
    messages_to_delete[message.from_user.id].append(msg.message_id)

    # await message.answer(f"Gotcha! You chose {message.text}. {curr}")
    await command_settings_handler(message)
    # await message.delete()
    await state.clear()


@router.message(Command("settings"))
async def command_settings_handler(message: Message):
    """
    Send a settings panel with buttons.
    """

    # get user interval
    user_settings = await db_client.exec(
        "select interval_hours, utc_offset, dnd_hours, language from users where user_id = %s",
        (message.from_user.id,),
    )
    user_settings = user_settings[0]

    try:
        if messages := messages_to_delete[message.from_user.id]:
            await message.bot.delete_messages(message.chat.id, messages)
            # rework's needed perhaps
            messages_to_delete[message.from_user.id] = []

    except Exception as e:
        logger.exception(f"Exception while trying to delete messages: {e}")

    msg = await message.answer(
        f"""Settings: 
Interval hours: {user_settings[0]}
Utc offset: {user_settings[1]}
Do not disturb hours: {user_settings[2]}
Language: {user_settings[3]}""",
        reply_markup=build_and_adjust(settings_kb, (3, 2)),
    )
    messages_to_delete[message.from_user.id].append(msg.message_id)


# format of callback - set:{option}
@router.callback_query(F.data.regexp(r"set:[a-z]+$"))
async def handle_settings(callback: CallbackQuery, state: FSMContext):
    """
    handle callback_query from /settings panel
    """
    command, option = callback.data.split(":")
    match option:
        case "int":
            message = await callback.message.reply(
                "What interval do you want? (in hours)"
            )
            await state.set_state(Form.waiting_interval)
        case "dnd":
            message = await callback.message.answer(
                "What time do you usually sleep? Tell me, and i won't disturb you then. (range from_hour-to_hour. ex: 22-7)"
            )
            await state.set_state(Form.waiting_dnd)
        case "lang":
            message = await callback.message.answer(
                "What language do you speak? (ru/en)"
            )
            await state.set_state(Form.waiting_lang)
        case "tmz":
            message = await callback.message.reply(
                f"Choose your timezone:",
                reply_markup=build_and_adjust(timezones_kb, (3, 2)),
            )
            # await state.set_state(Form.waiting_tmz)
        case _:
            message = await callback.message.answer("Something went wrong.")

    messages_to_delete[callback.from_user.id].append(message.message_id)
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
    await callback.message.edit_text(
        f"Timezone set to {name}! It is {time_offset.strftime('%H:%M:%S')} there.",
        reply_markup=build_and_adjust(timezones_kb, (3, 2)),
    )
    await callback.answer(f"Selected {name}")
