import json
import logging
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)

_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        if not settings.firebase_cred_path:
            return None
        cred_path = Path(__file__).resolve().parent.parent / settings.firebase_cred_path
        if not cred_path.exists():
            logger.warning(f"Firebase cred file not found: {cred_path}")
            return None
        import firebase_admin
        from firebase_admin import credentials
        cred = credentials.Certificate(str(cred_path))
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def _send_firebase(device_token: str, title: str, body: str, url: str = None) -> bool:
    app = _get_firebase_app()
    if app is None:
        logger.info(f"[PUSH STUB/firebase] {title}: {body} → {device_token[:12]}...")
        return True
    try:
        from firebase_admin import messaging
        webpush_config = None
        if url:
            webpush_config = messaging.WebpushConfig(
                fcm_options=messaging.WebpushFCMOptions(link=url)
            )
        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=device_token,
            webpush=webpush_config,
        )
        messaging.send(msg)
        logger.info(f"[firebase] Push sent to {device_token[:12]}...")
        return True
    except Exception as e:
        logger.error(f"[firebase] Push failed: {e}")
        return False


def _send_webpush(subscription_json: str, title: str, body: str, url: str = None) -> bool:
    if not settings.webpush_vapid_private_key or not settings.webpush_vapid_public_key:
        logger.info(f"[PUSH STUB/webpush] {title}: {body}")
        return True
    try:
        from pywebpush import webpush, WebPushException
        subscription = json.loads(subscription_json)
        payload = json.dumps({"title": title, "body": body, "url": url or settings.base_url})
        webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=settings.webpush_vapid_private_key,
            vapid_claims={
                "sub": f"mailto:{settings.webpush_vapid_email or 'hello@stillherehq.com'}",
            },
        )
        logger.info(f"[webpush] Push sent to {subscription.get('endpoint', '')[:40]}...")
        return True
    except Exception as e:
        logger.error(f"[webpush] Push failed: {e}")
        return False


def send_push(device_token: str, title: str, body: str, url: str = None) -> bool:
    if not device_token:
        return False
    provider = settings.push_provider.lower()
    if provider == "webpush":
        if device_token.startswith("{"):
            return _send_webpush(device_token, title, body, url)
        logger.warning("push_provider=webpush but device_token looks like FCM token — skipping")
        return False
    return _send_firebase(device_token, title, body, url)
