-- User address fields for welfare check routing
ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS city TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS state TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS zip_code TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS non_emergency_number TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS non_emergency_verified BOOLEAN NOT NULL DEFAULT FALSE;

-- Non-emergency number lookup table
CREATE TABLE IF NOT EXISTS non_emergency_numbers (
    id SERIAL PRIMARY KEY,
    state TEXT NOT NULL,
    city TEXT NOT NULL,
    phone TEXT NOT NULL,
    department TEXT,
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_non_emergency_state_city ON non_emergency_numbers (LOWER(state), LOWER(city));
CREATE INDEX IF NOT EXISTS idx_users_zip ON users (zip_code);
