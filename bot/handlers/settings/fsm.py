# stdlib
import logging
import re

import loguru


# local
from handlers.settings.settings import command_settings_handler
from util.states import InSettingsInputStates
from util.constants import SERVER_UTC_OFFSET, SUPPORTED_LANGUAGES
from util.db import db_client
from ..scheduling import scheduler, send_msg

# third-party
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram import Router
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from util.delete_misc_messages import (
    delete_user_cached_messages,
    cache_message_for_deletion,
)

router = Router()
logger = loguru.logger


@router.message(InSettingsInputStates())
async def process_fsm(message: Message, state: FSMContext):
    """
    Handle messages with FSMContext present, meaning, messages that wait for a value from user. Used to configure settings.
    """
    # add_messages_to_delete(message.message_id)
    user_id = message.from_user.id
    usr_utc_offset = await db_client.fetch_field(
        field="utc_offset", where_value=user_id
    )

    curr = await state.get_state()  # Form:name_of_the_state
    curr = curr[20:]

    if curr == "tmz_setup":
        await message.answer("Your tmz isnt setyup")
        return

    # cache user message for deletion.
    # await cache_message_for_deletion(message)
    # * Handle different states.
    match curr:
        case "waiting_interval":
            if not message.text.isnumeric():
                msg = await message.answer(
                    "Please send me the interval you want in hours."
                )
            else:
                msg = None
                interval = int(message.text)
                await db_client.update_field(
                    "users", "interval_hours", interval, "user_id", user_id
                )
                job = scheduler.get_job(str(user_id))
                if job:
                    scheduler.add_job(
                        send_msg,
                        IntervalTrigger(hours=interval),
                        job.args,
                        kwargs=job.kwargs,
                        id=str(user_id),
                        replace_existing=True,
                    )

        case "waiting_dnd":
            if not re.search(r"\b\d{1,2}-\d{1,2}$", message.text):
                msg = await message.answer(
                    "Please ensure your range is valid. Like this: 22-7. (Meaning, i won't disturb you from 22:00 to 7:00) "
                )
            else:
                await db_client.update_field(
                    "users", "dnd_hours", message.text, "user_id", user_id
                )
                msg = None
        case "waiting_lang":
            if not message.text in SUPPORTED_LANGUAGES:
                msg = await message.answer(
                    "It's not a valid language. Choose en or ru."
                )
            else:
                await db_client.update_field(
                    "users", "language", message.text, "user_id", user_id
                )
                msg = None
        case "waiting_tmz":
            msg = None
            # ?
            await state.clear()
            ...

        case "waiting_cr":
            custom_reminders = re.findall(
                r"[\d\w\s\W][^;]+(?=[;])|[^;][\d\w\s\W]+$", message.text
            )  # <sentence>; <sentence>
            #! test
            logger.info(custom_reminders)
            if custom_reminders:
                await db_client.update_field(
                    "users", "custom_reminders", custom_reminders, "user_id", user_id
                )
                msg = None
            else:
                msg = message.reply(
                    "Your message is horribly wrong somehow. Try again."
                )
        case (
            "waiting_mm"
        ):  # todo rework. 0 to turn off, any other value < 12 to schedule a morning message

            if not message.text.isnumeric() or (
                message.text.isnumeric()
                and (int(message.text) < 0 or int(message.text))
            ):
                msg = message.answer(
                    "Your message has to be a number (0-24)."
                )  # test TODO
            else:
                # update in db
                allow_mm = int(message.text) - usr_utc_offset # allow_mm - morning message time #?
                await db_client.update_field(
                    "users",
                    "morning_message_at_hour",
                    allow_mm,
                    "user_id",
                    user_id,
                )

                # reschedule morning message
                job = scheduler.get_job(f"M{user_id}")
                if job and allow_mm:
                    scheduler.add_job(
                        send_msg,
                        CronTrigger(hour=allow_mm + SERVER_UTC_OFFSET),
                        [user_id, False, True],  # probs use kwargs instead
                        replace_existing=True,
                    )

                msg = None

        case "waiting_es":  # evening summary (auto-summary)
            if message.text.isnumeric() and -1 <= int(message.text) <= 24:

                time = (
                    int(message.text) - usr_utc_offset if int(message.text) != 0 else -1
                )

                if time + SERVER_UTC_OFFSET == 24:
                    time = 0

                await db_client.update_field(
                    "users",
                    "summary_at_hour",
                    time,  # store summary_at_hour in UTC.
                    "user_id",
                    user_id,
                )

                try:
                    job = scheduler.get_job(f"S{user_id}")
                except:
                    job = scheduler.add_job(
                        send_msg,
                        CronTrigger(hour=(int(message.text) + SERVER_UTC_OFFSET) % 24),
                        [user_id, True],
                        id=f"S{user_id}",
                    )

                if not time == -1:
                    if job:
                        scheduler.add_job(
                            send_msg,
                            CronTrigger(
                                hour=(int(message.text) + SERVER_UTC_OFFSET) % 24
                            ),
                            [user_id, True],
                            job.kwargs,
                            f"S{user_id}",
                            replace_existing=True,
                        )
                else:
                    scheduler.remove_job(job_id=f"S{user_id}")

            msg = None

        case _:
            msg = await message.answer("Something went wrong!")

    if msg:  # cache bot reply to user message if there is one
        await cache_message_for_deletion(msg, user_id=message.from_user.id)

    await state.clear()
    await command_settings_handler(message, state)
