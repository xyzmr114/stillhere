import logging
from config import settings

logger = logging.getLogger(__name__)


def call_non_emergency(user_name: str, user_phone: str, last_known_location: str = None) -> bool:
    logger.info(f"[NON-EMERGENCY CALL STUB] Welfare check requested for {user_name} ({user_phone}). Location: {last_known_location}")
    return True
