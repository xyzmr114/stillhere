import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

from routes import users, checkin, contacts, confirm, demo, mutual, groups, portal, family, webhooks, api_keys, stripe_payments, contact

app = FastAPI(title="Still Here", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def track_device_ping(request, call_next):
    response = await call_next(request)
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            from jose import jwt
            from config import settings
            payload = jwt.decode(auth[7:], settings.jwt_secret, algorithms=["HS256"])
            uid = payload.get("sub")
            if uid:
                from db import SessionLocal
                from sqlalchemy import text
                db = SessionLocal()
                try:
                    db.execute(text("UPDATE users SET last_device_ping = NOW() WHERE id = :uid"), {"uid": uid})
                    db.commit()
                finally:
                    db.close()
        except Exception:
            pass
    return response

app.include_router(users.router)
app.include_router(checkin.router)
app.include_router(contacts.router)
app.include_router(confirm.router)
app.include_router(demo.router)
app.include_router(mutual.router)
app.include_router(groups.router)
app.include_router(portal.router)
app.include_router(family.router)
app.include_router(webhooks.router)
app.include_router(api_keys.router)
app.include_router(stripe_payments.router)
app.include_router(contact.router)

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/demo")
def serve_demo():
    return FileResponse(FRONTEND / "demo.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def serve_landing():
    return FileResponse(FRONTEND / "landing.html")


@app.get("/app")
def serve_app():
    return FileResponse(FRONTEND / "index.html")


@app.get("/reset-password")
def serve_reset_password():
    return FileResponse(FRONTEND / "reset-password.html")


@app.get("/privacy")
def serve_privacy():
    return FileResponse(FRONTEND / "privacy.html")


@app.get("/terms")
def serve_terms():
    return FileResponse(FRONTEND / "terms.html")


@app.get("/buy")
def buy_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/stripe/buy")


@app.get("/consent")
def serve_consent():
    return FileResponse(FRONTEND / "consent.html")


@app.get("/contact")
def serve_contact():
    return FileResponse(FRONTEND / "contact.html")


@app.get("/sitemap")
def serve_sitemap():
    return FileResponse(FRONTEND / "sitemap.html")


@app.get("/sitemap.xml")
def serve_sitemap_xml():
    return Response(content=(FRONTEND / "sitemap.xml").read_text(), media_type="application/xml")


@app.get("/sw-config.js")
def serve_sw_config():
    from config import settings
    js = f"""self.__FIREBASE_CONFIG = {{
  apiKey: {repr(settings.firebase_api_key)},
  authDomain: {repr(settings.firebase_auth_domain)},
  projectId: {repr(settings.firebase_project_id)},
  storageBucket: {repr(settings.firebase_storage_bucket)},
  messagingSenderId: {repr(settings.firebase_messaging_sender_id)},
  appId: {repr(settings.firebase_app_id)},
  measurementId: {repr(settings.firebase_measurement_id)},
}};
self.__VAPID_KEY = {repr(settings.firebase_vapid_key)};
"""
    return Response(content=js, media_type="application/javascript")


@app.get("/api/config")
def serve_client_config():
    from config import settings
    return {
        "firebase": {
            "apiKey": settings.firebase_api_key,
            "authDomain": settings.firebase_auth_domain,
            "projectId": settings.firebase_project_id,
            "storageBucket": settings.firebase_storage_bucket,
            "messagingSenderId": settings.firebase_messaging_sender_id,
            "appId": settings.firebase_app_id,
            "measurementId": settings.firebase_measurement_id,
        },
        "vapidKey": settings.firebase_vapid_key,
        "auth0Domain": settings.auth0_domain,
        "auth0ClientId": settings.auth0_client_id,
    }


app.mount("/", StaticFiles(directory=str(FRONTEND)), name="static")
