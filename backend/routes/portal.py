from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_session
from db import get_portal_token, get_portal_status, refresh_portal_token, revoke_portal_token, update_portal_last_accessed

router = APIRouter(prefix="/portal", tags=["portal"])


@router.get("/{token}")
def portal_status(token: str, db=Depends(get_session)):
    token_row = get_portal_token(db, token)
    if not token_row:
        raise HTTPException(status_code=404, detail="Token not found or revoked")
    status = get_portal_status(db, token_row["contact_id"])
    if not status:
        raise HTTPException(status_code=404, detail="Contact not found")
    update_portal_last_accessed(db, token)
    return status


@router.post("/{token}/refresh")
def portal_refresh(token: str, db=Depends(get_session)):
    new_token = refresh_portal_token(db, token)
    if not new_token:
        raise HTTPException(status_code=404, detail="Token not found or revoked")
    return {"token": new_token}


@router.post("/{token}/revoke")
def portal_revoke(token: str, db=Depends(get_session)):
    revoke_portal_token(db, token)
    return {"message": "Token revoked"}
