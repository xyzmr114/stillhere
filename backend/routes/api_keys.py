from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_session
from dependencies import get_current_user

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateApiKeyRequest(BaseModel):
    name: str = "Default"


@router.post("")
def create_key(body: CreateApiKeyRequest = None, user=Depends(get_current_user), db=Depends(get_session)):
    from db import create_api_key
    name = body.name if body else "Default"
    key_id, plaintext = create_api_key(db, str(user["id"]), name)
    return {"id": key_id, "key": plaintext, "name": name}


@router.get("")
def list_keys(user=Depends(get_current_user), db=Depends(get_session)):
    from db import get_api_keys
    keys = get_api_keys(db, str(user["id"]))
    return {"keys": keys}


@router.delete("/{key_id}")
def revoke_key(key_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    from db import delete_api_key
    deleted = delete_api_key(db, key_id, str(user["id"]))
    if not deleted:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"status": "deleted"}
