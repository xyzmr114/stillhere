import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from db import get_session, get_contacts, add_contact, update_contact, delete_contact, create_portal_token
from dependencies import get_current_user
from limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contacts", tags=["contacts"])


class ContactIn(BaseModel):
    name: str
    phone: str
    email: str = None
    priority: int = 1


class ContactPatch(BaseModel):
    name: str = None
    phone: str = None
    email: str = None
    priority: int = None


@router.get("")
def list_contacts(user=Depends(get_current_user), db=Depends(get_session)):
    return get_contacts(db, str(user["id"]))


@router.post("")
@limiter.limit("10/minute")
def create_contact(request: Request, body: ContactIn, user=Depends(get_current_user), db=Depends(get_session)):
    # Auto-assign next priority if not explicitly set
    priority = body.priority
    if priority == 1:
        existing = get_contacts(db, str(user["id"]))
        priority = len(existing) + 1
    cid = add_contact(
        db,
        str(user["id"]),
        body.name,
        body.phone,
        body.email,
        priority,
    )
    portal_token = create_portal_token(db, cid)
    if body.email:
        try:
            from services.email_svc import send_contact_welcome_email
            send_contact_welcome_email(body.email, body.name, user["name"], portal_token)
        except Exception:
            logger.exception("Failed to send contact welcome email to %s for user %s", body.email, str(user["id"]))
    return {"id": cid, "portal_token": portal_token, "message": "Contact added"}


@router.patch("/{contact_id}")
def patch_contact(contact_id: str, body: ContactPatch, user=Depends(get_current_user), db=Depends(get_session)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_contact(db, contact_id, str(user["id"]), **fields)
    return {"message": "Contact updated"}


@router.delete("/{contact_id}")
def remove_contact(contact_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    delete_contact(db, contact_id, str(user["id"]))
    return {"message": "Contact deleted"}


class ReorderIn(BaseModel):
    order: list[str]  # list of contact IDs in desired priority order


@router.put("/reorder")
def reorder_contacts(body: ReorderIn, user=Depends(get_current_user), db=Depends(get_session)):
    uid = str(user["id"])
    for priority, contact_id in enumerate(body.order, start=1):
        update_contact(db, contact_id, uid, priority=priority)
    return {"message": "Contact order updated"}


@router.get("/circle")
def trusted_circle(user=Depends(get_current_user), db=Depends(get_session)):
    from db import get_trusted_circle
    circle = get_trusted_circle(db, str(user["id"]))
    return {"contacts": circle, "total": len(circle), "message": f"{len(circle)} {'person is' if len(circle) == 1 else 'people are'} watching out for you"}
