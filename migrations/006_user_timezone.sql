-- Store user's IANA timezone (e.g. 'America/New_York')
-- poll_and_fire uses this to compare checkin_time against local time
ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'UTC';
