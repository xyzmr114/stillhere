from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_session
from dependencies import get_current_user

router = APIRouter(prefix="/mutual", tags=["mutual"])


class InviteRequest(BaseModel):
    email: str


@router.post("/invite")
def invite_buddy(body: InviteRequest, user=Depends(get_current_user), db=Depends(get_session)):
    from db import get_user_by_email, create_mutual_pair, get_mutual_pairs

    uid = str(user["id"])
    if user["email"] == body.email:
        raise HTTPException(status_code=400, detail="Cannot invite yourself")
    buddy = get_user_by_email(db, body.email)
    if not buddy:
        raise HTTPException(status_code=404, detail="User not found")
    buddy_id = str(buddy["id"])
    existing = get_mutual_pairs(db, uid)
    for p in existing:
        other = str(p["user_a"]) if str(p["user_b"]) == uid else str(p["user_b"])
        if other == buddy_id and p["status"] in ("pending", "active", "paused"):
            raise HTTPException(status_code=400, detail="Already paired with this user")
    pair = create_mutual_pair(db, uid, buddy_id)
    return {"status": "invited", "pair_id": str(pair["id"])}


@router.get("/pending")
def pending_pairs(user=Depends(get_current_user), db=Depends(get_session)):
    from db import get_mutual_pairs

    uid = str(user["id"])
    pairs = get_mutual_pairs(db, uid)
    pending = [p for p in pairs if p["status"] == "pending"]
    received = []
    sent = []
    for p in pending:
        if str(p["user_b"]) == uid:
            received.append(p)
        else:
            sent.append(p)
    return {"received": received, "sent": sent}


@router.post("/accept/{pair_id}")
def accept_invite(pair_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    from db import accept_mutual_pair

    result = accept_mutual_pair(db, pair_id, str(user["id"]))
    if not result:
        raise HTTPException(status_code=400, detail="Cannot accept this invite")
    return {"status": "accepted"}


@router.post("/decline/{pair_id}")
def decline_invite(pair_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    from db import decline_mutual_pair

    result = decline_mutual_pair(db, pair_id, str(user["id"]))
    if not result:
        raise HTTPException(status_code=400, detail="Cannot decline this invite")
    return {"status": "declined"}


@router.post("/pause/{pair_id}")
def pause_pair(pair_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    from db import pause_mutual_pair

    result = pause_mutual_pair(db, pair_id, str(user["id"]))
    if not result:
        raise HTTPException(status_code=400, detail="Cannot pause this pair")
    return {"status": "paused"}


@router.post("/resume/{pair_id}")
def resume_pair(pair_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    from db import resume_mutual_pair

    result = resume_mutual_pair(db, pair_id, str(user["id"]))
    if not result:
        raise HTTPException(status_code=400, detail="Cannot resume this pair")
    return {"status": "active"}


@router.post("/end/{pair_id}")
def end_pair(pair_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    from db import end_mutual_pair

    result = end_mutual_pair(db, pair_id, str(user["id"]))
    if not result:
        raise HTTPException(status_code=400, detail="Cannot end this pair")
    return {"status": "ended"}


@router.get("/status")
def buddy_status(user=Depends(get_current_user), db=Depends(get_session)):
    from db import get_buddy_status

    buddies = get_buddy_status(db, str(user["id"]))
    return {"buddies": buddies}
