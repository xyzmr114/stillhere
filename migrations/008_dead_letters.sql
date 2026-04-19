CREATE TABLE IF NOT EXISTS dead_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_type TEXT NOT NULL DEFAULT 'contacts', -- 'contacts' or 'email'
    recipient_email TEXT,  -- for custom email recipients
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    trigger_days INT NOT NULL DEFAULT 30, -- days without check-in before sending
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dead_letters_user ON dead_letters (user_id);
CREATE INDEX IF NOT EXISTS idx_dead_letters_unsent ON dead_letters (user_id, sent_at) WHERE sent_at IS NULL;
