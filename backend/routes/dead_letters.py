import logging

from fastapi import APIRouter, Depends, HTTPException
import pydantic
from pydantic import BaseModel

from db import (
    get_session,
    get_dead_letters,
    create_dead_letter,
    update_dead_letter,
    delete_dead_letter,
    get_dead_letter,
)
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dead-letters", tags=["dead-letters"])


class DeadLetterIn(BaseModel):
    subject: str = pydantic.Field(max_length=200)
    body: str = pydantic.Field(max_length=5000)
    trigger_days: int = 30
    recipient_type: str = "contacts"
    recipient_email: str = None


class DeadLetterPatch(BaseModel):
    subject: str = pydantic.Field(None, max_length=200)
    body: str = pydantic.Field(None, max_length=5000)
    trigger_days: int = None
    recipient_type: str = None
    recipient_email: str = None


@router.get("")
def list_dead_letters(user=Depends(get_current_user), db=Depends(get_session)):
    """List all dead letters for the current user."""
    return get_dead_letters(db, str(user["id"]))


@router.post("")
def create_dead_letter_endpoint(body: DeadLetterIn, user=Depends(get_current_user), db=Depends(get_session)):
    """Create a new dead letter."""
    if not body.subject or not body.body:
        raise HTTPException(status_code=400, detail="Subject and body are required")
    if body.trigger_days < 7 or body.trigger_days > 365:
        raise HTTPException(status_code=400, detail="Trigger days must be between 7 and 365")
    if body.recipient_type not in ("contacts", "email"):
        raise HTTPException(status_code=400, detail="Recipient type must be 'contacts' or 'email'")
    if body.recipient_type == "email" and not body.recipient_email:
        raise HTTPException(status_code=400, detail="Recipient email is required for email recipient type")

    letter_id = create_dead_letter(
        db,
        str(user["id"]),
        body.subject,
        body.body,
        body.trigger_days,
        body.recipient_type,
        body.recipient_email,
    )
    return {"id": letter_id, "message": "Dead letter created"}


@router.get("/{letter_id}")
def get_dead_letter_endpoint(letter_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    """Get a specific dead letter."""
    letter = get_dead_letter(db, letter_id, str(user["id"]))
    if not letter:
        raise HTTPException(status_code=404, detail="Dead letter not found")
    return letter


@router.patch("/{letter_id}")
def update_dead_letter_endpoint(letter_id: str, body: DeadLetterPatch, user=Depends(get_current_user), db=Depends(get_session)):
    """Update a dead letter."""
    letter = get_dead_letter(db, letter_id, str(user["id"]))
    if not letter:
        raise HTTPException(status_code=404, detail="Dead letter not found")

    fields = {}
    if body.subject is not None:
        fields["subject"] = body.subject
    if body.body is not None:
        fields["body"] = body.body
    if body.trigger_days is not None:
        if body.trigger_days < 7 or body.trigger_days > 365:
            raise HTTPException(status_code=400, detail="Trigger days must be between 7 and 365")
        fields["trigger_days"] = body.trigger_days
    if body.recipient_type is not None:
        if body.recipient_type not in ("contacts", "email"):
            raise HTTPException(status_code=400, detail="Recipient type must be 'contacts' or 'email'")
        fields["recipient_type"] = body.recipient_type
    if body.recipient_email is not None:
        fields["recipient_email"] = body.recipient_email

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_dead_letter(db, letter_id, str(user["id"]), **fields)
    return {"message": "Dead letter updated"}


@router.delete("/{letter_id}")
def delete_dead_letter_endpoint(letter_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    """Delete a dead letter."""
    letter = get_dead_letter(db, letter_id, str(user["id"]))
    if not letter:
        raise HTTPException(status_code=404, detail="Dead letter not found")

    delete_dead_letter(db, letter_id, str(user["id"]))
    return {"message": "Dead letter deleted"}
