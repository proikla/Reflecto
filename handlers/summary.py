# third-party
import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

# stdlib
import datetime
import logging

# local
import util.llm_tasks as llm_tasks
from util.db import db_client
from keyboards.kb import *

router = Router()
logger = logging.getLogger(__name__)


async def get_user_summary(user_id: int, force=False):
    # * get user entries from the past 24 hours.
    sql = """
SELECT
  jsonb_set(
    entry,
    '{entry}',
    to_jsonb(
      CASE
        WHEN length(entry->>'entry') > 75
          THEN substr(entry->>'entry', 1, 75) || '...'
        ELSE
          entry->>'entry'
      END
    )
  ) AS entry
FROM entries
WHERE user_id = %s
  AND created_ts > %s
ORDER BY created_ts ASC;
"""
    # get user stuff
    user_utc_offset = await db_client.fetch_field(
        field="utc_offset", where_value=user_id
    )
    # user_context = (
    #     await db_client.fetch_field("users", "json_context", "user_id", user_id) or ""
    # ) TODO
    day_ago = (
        datetime.datetime.now(datetime.UTC).replace(hour=0, minute=0, second=0)
        - datetime.timedelta(days=1)
        + datetime.timedelta(hours=user_utc_offset)
    )

    # * check if summary is created already.
    summary_created = await db_client.exec(
        "SELECT s.summary_text FROM summaries as s WHERE s.created_ts > %s",
        (str(day_ago),),
    )

    if summary_created and not force:
        # await message.reply(str(summary_created[0][0]))
        return summary_created

    user_entries = await db_client.exec(sql, params=(user_id, str(day_ago)))

    # join all entries together
    combined_entries = []
    for (entry,) in user_entries:
        try:
            combined_entries.append(
                f"ENTRY: {entry['entry']}\nDONE: {", ".join(entry['done'])}\nPLANNED: {", ".join(entry['plans'])}"
            )
        except Exception as e:
            logger.exception(f"CAUGHT {e}")

    # get summary from LLM
    loop = asyncio.get_event_loop()
    get_summary_future = loop.run_in_executor(
        None, llm_tasks.make_day_summary, "\n".join(combined_entries)
    )
    try:
        summary = await get_summary_future
        return summary
    except:
        return False


@router.message(Command("summary"))
async def summary_command_handler(message: Message, state):
    """
    Get summary for the user.

    Summary is generated every day, at specified time. TODO

    THIS FUNCTION NEEDS TOO:
    - answer user with context.
    """
    user_id = message.from_user.id
    user_utc_offset = await db_client.fetch_field(
        field="utc_offset", where_value=user_id
    )
    day_ago = (
        datetime.datetime.now(datetime.UTC).replace(hour=0, minute=0, second=0)
        - datetime.timedelta(days=1)
        + datetime.timedelta(hours=user_utc_offset)
    )

    # # * check if summary is created already.
    # summary_created = await db_client.exec(
    #     "SELECT s.summary_text FROM summaries as s WHERE s.created_ts > %s",
    #     (str(day_ago),),
    # )

    # if summary_created:
    #     await message.reply(str(summary_created[0][0]))
    #     return

    # * Reply to user with summary
    await message.reply(f"Generating day summary for today, please wait..")
    try:

        summary = await get_user_summary(user_id)

        await db_client.exec(
            "INSERT INTO summaries (user_id, summary_text) VALUES (%s, %s)",
            (user_id, summary),
            fetchall=False,
        )
        await message.reply(f"{summary[0][0]}")
    except Exception as e:
        logger.exception(f"Exception while waiting for summary: {e}")
        await message.reply(f"Sorry, but there was a problem generating your summary.")
