import json
import logging
import urllib.request

from jose import jwt

from config import settings

logger = logging.getLogger(__name__)

_jwks_cache = None


def _get_jwks(force_refresh: bool = False):
    global _jwks_cache
    if _jwks_cache is None or force_refresh:
        url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
        with urllib.request.urlopen(url, timeout=5) as resp:
            _jwks_cache = json.loads(resp.read())
    return _jwks_cache


def verify_auth0_token(token: str) -> dict | None:
    if not settings.auth0_domain:
        logger.warning("AUTH0_DOMAIN not configured — skipping token verification")
        return None
    if not settings.auth0_client_id:
        logger.warning("AUTH0_CLIENT_ID not configured — skipping token verification")
        return None
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        jwks = _get_jwks()
        rsa_key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
        if not rsa_key:
            # kid not in cache — Auth0 may have rotated keys, retry once
            jwks = _get_jwks(force_refresh=True)
            rsa_key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
        if not rsa_key:
            logger.error("Auth0 JWT kid %s not found in JWKS", kid)
            return None
        issuer = f"https://{settings.auth0_domain}/"
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.auth0_client_id,
            issuer=issuer,
        )
        return payload
    except Exception as e:
        logger.error("Auth0 token verification failed: %s", e)
        return None
