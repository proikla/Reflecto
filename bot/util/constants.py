from datetime import UTC, datetime, timedelta

SUPPORTED_LANGUAGES = ["ru", "en"]  #
TIMEZONES = [
    ("utc", 0),
    ("europe", 1),
    ("moscow", 3),
    ("yekaterinburg", 5),
    ("NY", -4)
]  # ("TMZ", utc_offset)


utc_now_hour = int(datetime.now(UTC).strftime("%H"))
SERVER_UTC_OFFSET = int(
    (datetime.now() - timedelta(hours=utc_now_hour)).strftime("%H")
)  # server's UTC offset in hours
