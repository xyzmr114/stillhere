import os
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import settings

DEMO_EMAILS = ["demo1@stillhere.hack", "demo2@stillhere.hack"]

USERS = [
    {
        "email": "demo1@stillhere.hack",
        "name": "Alice (Demo)",
        "password": "demo1234",
        "phone": os.getenv("DEMO_PHONE_1", "+15551234567"),
        "grace_minutes": 60,
        "checkin_offset_minutes": 1,
    },
    {
        "email": "demo2@stillhere.hack",
        "name": "Bob (Demo)",
        "password": "demo1234",
        "phone": os.getenv("DEMO_PHONE_2", "+15559876543"),
        "grace_minutes": 1,
        "checkin_offset_minutes": 2,
    },
]


def main():
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    now = datetime.now(timezone.utc)
    user_ids = {}

    for u in USERS:
        existing = db.execute(
            text("SELECT id FROM users WHERE email = :email"), {"email": u["email"]}
        ).mappings().first()
        if existing:
            print(f"[skip] {u['name']} already exists ({u['email']})")
            user_ids[u["email"]] = existing["id"]
            continue

        pw_hash = bcrypt.hashpw(u["password"].encode(), bcrypt.gensalt()).decode()
        checkin_time = (now + timedelta(minutes=u["checkin_offset_minutes"])).replace(second=0, microsecond=0).time()

        result = db.execute(
            text(
                "INSERT INTO users (email, name, password_hash, phone, grace_minutes, checkin_time) "
                "VALUES (:email, :name, :pw, :phone, :grace, :ct) RETURNING id"
            ),
            {
                "email": u["email"],
                "name": u["name"],
                "pw": pw_hash,
                "phone": u["phone"],
                "grace": u["grace_minutes"],
                "ct": checkin_time,
            },
        ).first()
        db.commit()
        user_ids[u["email"]] = result[0]
        print(f"[created] {u['name']} — id={result[0]} checkin_time={checkin_time}")

    contacts = [
        {"user_email": "demo1@stillhere.hack", "name": "Bob (Demo Contact)", "phone": USERS[1]["phone"], "priority": 1},
        {"user_email": "demo2@stillhere.hack", "name": "Alice (Demo Contact)", "phone": USERS[0]["phone"], "priority": 1},
    ]

    for c in contacts:
        uid = user_ids[c["user_email"]]
        existing = db.execute(
            text("SELECT id FROM emergency_contacts WHERE user_id = :uid AND phone = :phone"),
            {"uid": uid, "phone": c["phone"]},
        ).mappings().first()
        if existing:
            print(f"[skip] contact {c['name']} for {c['user_email']} already exists")
            continue
        db.execute(
            text(
                "INSERT INTO emergency_contacts (user_id, name, phone, priority) "
                "VALUES (:uid, :name, :phone, :priority)"
            ),
            {"uid": uid, "name": c["name"], "phone": c["phone"], "priority": c["priority"]},
        )
        db.commit()
        print(f"[created] contact {c['name']} for {c['user_email']}")

    db.close()

    print()
    print("=" * 60)
    print("  STILL HERE — DEMO DATA SEEDED")
    print("=" * 60)
    print()
    print("  Credentials:")
    print("    demo1@stillhere.hack / demo1234  — Alice (checks in fine)")
    print("    demo2@stillhere.hack / demo1234  — Bob   (MISSES check-in)")
    print()
    print("  What to expect:")
    print("    1. Alice: grace=60min, checkin triggers in ~1 min")
    print("       → She checks in on time. No escalation.")
    print("    2. Bob:   grace=1min,  checkin triggers in ~2 min")
    print("       → He does NOT check in. Escalation fires after 1 min.")
    print("       → Alice gets an SMS alert (Bob's emergency contact).")
    print()
    print("  To reset:  python reset_demo.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
