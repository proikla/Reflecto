# stdlib
import asyncio
from util.constants import messages_to_delete
import io
from datetime import UTC, datetime, timedelta, timezone
import json
import logging
from jsonschema import validate

# third-party
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

# local
import neurotasks as nt
from util.db import db_client
from handlers.start import command_start_handler

logger = logging.getLogger(__name__)

router = Router()


@router.message(~F.command())
async def message_handler(message: Message, state: FSMContext) -> None:
    """
    Handle regular incoming messages. If got a voice message - transcribe it to text. Text then goes thru an LLM to make a json summary out of it. Example of the summary:

    Returns:
        None:

    Example:
        >>> message.text
        "Короче, я пошёл в зал. Сейчас буду заниматься."
        message_handler(message)
        >>> message_handler(message)
        "{"date_time":"","entry":"Я пошёл в зал. Сейчас буду заниматься.","plans":["заниматься"],"done":["пошёл в зал"]}"
    """

    # check if the users has set the timezone

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        bot = message.bot
        text = message.text or ''
        chat_id = message.chat.id
        user_utc_offset = await db_client.fetch_field(field='utc_offset', where_field='user_id', where_value=chat_id)
        user_tz = timezone(timedelta(hours=user_utc_offset))
        utc_plus_offset_datetime = datetime.now(user_tz)

        # if user is not in the db or hasn't set their utc_offset
        if not user_utc_offset:
            await command_start_handler(message)
            return

        # send an "reading" acknowledgement.
        messages_to_delete[message.from_user.id].append(await message.answer("Читаю.."))

        loop = asyncio.get_event_loop()

        # *handle voice messages*
        if message.voice:
            # download it in bytes.
            blob = io.BytesIO()
            file = await bot.get_file(message.voice.file_id)
            await bot.download_file(file.file_path, destination=blob)
            blob.seek(0)
            blob = blob.read()
            # += in case there is text already along with the voice message (not gonna happen tho but why not)
            logger.info('Trying to prompt whisper')
            get_whisper_future = loop.run_in_executor(
                None,
                nt.prompt_whisper,
                blob
            )
            try:
                whisper_text = await get_whisper_future
            except Exception as e:
                logger.exception(f"Exception while waiting for whisper: {e}")

            text += whisper_text
            logger.info(f"Got text: {whisper_text} from whisper")

        # length check to prevent deepseek from hallucinating.
        if text.count(' ') < 5:
            await message.reply('Your message is too small!')
            return

        # *await JSON entry from deepseek*
        get_json_future = loop.run_in_executor(
            None,
            nt.get_json_from_journal_entry,
            text
        )
        #
        try:
            raw_json_str = await get_json_future
        except Exception as llm:
            logger.exception(f"Error while calling LLM: {llm}")
            await message.reply("Error. Please try again later.")
            return

        # try to load entry from raw text
        try:
            entry: dict = json.loads(raw_json_str)
        except Exception as e:
            logger.exception(
                f"Failed to parse JSON from llm.\nRaw response: {raw_json_str}")
            await message.reply("Error. Please try again.")
            return

        # *validate JSON* ?maybe redundant.
        schema = {
            "type": "object",
            "properties": {
                "entry": {"type": "string"},
                "plans": {"type": "array"},
                "done": {"type": "array"},
                "mood": {"type": "integer"}}
        }

        sql = """
INSERT INTO entries (
user_id,
entry
) VALUES (
%s,
%s
)
"""
        # try to validate it.
        try:
            validate(entry, schema)

        except Exception as e:
            await message.answer("Error encountered while processing your entry. Please wait a little, then send it again.")
            logger.exception(
                f"Exception '{e}' while validating JSON from LLM.\n {entry=}")

        # try to put data in db.
        try:
            await db_client.exec(sql, (message.from_user.id, json.dumps(entry)))
        except Exception as db_e:
            logger.exception(f"Db error: {db_e}")

        # *Reply to user in user-friendly form.*
        done_list = entry.get("done", [])
        mood = entry.get('mood', '-')
        plans_list = entry.get('plans', [])

        reply = f"""Записал!
Сделано: {', '.join(done_list)}
Запланировано: {', '.join(plans_list)}
Настроение: {mood}
"""

        # todo let the user control data with InlinekeyboardMarkup. Prompt user to change mood, entry, or plans.
        await message.answer(reply)

    except TypeError as e:
        logger.exception(f"Caught exception: {e}")
        await message.answer(f"Nice try. {e}")  # ! debug
