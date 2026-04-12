import json
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user(db, user_id: str):
    row = db.execute(
        text("SELECT * FROM users WHERE id = :id"), {"id": user_id}
    ).mappings().first()
    return dict(row) if row else None


def get_user_by_email(db, email: str):
    row = db.execute(
        text("SELECT * FROM users WHERE email = :email"), {"email": email}
    ).mappings().first()
    return dict(row) if row else None


def get_users_due_for_checkin(db):
    now_utc = datetime.now(timezone.utc)
    current_time = now_utc.time().replace(second=0, microsecond=0)
    rows = db.execute(
        text("SELECT * FROM users WHERE checkin_time = :t"), {"t": current_time}
    ).mappings().all()
    return [dict(r) for r in rows]


def has_checked_in_today(db, user_id: str) -> bool:
    today = date.today()
    row = db.execute(
        text(
            "SELECT 1 FROM checkins WHERE user_id = :uid AND checked_in_at::date = :today LIMIT 1"
        ),
        {"uid": user_id, "today": today},
    ).first()
    return row is not None


def log_checkin(db, user_id: str, method: str = "app"):
    db.execute(
        text(
            "INSERT INTO checkins (user_id, method) VALUES (:uid, :method)"
        ),
        {"uid": user_id, "method": method},
    )
    db.commit()


def get_today_checkin(db, user_id: str):
    today = date.today()
    row = db.execute(
        text(
            "SELECT * FROM checkins WHERE user_id = :uid AND checked_in_at::date = :today ORDER BY checked_in_at DESC LIMIT 1"
        ),
        {"uid": user_id, "today": today},
    ).mappings().first()
    return dict(row) if row else None


def get_contacts(db, user_id: str):
    rows = db.execute(
        text(
            "SELECT * FROM emergency_contacts WHERE user_id = :uid ORDER BY priority"
        ),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def add_contact(db, user_id: str, name: str, phone: str, email: str = None, priority: int = 1):
    result = db.execute(
        text(
            "INSERT INTO emergency_contacts (user_id, name, phone, email, priority) VALUES (:uid, :name, :phone, :email, :priority) RETURNING id"
        ),
        {"uid": user_id, "name": name, "phone": phone, "email": email, "priority": priority},
    ).first()
    db.commit()
    return result[0]


def update_contact(db, contact_id: str, user_id: str, **fields):
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    fields["cid"] = contact_id
    fields["uid"] = user_id
    db.execute(
        text(f"UPDATE emergency_contacts SET {sets} WHERE id = :cid AND user_id = :uid"),
        fields,
    )
    db.commit()


def delete_contact(db, contact_id: str, user_id: str):
    db.execute(
        text("DELETE FROM emergency_contacts WHERE id = :cid AND user_id = :uid"),
        {"cid": contact_id, "uid": user_id},
    )
    db.commit()


def log_escalation_event(db, user_id: str, stage: str, confirmation_token: str = None):
    result = db.execute(
        text(
            "INSERT INTO escalation_events (user_id, stage, confirmation_token) VALUES (:uid, :stage, :token) RETURNING id"
        ),
        {"uid": user_id, "stage": stage, "token": confirmation_token},
    ).first()
    db.commit()
    return result[0]


def resolve_escalations(db, user_id: str):
    db.execute(
        text(
            "UPDATE escalation_events SET resolved = TRUE, resolved_at = NOW() WHERE user_id = :uid AND resolved = FALSE"
        ),
        {"uid": user_id},
    )
    db.commit()


def get_active_escalation(db, user_id: str):
    row = db.execute(
        text(
            "SELECT * FROM escalation_events WHERE user_id = :uid AND resolved = FALSE ORDER BY triggered_at DESC LIMIT 1"
        ),
        {"uid": user_id},
    ).mappings().first()
    return dict(row) if row else None


def get_escalation_by_token(db, token: str):
    row = db.execute(
        text(
            "SELECT * FROM escalation_events WHERE confirmation_token = :token LIMIT 1"
        ),
        {"token": token},
    ).mappings().first()
    return dict(row) if row else None


def get_checkin_history(db, user_id: str):
    rows = db.execute(
        text(
            "SELECT c.checked_in_at, c.method, c.note FROM checkins c WHERE c.user_id = :uid ORDER BY c.checked_in_at DESC LIMIT 30"
        ),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def get_streak(db, user_id: str) -> int:
    rows = db.execute(
        text(
            "SELECT DISTINCT checked_in_at::date AS d FROM checkins WHERE user_id = :uid AND checked_in_at::date <= CURRENT_DATE ORDER BY d DESC LIMIT 365"
        ),
        {"uid": user_id},
    ).mappings().all()
    if not rows:
        return 0
    dates = [r["d"] for r in rows]
    today = date.today()
    if dates[0] != today:
        return 0
    streak = 1
    for i in range(1, len(dates)):
        if dates[i - 1] - dates[i] == timedelta(days=1):
            streak += 1
        else:
            break
    return streak


def has_contact_confirmed(db, user_id: str) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM escalation_events WHERE user_id = :uid AND stage = 'contact_confirmed' AND resolved = TRUE LIMIT 1"
        ),
        {"uid": user_id},
    ).first()
    return row is not None


def get_contact_confirmation_by_token(db, token: str):
    row = db.execute(
        text("SELECT cc.*, ec.name as contact_name FROM contact_confirmations cc JOIN emergency_contacts ec ON cc.contact_id = ec.id WHERE cc.confirmation_token = :token"),
        {"token": token},
    ).mappings().first()
    return dict(row) if row else None


def confirm_contact(db, confirmation_token: str):
    result = db.execute(
        text("UPDATE contact_confirmations SET confirmed_at = NOW() WHERE confirmation_token = :token AND confirmed_at IS NULL RETURNING escalation_event_id"),
        {"token": confirmation_token},
    ).first()
    db.commit()
    return result[0] if result else None


def count_contact_confirmations(db, escalation_event_id: str):
    confirmed = db.execute(
        text("SELECT COUNT(*) FROM contact_confirmations WHERE escalation_event_id = :eid AND confirmed_at IS NOT NULL"),
        {"eid": escalation_event_id},
    ).scalar()
    total = db.execute(
        text("SELECT COUNT(*) FROM contact_confirmations WHERE escalation_event_id = :eid"),
        {"eid": escalation_event_id},
    ).scalar()
    return confirmed, total


def user_confirm_escalation(db, escalation_event_id: str, user_id: str):
    db.execute(
        text("UPDATE escalation_events SET user_confirmed_at = NOW(), resolved = TRUE, resolved_at = NOW() WHERE id = :eid AND user_id::text = :uid AND resolved = FALSE"),
        {"eid": escalation_event_id, "uid": user_id},
    )
    db.commit()


def is_escalation_resolved(db, escalation_event_id: str) -> bool:
    row = db.execute(
        text("SELECT resolved FROM escalation_events WHERE id = :eid"),
        {"eid": escalation_event_id},
    ).first()
    return row[0] if row else True


def get_escalation_by_id(db, escalation_event_id: str):
    row = db.execute(
        text("SELECT * FROM escalation_events WHERE id = :eid"),
        {"eid": escalation_event_id},
    ).mappings().first()
    return dict(row) if row else None


def cancel_escalation(db, escalation_id: str, user_id: str):
    row = db.execute(
        text("SELECT id, resolved, user_id FROM escalation_events WHERE id::text = :eid"),
        {"eid": escalation_id},
    ).mappings().first()
    if not row:
        return "not_found"
    r = dict(row)
    if str(r["user_id"]) != user_id:
        return "forbidden"
    if r["resolved"]:
        return "already_resolved"
    db.execute(
        text("UPDATE escalation_events SET resolved = TRUE, resolved_at = NOW(), stage = 'cancelled' WHERE id::text = :eid"),
        {"eid": escalation_id},
    )
    db.commit()
    return "cancelled"


def is_on_vacation(db, user_id: str) -> bool:
    row = db.execute(
        text("SELECT vacation_start, vacation_end FROM users WHERE id::text = :uid"),
        {"uid": user_id},
    ).mappings().first()
    if not row:
        return False
    r = dict(row)
    if not r.get("vacation_start") or not r.get("vacation_end"):
        return False
    now = datetime.now(timezone.utc)
    return r["vacation_start"] <= now <= r["vacation_end"]


def log_audit_event(db, user_id: str, event_type: str, details: dict = None):
    db.execute(
        text("INSERT INTO audit_log (user_id, event_type, details) VALUES (:uid, :etype, CAST(:details AS jsonb))"),
        {"uid": user_id, "etype": event_type, "details": json.dumps(details or {})},
    )
    db.commit()


def get_audit_log(db, user_id: str, limit: int = 100):
    rows = db.execute(
        text("SELECT event_type, details, created_at FROM audit_log WHERE user_id::text = :uid ORDER BY created_at DESC LIMIT :lim"),
        {"uid": user_id, "lim": limit},
    ).mappings().all()
    return [dict(r) for r in rows]


def update_checkin_note(db, user_id: str, note: str):
    today = date.today()
    db.execute(
        text("UPDATE checkins SET note = :note WHERE user_id = :uid AND checked_in_at::date = :today"),
        {"note": note[:280], "uid": user_id, "today": today},
    )
    db.commit()


def get_random_checkin_message(db):
    row = db.execute(
        text("SELECT text FROM notification_messages WHERE category = 'checkin' ORDER BY RANDOM() LIMIT 1")
    ).first()
    return row[0] if row else "Still Here? Time to check in!"


def get_random_prompt(db):
    row = db.execute(
        text("SELECT text FROM checkin_prompts ORDER BY RANDOM() LIMIT 1")
    ).first()
    return row[0] if row else None


def get_trusted_circle(db, user_id: str):
    rows = db.execute(
        text("""
            SELECT ec.id, ec.name, ec.phone, ec.email, ec.created_at,
                   COUNT(cc.id) AS times_confirmed,
                   MAX(cc.confirmed_at) AS last_confirmed_at
            FROM emergency_contacts ec
            LEFT JOIN contact_confirmations cc ON cc.contact_id = ec.id
            LEFT JOIN escalation_events ee ON cc.escalation_event_id = ee.id AND ee.stage NOT IN ('dry_run', 'cancelled')
            WHERE ec.user_id = :uid
            GROUP BY ec.id, ec.name, ec.phone, ec.email, ec.created_at
            ORDER BY ec.priority
        """),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def get_annual_report(db, user_id: str):
    from datetime import date
    year_start = date(date.today().year, 1, 1)
    total = db.execute(
        text("SELECT COUNT(*) FROM checkins WHERE user_id = :uid AND checked_in_at::date >= :year_start"),
        {"uid": user_id, "year_start": year_start},
    ).scalar() or 0
    longest = db.execute(
        text("""
            WITH dates AS (SELECT DISTINCT checked_in_at::date AS d FROM checkins WHERE user_id = :uid AND checked_in_at::date >= :year_start)
            SELECT MAX(streak) FROM (
                SELECT COUNT(*) AS streak FROM (
                    SELECT d, d - ROW_NUMBER() OVER (ORDER BY d)::int AS grp FROM dates
                ) sub GROUP BY grp
            ) streaks
        """),
        {"uid": user_id, "year_start": year_start},
    ).scalar() or 0
    current_streak = get_streak(db, user_id)
    by_month = db.execute(
        text("SELECT EXTRACT(MONTH FROM checked_in_at)::int AS m, COUNT(*) AS c FROM checkins WHERE user_id = :uid AND checked_in_at::date >= :year_start GROUP BY m ORDER BY m"),
        {"uid": user_id, "year_start": year_start},
    ).mappings().all()
    milestones = []
    for m in [7, 30, 100, 365, 500, 1000]:
        if longest >= m:
            milestones.append(m)
    return {
        "year": date.today().year,
        "total_checkins": total,
        "longest_streak": longest,
        "current_streak": current_streak,
        "by_month": {r["m"]: r["c"] for r in by_month},
        "milestones": milestones,
    }


def create_mutual_pair(db, inviter_id: str, invitee_id: str):
    a, b = sorted([inviter_id, invitee_id])
    result = db.execute(
        text(
            "INSERT INTO mutual_pairs (user_a, user_b, status) VALUES (:a, :b, 'pending') RETURNING id, user_a, user_b, status, created_at, accepted_at, paused_at"
        ),
        {"a": a, "b": b},
    ).mappings().first()
    db.commit()
    return dict(result) if result else None


def get_mutual_pairs(db, user_id: str):
    rows = db.execute(
        text(
            "SELECT * FROM mutual_pairs WHERE user_a::text = :uid OR user_b::text = :uid ORDER BY created_at DESC"
        ),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def get_mutual_pair(db, pair_id: str):
    row = db.execute(
        text("SELECT * FROM mutual_pairs WHERE id::text = :pid"),
        {"pid": pair_id},
    ).mappings().first()
    return dict(row) if row else None


def accept_mutual_pair(db, pair_id: str, user_id: str):
    row = db.execute(
        text(
            "SELECT * FROM mutual_pairs WHERE id::text = :pid AND status = 'pending'"
        ),
        {"pid": pair_id},
    ).mappings().first()
    if not row:
        return None
    r = dict(row)
    if str(r["user_b"]) != user_id:
        return None
    db.execute(
        text(
            "UPDATE mutual_pairs SET status = 'active', accepted_at = NOW() WHERE id::text = :pid"
        ),
        {"pid": pair_id},
    )
    db.commit()
    return True


def decline_mutual_pair(db, pair_id: str, user_id: str):
    pair = get_mutual_pair(db, pair_id)
    if not pair:
        return None
    if str(pair["user_a"]) != user_id and str(pair["user_b"]) != user_id:
        return None
    db.execute(
        text("UPDATE mutual_pairs SET status = 'declined' WHERE id::text = :pid"),
        {"pid": pair_id},
    )
    db.commit()
    return True


def pause_mutual_pair(db, pair_id: str, user_id: str):
    pair = get_mutual_pair(db, pair_id)
    if not pair or pair["status"] != "active":
        return None
    if str(pair["user_a"]) != user_id and str(pair["user_b"]) != user_id:
        return None
    db.execute(
        text(
            "UPDATE mutual_pairs SET status = 'paused', paused_at = NOW() WHERE id::text = :pid"
        ),
        {"pid": pair_id},
    )
    db.commit()
    return True


def resume_mutual_pair(db, pair_id: str, user_id: str):
    pair = get_mutual_pair(db, pair_id)
    if not pair or pair["status"] != "paused":
        return None
    if str(pair["user_a"]) != user_id and str(pair["user_b"]) != user_id:
        return None
    db.execute(
        text("UPDATE mutual_pairs SET status = 'active' WHERE id::text = :pid"),
        {"pid": pair_id},
    )
    db.commit()
    return True


def end_mutual_pair(db, pair_id: str, user_id: str):
    pair = get_mutual_pair(db, pair_id)
    if not pair:
        return None
    if str(pair["user_a"]) != user_id and str(pair["user_b"]) != user_id:
        return None
    db.execute(
        text("DELETE FROM mutual_pairs WHERE id::text = :pid"),
        {"pid": pair_id},
    )
    db.commit()
    return True


def get_buddy_status(db, user_id: str):
    rows = db.execute(
        text(
            "SELECT * FROM mutual_pairs WHERE status = 'active' AND (user_a::text = :uid OR user_b::text = :uid)"
        ),
        {"uid": user_id},
    ).mappings().all()
    result = []
    for r in rows:
        r = dict(r)
        buddy_id = str(r["user_b"]) if str(r["user_a"]) == user_id else str(r["user_a"])
        buddy = get_user(db, buddy_id)
        if not buddy:
            continue
        checkin_row = db.execute(
            text(
                "SELECT checked_in_at FROM checkins WHERE user_id::text = :bid ORDER BY checked_in_at DESC LIMIT 1"
            ),
            {"bid": buddy_id},
        ).first()
        today = date.today()
        status = "green"
        if checkin_row and checkin_row[0]:
            checkin_date = checkin_row[0].date() if hasattr(checkin_row[0], 'date') else checkin_row[0]
            if checkin_date != today:
                status = "yellow"
        else:
            status = "red"
        result.append({
            "pair_id": str(r["id"]),
            "buddy_id": buddy_id,
            "buddy_name": buddy.get("name", buddy.get("email", "Buddy")),
            "buddy_email": buddy.get("email", ""),
            "status": status,
        })
    return result


def create_group(db, name: str, creator_id: str):
    result = db.execute(
        text("INSERT INTO groups (name, created_by) VALUES (:name, :cid) RETURNING id"),
        {"name": name, "cid": creator_id},
    ).first()
    group_id = str(result[0])
    db.execute(
        text("INSERT INTO group_members (group_id, user_id, role) VALUES (:gid, :uid, 'admin')"),
        {"gid": group_id, "uid": creator_id},
    )
    db.commit()
    return group_id


def get_user_groups(db, user_id: str):
    rows = db.execute(
        text("""
            SELECT g.id, g.name, g.is_active, g.created_at
            FROM groups g JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.user_id::text = :uid AND g.is_active = true
            ORDER BY g.created_at DESC
        """),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def get_group(db, group_id: str):
    row = db.execute(
        text("SELECT * FROM groups WHERE id::text = :gid"),
        {"gid": group_id},
    ).mappings().first()
    if not row:
        return None
    group = dict(row)
    members = db.execute(
        text("""
            SELECT gm.user_id, gm.role, gm.joined_at
            FROM group_members gm WHERE gm.group_id::text = :gid
            ORDER BY gm.joined_at
        """),
        {"gid": group_id},
    ).mappings().all()
    group["members"] = [dict(m) for m in members]
    return group


def add_group_member(db, group_id: str, user_id: str, role: str = "member"):
    db.execute(
        text("""
            INSERT INTO group_members (group_id, user_id, role)
            VALUES (:gid, :uid, :role) ON CONFLICT (group_id, user_id) DO NOTHING
        """),
        {"gid": group_id, "uid": user_id, "role": role},
    )
    db.commit()


def remove_group_member(db, group_id: str, user_id: str):
    db.execute(
        text("DELETE FROM group_members WHERE group_id::text = :gid AND user_id::text = :uid"),
        {"gid": group_id, "uid": user_id},
    )
    db.commit()


def create_family(db, name: str, admin_user_id: str):
    row = db.execute(
        text("SELECT has_paid FROM users WHERE id::text = :uid"),
        {"uid": admin_user_id},
    ).mappings().first()
    if not row or not row["has_paid"]:
        raise PermissionError("has_paid required")
    result = db.execute(
        text("INSERT INTO families (name, admin_user_id) VALUES (:name, :uid) RETURNING id"),
        {"name": name, "uid": admin_user_id},
    ).first()
    family_id = str(result[0])
    db.execute(
        text("INSERT INTO family_members (family_id, user_id, role) VALUES (:fid, :uid, 'admin')"),
        {"fid": family_id, "uid": admin_user_id},
    )
    db.execute(
        text("UPDATE users SET family_id = :fid WHERE id::text = :uid"),
        {"fid": family_id, "uid": admin_user_id},
    )
    db.commit()
    return family_id


def get_family(db, family_id: str):
    row = db.execute(
        text("SELECT * FROM families WHERE id::text = :fid"),
        {"fid": family_id},
    ).mappings().first()
    if not row:
        return None
    family = dict(row)
    members = db.execute(
        text("""
            SELECT fm.user_id, fm.role, fm.joined_at, u.email, u.name
            FROM family_members fm JOIN users u ON fm.user_id = u.id
            WHERE fm.family_id::text = :fid ORDER BY fm.joined_at
        """),
        {"fid": family_id},
    ).mappings().all()
    family["members"] = [dict(m) for m in members]
    return family


def get_user_family(db, user_id: str):
    row = db.execute(
        text("""
            SELECT f.* FROM families f
            JOIN family_members fm ON f.id = fm.family_id
            WHERE fm.user_id::text = :uid
        """),
        {"uid": user_id},
    ).mappings().first()
    return dict(row) if row else None


def create_family_invite(db, family_id: str, email: str):
    count = db.execute(
        text("SELECT COUNT(*) FROM family_members WHERE family_id::text = :fid"),
        {"fid": family_id},
    ).scalar()
    row = db.execute(
        text("SELECT max_seats FROM families WHERE id::text = :fid"),
        {"fid": family_id},
    ).mappings().first()
    if row and count >= row["max_seats"]:
        raise ValueError("Family is full")
    result = db.execute(
        text("INSERT INTO family_invites (family_id, email) VALUES (:fid, :email) RETURNING token"),
        {"fid": family_id, "email": email},
    ).first()
    db.commit()
    return result[0]


def get_family_invite(db, token: str):
    row = db.execute(
        text("SELECT * FROM family_invites WHERE token = :token AND used_at IS NULL AND expires_at > NOW()"),
        {"token": token},
    ).mappings().first()
    return dict(row) if row else None


def join_family(db, token: str, user_id: str):
    invite = get_family_invite(db, token)
    if not invite:
        raise ValueError("Invalid or expired invite")
    existing = db.execute(
        text("SELECT 1 FROM family_members WHERE user_id::text = :uid LIMIT 1"),
        {"uid": user_id},
    ).first()
    if existing:
        raise ValueError("Already in a family")
    family_id = invite["family_id"]
    db.execute(
        text("INSERT INTO family_members (family_id, user_id, role) VALUES (:fid, :uid, 'member')"),
        {"fid": family_id, "uid": user_id},
    )
    db.execute(
        text("UPDATE users SET family_id = :fid WHERE id::text = :uid"),
        {"fid": family_id, "uid": user_id},
    )
    db.execute(
        text("UPDATE family_invites SET used_at = NOW() WHERE token = :token"),
        {"token": token},
    )
    db.commit()
    return {"family_id": str(family_id)}


def remove_family_member(db, family_id: str, user_id: str, admin_id: str):
    row = db.execute(
        text("SELECT * FROM families WHERE id::text = :fid AND admin_user_id::text = :aid"),
        {"fid": family_id, "aid": admin_id},
    ).mappings().first()
    if not row:
        raise PermissionError("Only admin can remove members")
    db.execute(
        text("DELETE FROM family_members WHERE family_id::text = :fid AND user_id::text = :uid"),
        {"fid": family_id, "uid": user_id},
    )
    db.execute(
        text("UPDATE users SET family_id = NULL WHERE id::text = :uid"),
        {"uid": user_id},
    )
    db.commit()


def leave_family(db, family_id: str, user_id: str):
    row = db.execute(
        text("SELECT admin_user_id FROM families WHERE id::text = :fid"),
        {"fid": family_id},
    ).mappings().first()
    if row and str(row["admin_user_id"]) == user_id:
        disband_family(db, family_id, user_id)
        return
    db.execute(
        text("DELETE FROM family_members WHERE family_id::text = :fid AND user_id::text = :uid"),
        {"fid": family_id, "uid": user_id},
    )
    db.execute(
        text("UPDATE users SET family_id = NULL WHERE id::text = :uid"),
        {"uid": user_id},
    )
    db.commit()


def disband_family(db, family_id: str, admin_id: str):
    row = db.execute(
        text("SELECT admin_user_id FROM families WHERE id::text = :fid"),
        {"fid": family_id},
    ).mappings().first()
    if not row or str(row["admin_user_id"]) != admin_id:
        raise PermissionError("Only admin can disband")
    db.execute(
        text("UPDATE users SET family_id = NULL WHERE family_id::text = :fid"),
        {"fid": family_id},
    )
    db.execute(
        text("DELETE FROM family_members WHERE family_id::text = :fid"),
        {"fid": family_id},
    )
    db.execute(
        text("DELETE FROM family_invites WHERE family_id::text = :fid"),
        {"fid": family_id},
    )
    db.execute(
        text("DELETE FROM families WHERE id::text = :fid"),
        {"fid": family_id},
    )
    db.commit()


def get_family_status(db, family_id: str):
    members = db.execute(
        text("""
            SELECT fm.user_id, fm.role, u.email, u.name,
                   (SELECT checked_in_at FROM checkins WHERE user_id = fm.user_id ORDER BY checked_in_at DESC LIMIT 1) AS last_checkin
            FROM family_members fm JOIN users u ON fm.user_id = u.id
            WHERE fm.family_id::text = :fid ORDER BY fm.joined_at
        """),
        {"fid": family_id},
    ).mappings().all()
    result = []
    for m in members:
        m = dict(m)
        m["streak"] = get_streak(db, str(m["user_id"]))
        m["dormant"] = m["streak"] == 0
        result.append(m)
    return {"members": result}


def get_group_member_count(db, group_id: str) -> int:
    return db.execute(
        text("SELECT COUNT(*) FROM group_members WHERE group_id::text = :gid"),
        {"gid": group_id},
    ).scalar()


def disband_group(db, group_id: str):
    db.execute(
        text("UPDATE groups SET is_active = false WHERE id::text = :gid"),
        {"gid": group_id},
    )
    db.execute(
        text("DELETE FROM group_members WHERE group_id::text = :gid"),
        {"gid": group_id},
    )
    db.commit()


def create_portal_token(db, contact_id):
    row = db.execute(
        text("INSERT INTO contact_portal_tokens (contact_id) VALUES (:cid) RETURNING token"),
        {"cid": contact_id},
    ).first()
    db.commit()
    return row[0]


def get_portal_token(db, token: str):
    row = db.execute(
        text("SELECT * FROM contact_portal_tokens WHERE token = :token AND revoked = false"),
        {"token": token},
    ).mappings().first()
    return dict(row) if row else None


def refresh_portal_token(db, token: str):
    old = db.execute(
        text("SELECT contact_id FROM contact_portal_tokens WHERE token = :token AND revoked = false"),
        {"token": token},
    ).first()
    if not old:
        return None
    contact_id = old[0]
    db.execute(
        text("UPDATE contact_portal_tokens SET revoked = true WHERE token = :token"),
        {"token": token},
    )
    row = db.execute(
        text("INSERT INTO contact_portal_tokens (contact_id) VALUES (:cid) RETURNING token"),
        {"cid": contact_id},
    ).first()
    db.commit()
    return row[0]


def revoke_portal_token(db, token: str):
    db.execute(
        text("UPDATE contact_portal_tokens SET revoked = true WHERE token = :token"),
        {"token": token},
    )
    db.commit()


def get_portal_status(db, contact_id):
    contact = db.execute(
        text("SELECT user_id FROM emergency_contacts WHERE id = :cid"),
        {"cid": contact_id},
    ).mappings().first()
    if not contact:
        return None
    user_id = str(contact["user_id"])
    user = get_user(db, user_id)
    if not user:
        return None
    last = db.execute(
        text("SELECT checked_in_at FROM checkins WHERE user_id::text = :uid ORDER BY checked_in_at DESC LIMIT 1"),
        {"uid": user_id},
    ).first()
    streak = get_streak(db, user_id)
    esc = get_active_escalation(db, user_id)
    dormant = not last or (datetime.now(timezone.utc) - last[0]).days > 7
    return {
        "user_name": user.get("name", user.get("email", "User")),
        "last_checkin": last[0].isoformat() if last else None,
        "streak": streak,
        "escalation_active": esc is not None,
        "is_dormant": dormant,
    }


def update_portal_last_accessed(db, token: str):
    db.execute(
        text("UPDATE contact_portal_tokens SET last_accessed = NOW() WHERE token = :token"),
        {"token": token},
    )
    db.commit()


def create_group_ping(db, group_id: str, target_user_id: str):
    result = db.execute(
        text("""
            INSERT INTO group_pings (group_id, target_user_id)
            VALUES (:gid, :uid) RETURNING id
        """),
        {"gid": group_id, "uid": target_user_id},
    ).first()
    db.commit()
    return str(result[0])


def get_active_pings(db, user_id: str):
    rows = db.execute(
        text("""
            SELECT gp.* FROM group_pings gp
            JOIN group_members gm ON gp.group_id = gm.group_id
            WHERE gm.user_id::text = :uid AND gp.resolved = false
            ORDER BY gp.sent_at DESC
        """),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def resolve_group_ping(db, ping_id: str, resolver_id: str):
    db.execute(
        text("""
            UPDATE group_pings SET resolved = true, resolved_by = :rid, resolved_at = NOW()
            WHERE id::text = :pid
        """),
        {"pid": ping_id, "rid": resolver_id},
    )
    db.commit()


def register_sensor(db, user_id: str, sensor_type: str, sensor_id: str):
    row = db.execute(
        text("""
            INSERT INTO sensor_webhooks (user_id, sensor_type, sensor_id)
            VALUES (:uid, :stype, :sid)
            ON CONFLICT (user_id, sensor_id) DO NOTHING
            RETURNING id, user_id, sensor_type, sensor_id, last_reading, last_reading_at, created_at
        """),
        {"uid": user_id, "stype": sensor_type, "sid": sensor_id},
    ).mappings().first()
    db.commit()
    return dict(row) if row else None


def update_sensor_reading(db, user_id: str, sensor_id: str, reading_json: dict):
    db.execute(
        text("""
            UPDATE sensor_webhooks
            SET last_reading = CAST(:reading AS jsonb), last_reading_at = NOW()
            WHERE user_id::text = :uid AND sensor_id = :sid
        """),
        {"uid": user_id, "sid": sensor_id, "reading": json.dumps(reading_json)},
    )
    db.commit()


def get_user_sensors(db, user_id: str):
    rows = db.execute(
        text("SELECT * FROM sensor_webhooks WHERE user_id::text = :uid ORDER BY created_at DESC"),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def delete_sensor(db, sensor_id_internal: str, user_id: str):
    db.execute(
        text("DELETE FROM sensor_webhooks WHERE id::text = :sid AND user_id::text = :uid"),
        {"sid": sensor_id_internal, "uid": user_id},
    )
    db.commit()


def get_user_by_alexa_id(db, alexa_user_id: str):
    row = db.execute(
        text("SELECT * FROM users WHERE alexa_user_id = :aid"),
        {"aid": alexa_user_id},
    ).mappings().first()
    return dict(row) if row else None


def auto_checkin_if_active(db, user_id: str, method: str) -> bool:
    if has_checked_in_today(db, user_id):
        return False
    now_utc = datetime.now(timezone.utc)
    user = get_user(db, user_id)
    if not user:
        return False
    checkin_time = user.get("checkin_time")
    grace_minutes = user.get("grace_minutes", 60)
    if not checkin_time:
        return False
    ct = checkin_time if isinstance(checkin_time, time) else now_utc.time()
    now_mins = now_utc.hour * 60 + now_utc.minute
    ct_mins = ct.hour * 60 + ct.minute
    window_start = ct_mins
    window_end = ct_mins + grace_minutes
    if now_mins < window_start or now_mins > window_end:
        return False
    log_checkin(db, user_id, method)
    log_audit_event(db, user_id, "auto_checkin", {"method": method})
    return True


def create_api_key(db, user_id: str, name: str):
    from api_key_auth import generate_api_key, hash_api_key
    plaintext = generate_api_key()
    key_hash = hash_api_key(plaintext)
    result = db.execute(
        text("INSERT INTO api_keys (user_id, key_hash, name) VALUES (:uid, :kh, :name) RETURNING id"),
        {"uid": user_id, "kh": key_hash, "name": name},
    ).first()
    db.commit()
    return str(result[0]), plaintext


def get_api_keys(db, user_id: str):
    rows = db.execute(
        text("SELECT id, name, last_used, created_at FROM api_keys WHERE user_id::text = :uid ORDER BY created_at DESC"),
        {"uid": user_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def lookup_api_key(db, key_hash: str):
    row = db.execute(
        text("""SELECT ak.id as key_id, u.id, u.email, u.password_hash
                FROM api_keys ak JOIN users u ON ak.user_id = u.id
                WHERE ak.key_hash = :kh"""),
        {"kh": key_hash},
    ).mappings().first()
    return dict(row) if row else None


def delete_api_key(db, key_id: str, user_id: str):
    result = db.execute(
        text("DELETE FROM api_keys WHERE id::text = :kid AND user_id::text = :uid"),
        {"kid": key_id, "uid": user_id},
    )
    db.commit()
    return result.rowcount > 0


def touch_api_key(db, key_id: str):
    db.execute(
        text("UPDATE api_keys SET last_used = NOW() WHERE id::text = :kid"),
        {"kid": key_id},
    )
    db.commit()
