import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from db import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["contact"])


class ContactForm(BaseModel):
    name: str
    email: str
    message: str


@router.post("/api/contact")
def submit_contact(form: ContactForm):
    db = SessionLocal()
    try:
        db.execute(
            text(
                "INSERT INTO contact_submissions (name, email, message) "
                "VALUES (:name, :email, :message)"
            ),
            {"name": form.name, "email": form.email, "message": form.message},
        )
        db.commit()
    finally:
        db.close()
    return {"ok": True, "message": "Message received"}
