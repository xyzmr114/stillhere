from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import settings

TABLES = [
    ("escalation_events", "user_id"),
    ("checkins", "user_id"),
    ("emergency_contacts", "user_id"),
    ("users", "id"),
]

DEMO_EMAILS = ["demo1@stillhere.hack", "demo2@stillhere.hack"]


def main():
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    user_ids = [
        row["id"]
        for row in db.execute(
            text("SELECT id FROM users WHERE email = ANY(:emails)"),
            {"emails": DEMO_EMAILS},
        ).mappings().all()
    ]

    if not user_ids:
        print("No demo data found. Nothing to reset.")
        db.close()
        return

    for table, col in TABLES:
        if table == "users":
            result = db.execute(
                text(f"DELETE FROM {table} WHERE id = ANY(:ids)"),
                {"ids": user_ids},
            )
        else:
            result = db.execute(
                text(f"DELETE FROM {table} WHERE user_id = ANY(:ids)"),
                {"ids": user_ids},
            )
        db.commit()
        print(f"[deleted] {result.rowcount} rows from {table}")

    db.close()
    print("\nDemo data reset complete.")


if __name__ == "__main__":
    main()
