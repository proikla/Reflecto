# local
from collections import defaultdict

# stdlib
from typing import Dict, List

# third-party
from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError
import loguru

logger = loguru.logger

messages_to_delete: Dict[int, List[Message]] = defaultdict(list)


async def delete_user_cached_messages(bot: Bot, chat_id: int, user_id: int) -> None:
    "delete cached messages in a specific chat"

    messages: List[Message] = messages_to_delete.get(user_id)

    if not messages:
        logger.debug(f"No messages to delete for {user_id}")
        return

    message_ids = [msg.message_id for msg in messages]
    try:
        await bot.delete_messages(
            chat_id=chat_id, message_ids=message_ids
        )  # delete cached user messages

        logger.info(f"deleted messages for user {user_id} and {bot.id}")
    except TelegramAPIError as api_error:
        logger.error(f"failed to delete messages for user {user_id}: {api_error=}")
    finally:
        messages_to_delete[user_id].clear()


async def cache_message_for_deletion(message: Message, user_id: int = None) -> None:
    """
    cache messages to delete later

    Params:
        :user_id: specify user_id when the message being cached is from the bot, not user.
    """
    if not user_id:
        user_id = message.from_user.id
    # if isinstance(message, SendMessage):
    # logger.exception(f"Got message: {message}")

    messages_to_delete[user_id].append(message)
    logger.debug(f"cached message {message.message_id} for user {user_id}")
