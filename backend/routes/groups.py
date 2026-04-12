from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import (
    get_session,
    create_group,
    get_user_groups,
    get_group,
    add_group_member,
    remove_group_member,
    get_group_member_count,
    disband_group,
    resolve_group_ping,
    get_user_by_email,
)
from dependencies import get_current_user

router = APIRouter(prefix="/groups", tags=["groups"])


class GroupIn(BaseModel):
    name: str


class InviteIn(BaseModel):
    email: str


@router.post("")
def create(body: GroupIn, user=Depends(get_current_user), db=Depends(get_session)):
    if len(body.name) > 50 or len(body.name.strip()) == 0:
        raise HTTPException(status_code=400, detail="Name must be 1-50 characters")
    gid = create_group(db, body.name.strip(), str(user["id"]))
    return {"id": gid, "message": "Group created"}


@router.get("")
def list_groups(user=Depends(get_current_user), db=Depends(get_session)):
    return get_user_groups(db, str(user["id"]))


@router.get("/pings")
def list_pings(user=Depends(get_current_user), db=Depends(get_session)):
    from db import get_active_pings
    return get_active_pings(db, str(user["id"]))


@router.get("/{group_id}")
def detail(group_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    group = get_group(db, group_id)
    if not group or not group.get("is_active"):
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.post("/{group_id}/invite")
def invite(group_id: str, body: InviteIn, user=Depends(get_current_user), db=Depends(get_session)):
    group = get_group(db, group_id)
    if not group or not group.get("is_active"):
        raise HTTPException(status_code=404, detail="Group not found")
    count = get_group_member_count(db, group_id)
    if count >= 10:
        raise HTTPException(status_code=400, detail="Group is full (max 10 members)")
    target = get_user_by_email(db, body.email)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if str(target["id"]) == str(user["id"]):
        raise HTTPException(status_code=400, detail="Cannot invite yourself")
    member_ids = [str(m["user_id"]) for m in group.get("members", [])]
    if str(target["id"]) in member_ids:
        raise HTTPException(status_code=400, detail="Already a member")
    add_group_member(db, group_id, str(target["id"]))
    return {"message": "Member added"}


@router.post("/{group_id}/join")
def join(group_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    group = get_group(db, group_id)
    if not group or not group.get("is_active"):
        raise HTTPException(status_code=404, detail="Group not found")
    count = get_group_member_count(db, group_id)
    if count >= 10:
        raise HTTPException(status_code=400, detail="Group is full")
    add_group_member(db, group_id, str(user["id"]))
    return {"message": "Joined group"}


@router.post("/{group_id}/leave")
def leave(group_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    group = get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    uid = str(user["id"])
    is_admin = any(
        str(m["user_id"]) == uid and m["role"] == "admin"
        for m in group.get("members", [])
    )
    if is_admin:
        others = [m for m in group.get("members", []) if str(m["user_id"]) != uid]
        if others:
            longest = min(others, key=lambda m: m["joined_at"])
            add_group_member(db, group_id, str(longest["user_id"]), role="admin")
    remove_group_member(db, group_id, uid)
    return {"message": "Left group"}


@router.delete("/{group_id}")
def disband(group_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    group = get_group(db, group_id)
    if not group or not group.get("is_active"):
        raise HTTPException(status_code=404, detail="Group not found")
    if str(group["created_by"]) != str(user["id"]):
        raise HTTPException(status_code=403, detail="Only admin can disband")
    disband_group(db, group_id)
    return {"message": "Group disbanded"}


@router.post("/pings/{ping_id}/resolve")
def resolve_ping(ping_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    resolve_group_ping(db, ping_id, str(user["id"]))
    return {"message": "Ping resolved"}
