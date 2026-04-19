"""
Still Here — Non-Emergency Number API
Public, read-only API for non-emergency police numbers.
Self-hosted instances sync from this on first boot.
Host at db.stillherehq.com
"""
import json
import hashlib
import logging
from pathlib import Path
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)
app = FastAPI(title="Still Here Non-Emergency Numbers", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Public API
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Load numbers from bundled JSON
_numbers = []
_etag = ""

def _load_numbers():
    global _numbers, _etag
    data_path = Path(__file__).parent / "data" / "numbers.json"
    if data_path.exists():
        _numbers = json.loads(data_path.read_text())
        _etag = hashlib.md5(json.dumps(_numbers, sort_keys=True).encode()).hexdigest()

_load_numbers()

@app.get("/v1/numbers")
def get_numbers(city: str = None, state: str = None, response: Response = None):
    """Get non-emergency numbers. Supports ETag caching."""
    response.headers["ETag"] = _etag
    response.headers["Cache-Control"] = "public, max-age=86400"

    results = _numbers
    if state:
        results = [n for n in results if n["state"].lower() == state.lower()]
    if city:
        results = [n for n in results if n["city"].lower() == city.lower()]

    return {"numbers": results, "total": len(results), "etag": _etag}

@app.get("/v1/health")
def health():
    return {"status": "ok", "count": len(_numbers)}
