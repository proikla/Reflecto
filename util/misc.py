# local
from util.constants import messages_to_delete
from util.log import get_logger

# stdlib

logger = get_logger(__name__)


# todo rename, rework
async def delete_misc_messages(message, user_id: int):

    try:
        messages = messages_to_delete[user_id]
        if messages:
            message_ids = [m.message_id for m in messages]
            # if messages := messages_to_delete[int(user_id)]:
            await message.bot.delete_messages(
                message.chat.id, message_ids
            )  # ? lol use user_id instead of message.chat.id no?

            # rework's needed perhaps
            messages_to_delete[int(user_id)] = []
            logger.info(f"Deleted messages from {user_id}. Chat: {message.chat.id}")

    except Exception as e:
        logger.exception(f"Exception while trying to delete messages: {e}")
