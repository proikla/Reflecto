# stdlib
import re
import logging
from datetime import UTC, datetime, timedelta

# local
from handlers.help import help_handler
from util.inline_keyboards import build_and_adjust
from util.constants import SERVER_UTC_OFFSET, messages_to_delete
from handlers.scheduling import scheduler, send_msg
from util.constants import SUPPORTED_LANGUAGES
from util.db import db_client
from util.inline_keyboards import settings_kb, settings_firsttime_kb, timezones_kb

# third-party
from apscheduler.triggers.interval import IntervalTrigger
from aiogram.methods.send_message import SendMessage
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext


from apscheduler.triggers.cron import CronTrigger

from util.states import InSettingsInputStates, SettingsInputStates

logger = logging.getLogger(__name__)

router = Router()


def next_midnight():
    return datetime.datetime.combine(
        datetime.date.today() + datetime.timedelta(days=1), datetime.time.min
    )


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

    messages_to_delete[user_id].append(message.message_id)

    curr = await state.get_state()  # Form:name_of_the_state
    curr = curr[20:]

    if curr == "tmz_setup":
        await message.answer("Your tmz isnt setyup")
        return

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
                await db_client.update_field(
                    "users", "interval_hours", interval, "user_id", user_id
                )
                job = scheduler.get_job(str(user_id))
                if job:
                    # scheduler.remove_job(str(user_id))
                    scheduler.add_job(
                        send_msg,
                        IntervalTrigger(hours=interval),
                        job.args,
                        kwargs=job.kwargs,
                        id=str(user_id),
                        replace_existing=True,
                    )

                msg = None

        case "waiting_dnd":
            if not re.search(r"\b\d{1,2}-\d{1,2}$", message.text):
                msg = await message.reply(
                    "Please ensure your range is valid. Like this: 22-7. (Meaning, i won't disturb you from 22:00 to 7:00) "
                )
            else:
                await db_client.update_field(
                    "users", "dnd_hours", message.text, "user_id", user_id
                )
                msg = None
        case "waiting_lang":
            if not message.text in SUPPORTED_LANGUAGES:
                msg = await message.reply("It's not a valid language. Choose en or ru.")
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
            if (
                not message.text.isnumeric()
                and int(message.text) < 0
                or int(message.text) > 24
            ):
                msg = message.answer(
                    "Your message has to be a number (0-24)."
                )  # test TODO
            else:
                # update in db
                await db_client.update_field(
                    "users",
                    "morning_message_at_hour",
                    int(message.text),
                    "user_id",
                    user_id,
                )
                allow_mm = int(message.text) - usr_utc_offset

                # reschedule morning message
                job = scheduler.get_job(f"M{user_id}")
                if job:
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

    if not msg:
        msg = message.message_id

    if isinstance(msg, SendMessage):  # ?
        msg = msg.reply_parameters.message_id

    messages_to_delete[user_id].append(msg)

    await command_settings_handler(message)
    await state.clear()


@router.message(Command("settings"))
async def command_settings_handler(message: Message):
    """
    Send a settings panel with buttons.
    """
    user_id = message.from_user.id

    # get user interval
    user_settings = await db_client.exec(
        "select interval_hours, utc_offset, dnd_hours, language, morning_message_at_hour, summary_at_hour, custom_reminders from users where user_id = %s",
        (user_id,),
    )
    user_settings = user_settings[0]

    msg = await message.answer(
        f"""Settings: 
Interval hours: {user_settings[0]}
Utc offset: {user_settings[1]}
Do not disturb hours: {user_settings[2]}
Language: {user_settings[3]}
Morning messages: {f'at {user_settings[4]}' if user_settings[4] else 'disallowed'}
Auto-summary: {f'at {user_settings[5] + user_settings[1]}:00' if user_settings[5] != -1 else 'turned off'}
""",
        reply_markup=build_and_adjust(settings_kb, (3, 2)),
    )
    messages_to_delete[user_id].append(msg.message_id)


#! format of callback - set:{option}
@router.callback_query(F.data.regexp(r"set:[a-z]+$"))
async def handle_settings(callback: CallbackQuery, state: FSMContext):
    """
    handle callback_query from /settings panel
    """
    user_id = callback.from_user.id
    command, option = callback.data.split(":")
    match option:
        case "int":
            message = await callback.message.reply(
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
            message = await callback.message.reply(
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

            message = await callback.message.reply(
                f"""
List custom reminders you'd like to add, separated by a semicolon.
Your current ones are:
<code>{'; '.join(usr_custom_reminders[0])}</code>
                                                   """
            )
            await state.set_state(SettingsInputStates.waiting_cr)
        case "mm":  # morning messages
            message = await callback.message.reply(
                f"What time do you want to get morning messages? 0 To turn off."
            )
            await state.set_state(SettingsInputStates.waiting_mm)

        case "es":  # evening summaries
            message = await callback.message.reply(
                f"What time do you want to get auto summary at? 0 if you don't want to get summaries.\nExample: 20"
            )
            await state.set_state(SettingsInputStates.waiting_es)
        case _:
            message = await callback.message.answer("Something went wrong.")

    messages_to_delete[user_id].append(message.message_id)
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
        markup = (build_and_adjust(timezones_kb, (3, 2)),)

    await callback.message.edit_text(
        text,
        reply_markup=markup,
    )
    await callback.answer(f"Selected {name}")

    if help:
        await help_handler(callback.message, state, True)
