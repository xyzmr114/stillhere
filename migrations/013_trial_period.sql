-- Add 7-day free trial support
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMPTZ DEFAULT NULL;

-- Backfill: existing paid users don't need a trial
-- Existing unpaid users get no trial (they were on the old flow)
-- New signups will get trial_ends_at set by the registration endpoint
