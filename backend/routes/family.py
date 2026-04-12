from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import (
    get_session,
    create_family,
    get_user_family,
    get_family,
    create_family_invite,
    get_family_invite,
    join_family,
    leave_family,
    remove_family_member,
    disband_family,
    get_family_status,
)
from dependencies import get_current_user

router = APIRouter(prefix="/family", tags=["family"])


class FamilyIn(BaseModel):
    name: str


class InviteIn(BaseModel):
    email: str


@router.post("")
def create(body: FamilyIn, user=Depends(get_current_user), db=Depends(get_session)):
    name = body.name.strip()
    if not name or len(name) > 100:
        raise HTTPException(status_code=400, detail="Name must be 1-100 characters")
    try:
        fid = create_family(db, name, str(user["id"]))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Payment required to create a family")
    return {"id": fid, "message": "Family created"}


@router.get("")
def get_my_family(user=Depends(get_current_user), db=Depends(get_session)):
    family = get_user_family(db, str(user["id"]))
    if not family:
        return {"family": None}
    full = get_family(db, family["id"])
    return {"family": full}


@router.post("/invite")
def invite(body: InviteIn, user=Depends(get_current_user), db=Depends(get_session)):
    family = get_user_family(db, str(user["id"]))
    if not family:
        raise HTTPException(status_code=404, detail="No family found")
    if str(family["admin_user_id"]) != str(user["id"]):
        raise HTTPException(status_code=403, detail="Only admin can invite")
    try:
        token = create_family_invite(db, family["id"], body.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"token": token, "message": "Invite created"}


@router.get("/join/{token}")
def preview_join(token: str, db=Depends(get_session)):
    invite = get_family_invite(db, token)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found or expired")
    family = get_family(db, invite["family_id"])
    return {"family_name": family["name"] if family else "Unknown", "email": invite["email"]}


@router.post("/join/{token}")
def accept_join(token: str, user=Depends(get_current_user), db=Depends(get_session)):
    try:
        result = join_family(db, token, str(user["id"]))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"family_id": result["family_id"], "message": "Joined family"}


@router.post("/leave")
def leave(user=Depends(get_current_user), db=Depends(get_session)):
    family = get_user_family(db, str(user["id"]))
    if not family:
        raise HTTPException(status_code=404, detail="No family to leave")
    leave_family(db, family["id"], str(user["id"]))
    return {"message": "Left family"}


@router.post("/members/{target_id}/remove")
def remove_member(target_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    family = get_user_family(db, str(user["id"]))
    if not family:
        raise HTTPException(status_code=404, detail="No family found")
    if str(family["admin_user_id"]) != str(user["id"]):
        raise HTTPException(status_code=403, detail="Only admin can remove members")
    if target_id == str(user["id"]):
        raise HTTPException(status_code=400, detail="Cannot remove admin")
    remove_family_member(db, family["id"], target_id, str(user["id"]))
    return {"message": "Member removed"}


@router.get("/status")
def status(user=Depends(get_current_user), db=Depends(get_session)):
    family = get_user_family(db, str(user["id"]))
    if not family:
        raise HTTPException(status_code=404, detail="No family found")
    if str(family["admin_user_id"]) != str(user["id"]):
        raise HTTPException(status_code=403, detail="Only admin can view status")
    return get_family_status(db, family["id"])


@router.delete("")
def disband(user=Depends(get_current_user), db=Depends(get_session)):
    family = get_user_family(db, str(user["id"]))
    if not family:
        raise HTTPException(status_code=404, detail="No family found")
    if str(family["admin_user_id"]) != str(user["id"]):
        raise HTTPException(status_code=403, detail="Only admin can disband")
    disband_family(db, family["id"], str(user["id"]))
    return {"message": "Family disbanded"}
