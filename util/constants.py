from collections import defaultdict


# DEFAULT_RU_REMINDERS = ['Пожалуйста, сделайте запись.',
#                         'Не забудь сделать запись!', 'Я жду запись от тебя ;)', 'Сделаешь запись? Ты мне сказал тебе надо напоминать каждые {i} часа.']


SUPPORTED_LANGUAGES = ["ru", "en"]
TIMEZONES = [("utc", 0), ("europe", 1), ("moscow", 3), ("yekaterinburg", 5)]
from datetime import UTC, datetime, timedelta

utc_now_hour = int(datetime.now(UTC).strftime("%H"))
SERVER_UTC_OFFSET = int(
    (datetime.now() - timedelta(hours=utc_now_hour)).strftime("%H")
)  # server's UTC offset in hours

#! temporary!
messages_to_delete: defaultdict = defaultdict(list)
