-- Account deletion confirmation tokens
-- Stores time-limited tokens for account deletion confirmation flow.
-- User requests deletion → token created → emailed → clicked → account deleted.
-- Previous unused tokens are invalidated when a new one is created.

CREATE TABLE IF NOT EXISTS deletion_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,
    token       TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_deletion_tokens_user_id ON deletion_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_deletion_tokens_token    ON deletion_tokens(token);
