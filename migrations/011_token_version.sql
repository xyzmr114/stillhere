-- Token version for JWT revocation.
-- Incrementing this column invalidates all existing tokens for that user.
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER DEFAULT 1 NOT NULL;
