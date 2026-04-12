import hashlib
import secrets

from fastapi import Depends, Header
from fastapi.security import HTTPBearer

from db import get_session

_bearer = HTTPBearer(auto_error=False)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    return f"sh_live_{secrets.token_hex(32)}"


def get_api_key_user(api_key: str = Header(None, alias="X-API-Key"), db=Depends(get_session)):
    if not api_key:
        return None
    from db import lookup_api_key, touch_api_key
    key_hash = hash_api_key(api_key)
    result = lookup_api_key(db, key_hash)
    if not result:
        return None
    touch_api_key(db, str(result["key_id"]))
    return {k: v for k, v in result.items() if k != "key_id"}


def get_optional_user(creds=Depends(_bearer), db=Depends(get_session)):
    if not creds:
        return None
    try:
        from auth import decode_jwt
        payload = decode_jwt(creds.credentials)
        user_id = payload.get("sub")
    except Exception:
        return None
    from db import get_user
    return get_user(db, user_id)
