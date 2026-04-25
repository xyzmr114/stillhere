-- Track Stripe payment details for audit trail.
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_session_id TEXT DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_email TEXT DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ DEFAULT NULL;
