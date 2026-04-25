-- SECURITY FIX: Enable RLS on all tables and revoke public/anon access.
--
-- The backend connects as postgres (superuser) via DATABASE_URL, which bypasses
-- RLS entirely. No policies are needed — deny-all is the correct default.
-- The anon and authenticated roles should never access these tables directly;
-- all access goes through the FastAPI backend.

-- ── Enable RLS on tables that don't have it ──────────────────────────────────
ALTER TABLE checkin_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE contact_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE dead_letters ENABLE ROW LEVEL SECURITY;
ALTER TABLE non_emergency_numbers ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE waitlist ENABLE ROW LEVEL SECURITY;

-- ── Revoke anon access from ALL tables ───────────────────────────────────────
-- anon role = unauthenticated Supabase client requests. Our app never uses this.
REVOKE ALL ON users FROM anon;
REVOKE ALL ON checkins FROM anon;
REVOKE ALL ON emergency_contacts FROM anon;
REVOKE ALL ON escalation_events FROM anon;
REVOKE ALL ON contact_confirmations FROM anon;
REVOKE ALL ON contact_portal_tokens FROM anon;
REVOKE ALL ON contact_submissions FROM anon;
REVOKE ALL ON audit_log FROM anon;
REVOKE ALL ON mutual_pairs FROM anon;
REVOKE ALL ON groups FROM anon;
REVOKE ALL ON group_members FROM anon;
REVOKE ALL ON group_pings FROM anon;
REVOKE ALL ON families FROM anon;
REVOKE ALL ON family_members FROM anon;
REVOKE ALL ON family_invites FROM anon;
REVOKE ALL ON sensor_webhooks FROM anon;
REVOKE ALL ON api_keys FROM anon;
REVOKE ALL ON checkin_prompts FROM anon;
REVOKE ALL ON contact_messages FROM anon;
REVOKE ALL ON dead_letters FROM anon;
REVOKE ALL ON non_emergency_numbers FROM anon;
REVOKE ALL ON notification_messages FROM anon;
REVOKE ALL ON waitlist FROM anon;

-- ── Revoke authenticated access from ALL tables ──────────────────────────────
-- authenticated role = Supabase client JWT requests. Our app uses its own JWT
-- layer (python-jose), not Supabase Auth, so this role should also be locked out.
REVOKE ALL ON users FROM authenticated;
REVOKE ALL ON checkins FROM authenticated;
REVOKE ALL ON emergency_contacts FROM authenticated;
REVOKE ALL ON escalation_events FROM authenticated;
REVOKE ALL ON contact_confirmations FROM authenticated;
REVOKE ALL ON contact_portal_tokens FROM authenticated;
REVOKE ALL ON contact_submissions FROM authenticated;
REVOKE ALL ON audit_log FROM authenticated;
REVOKE ALL ON mutual_pairs FROM authenticated;
REVOKE ALL ON groups FROM authenticated;
REVOKE ALL ON group_members FROM authenticated;
REVOKE ALL ON group_pings FROM authenticated;
REVOKE ALL ON families FROM authenticated;
REVOKE ALL ON family_members FROM authenticated;
REVOKE ALL ON family_invites FROM authenticated;
REVOKE ALL ON sensor_webhooks FROM authenticated;
REVOKE ALL ON api_keys FROM authenticated;
REVOKE ALL ON checkin_prompts FROM authenticated;
REVOKE ALL ON contact_messages FROM authenticated;
REVOKE ALL ON dead_letters FROM authenticated;
REVOKE ALL ON non_emergency_numbers FROM authenticated;
REVOKE ALL ON notification_messages FROM authenticated;
REVOKE ALL ON waitlist FROM authenticated;

-- ── Also revoke default privileges for future tables ─────────────────────────
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM authenticated;
