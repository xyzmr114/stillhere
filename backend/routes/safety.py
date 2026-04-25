from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from db import (
    get_session,
    lookup_non_emergency_number,
    search_non_emergency_numbers,
    save_user_address,
    get_user_non_emergency_number,
)
from dependencies import get_current_user
from limiter import limiter

router = APIRouter(prefix="/safety", tags=["safety"])


class AddressIn(BaseModel):
    address: str
    city: str
    state: str
    zip_code: str


class VerifyNumberIn(BaseModel):
    address: str
    city: str
    state: str
    zip_code: str
    non_emergency_number: str
    verified: bool = True


class SearchIn(BaseModel):
    query: str


@router.post("/lookup-non-emergency")
@limiter.limit("15/minute")
def lookup(request: Request, body: AddressIn, user=Depends(get_current_user), db=Depends(get_session)):
    """
    Look up the non-emergency number for a user's city/state.
    Returns the number if found, or null with a help link.
    """
    result = lookup_non_emergency_number(db, body.city, body.state)
    if result:
        return {
            "found": True,
            "phone": result["phone"],
            "department": result.get("department"),
            "source_url": result.get("source_url"),
            "message": (
                f"We found the non-emergency line for {body.city}, {body.state}: "
                f"{result['phone']} ({result.get('department', 'Police')}). "
                "Please verify this is correct for your area."
            ),
            "verify_url": result.get("source_url"),
        }
    return {
        "found": False,
        "phone": None,
        "message": (
            f"We don't have the non-emergency number for {body.city}, {body.state} on file. "
            "Please look it up and enter it manually."
        ),
        "help_links": [
            {"label": "Search your city police website", "url": f"https://www.google.com/search?q={body.city}+{body.state}+police+non+emergency+number"},
            {"label": "USA.gov local police directory", "url": "https://www.usa.gov/local-governments"},
        ],
    }


@router.post("/save-address")
def save_address(body: VerifyNumberIn, user=Depends(get_current_user), db=Depends(get_session)):
    """
    Save the user's address and non-emergency number.
    Called after the user confirms the looked-up or manually entered number.
    """
    if not body.non_emergency_number:
        raise HTTPException(status_code=400, detail="Non-emergency number is required")
    if not body.non_emergency_number.startswith("+"):
        raise HTTPException(status_code=400, detail="Phone number must include country code (e.g. +1...)")

    save_user_address(
        db,
        str(user["id"]),
        body.address,
        body.city,
        body.state,
        body.zip_code,
        body.non_emergency_number,
        body.verified,
    )
    return {"ok": True, "message": "Address and non-emergency number saved."}


@router.get("/my-non-emergency")
def my_non_emergency(user=Depends(get_current_user), db=Depends(get_session)):
    """Get the current user's saved non-emergency number and address."""
    info = get_user_non_emergency_number(db, str(user["id"]))
    if not info or not info.get("non_emergency_number"):
        return {
            "configured": False,
            "message": "No non-emergency number set. Complete your safety setup to enable welfare checks.",
        }
    return {
        "configured": True,
        "phone": info["non_emergency_number"],
        "verified": info.get("non_emergency_verified", False),
        "city": info.get("city"),
        "state": info.get("state"),
        "address": info.get("address"),
    }


@router.get("/search-numbers")
def search_numbers(q: str, db=Depends(get_session)):
    """Search non-emergency numbers by city or state name. Public endpoint."""
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Query too short")
    results = search_non_emergency_numbers(db, q)
    return {"results": results}
