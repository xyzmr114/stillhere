import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from dependencies import get_current_user

router = APIRouter(prefix="/netcore", tags=["netcore"])

NCP2P = "http://127.0.0.1:8080"


async def _ncp2p(method: str, path: str, body=None):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            if method == "GET":
                r = await client.get(f"{NCP2P}{path}")
            elif method == "POST":
                r = await client.post(f"{NCP2P}{path}", json=body)
            elif method == "DELETE":
                r = await client.delete(f"{NCP2P}{path}")
            else:
                raise HTTPException(status_code=400, detail="unsupported method")
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Netcore client not running")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@router.get("/identity")
async def get_identity(user=Depends(get_current_user)):
    data = await _ncp2p("GET", "/v1/identity/peer-user")
    return data.get("peer_user", data)


@router.get("/device")
async def get_device(user=Depends(get_current_user)):
    data = await _ncp2p("GET", "/v1/this-device")
    return data.get("this_device", data)


@router.get("/peers")
async def get_peers(user=Depends(get_current_user)):
    data = await _ncp2p("GET", "/v1/peers")
    return {"peers": data.get("peers", [])}


@router.get("/peer-users")
async def get_peer_users(user=Depends(get_current_user)):
    data = await _ncp2p("GET", "/v1/peer-users")
    return {"peer_users": data.get("peer_users", [])}


class AddPeerRequest(BaseModel):
    version: int
    pub_key_b36: str
    data_key_b36: str


@router.post("/peer-users")
async def add_peer(body: AddPeerRequest, user=Depends(get_current_user)):
    return await _ncp2p("POST", "/v1/peer-users", body.model_dump())


@router.delete("/peer-users/{pub_key_b36}")
async def remove_peer(pub_key_b36: str, user=Depends(get_current_user)):
    return await _ncp2p("DELETE", f"/v1/peer-users/{pub_key_b36}")
