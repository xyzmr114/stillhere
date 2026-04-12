import logging
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)

_firebase_app = None


def _get_app():
    global _firebase_app
    if _firebase_app is None:
        if not settings.firebase_cred_path:
            logger.warning("Firebase credentials not configured — push will be logged only")
            return None
        cred_path = Path(__file__).resolve().parent.parent / settings.firebase_cred_path
        if not cred_path.exists():
            logger.warning(f"Firebase cred file not found: {cred_path} — push will be logged only")
            return None
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(str(cred_path))
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def send_push(device_token: str, title: str, body: str, url: str = None) -> bool:
    app = _get_app()
    if not device_token:
        return False
    if app is None:
        logger.info(f"[PUSH STUB] To: {device_token[:8]}... | {title}: {body}")
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
        logger.info(f"Push sent to {device_token[:8]}...")
        return True
    except Exception as e:
        logger.error(f"Push failed: {e}")
        return False
