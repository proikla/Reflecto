import datetime
import json
import logging
from aiogram import Router
from aiogram.filters import Command
import neurotasks
from util.db import db_client
from aiogram.types import Message
from keyboards.kb import *
from util.constants import messages_to_delete
router = Router()
logger = logging.getLogger(__name__)


@router.message(Command('summary'))
async def summary_handler(message: Message, state):
    """
    Get summary for the user.

    Summary should be stored in DB. TODO
    Summary is generated every day, at specified time. TODO
    If summary was already generated today, it's not necessary to generate it again obviously. TODO
    LLM takes user context in, today's done tasks and planned tasks [DONE]

    TODO USER CONTEXT:
    context should be renewed once in a while.
    possible times for context renewal:
    - new entry time (if it's big idk, or if there are a lot of plans and stuff.)
        - you can check long entries for new context TODO:
        ie:
        - OR:
            - pass user context on every entry processing
            - if entry is long enough prompt LLM for new context (it already knows past context) [im gonna go with that lol]

    THIS FUNCTION NEEDS TOO:
    - prompt LLM to create summary of today based on all entries
        - figure out the way to save tokens on that one
    - answer user with context. 

    TODO:
    MAKE IT ASYNC! run in pool.
    """

    user_id = message.from_user.id
    user_utc_offset = await db_client.fetch_field(field='utc_offset', where_value=user_id)
    day_ago = datetime.datetime.now(datetime.UTC).replace(
        hour=0, minute=0, second=0) - datetime.timedelta(days=1) + datetime.timedelta(hours=user_utc_offset)

    user_context = await db_client.fetch_field(
        'users', 'json_context', 'user_id', user_id) or ''

#     sql = """
# SELECT entry FROM entries WHERE user_id = %s AND created_ts > %s ORDER BY created_ts ASC
# """

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
    user_entries = await db_client.exec(sql, params=(user_id, str(day_ago)))
    logger.info(f"USER_ENTRIES: {len(user_entries)=}")
    """
    IM GONNA DO IT THIS WAY:
    entries = [
    ENTRY: blablablabla
    DONE: 1,2,3,4
    PLANNED: bla,bla,bla,bla

    ENTRY: ...
    ...
    ]
    """

    combined_entries = [
        f"ENTRIES FROM {day_ago - datetime.timedelta(hours=user_utc_offset)} to {datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=user_utc_offset)}"]
    for entry, in user_entries:
        try:
            combined_entries.append(
                f"ENTRY: {entry['entry']}\nDONE: {", ".join(entry['done'])}\nPLANNED: {", ".join(entry['plans'])}")
        except Exception as e:
            logger.exception(f"CAUGHT {e}")
            # logger.info(f"Got {combined_entries=}")

    summary = neurotasks.make_day_summary_from_json(
        entries='\n'.join(combined_entries))
    # TODO: PUT THIS SUMMARY IN DB!
    await message.reply(summary)
    # await message.answer("\n\n".join(combined_entries))
