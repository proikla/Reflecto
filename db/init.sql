
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    interval_hours INT,
    utc_offset INT,
    dnd_hours TEXT,
    language TEXT,
    morning_message_at_hour INT,
    summary_at_hour INT DEFAULT -1,
    custom_reminders TEXT,
    json_context JSONB
);

CREATE TABLE entries (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    entry JSONB,
    created_ts TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE summaries (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    summary_text TEXT,
    created_ts TIMESTAMPTZ DEFAULT NOW()
);
