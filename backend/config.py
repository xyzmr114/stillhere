import os
from pathlib import Path

from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    database_url: str = ""
    jwt_secret: str = "dev-secret"
    redis_url: str = "redis://localhost:6379"
    celery_broker: str = "redis://localhost:6379/0"
    base_url: str = "https://stillherehq.com"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    sns_sender_id: str = "StillHere"
    firebase_cred_path: str = ""
    firebase_api_key: str = ""
    firebase_auth_domain: str = ""
    firebase_project_id: str = ""
    firebase_storage_bucket: str = ""
    firebase_messaging_sender_id: str = ""
    firebase_app_id: str = ""
    firebase_measurement_id: str = ""
    firebase_vapid_key: str = ""
    auth0_domain: str = ""
    auth0_client_id: str = ""
    resend_api_key: str = ""
    email_from: str = "Still Here <onboarding@resend.dev>"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_verify_sid: str = ""
    demo_sms_to: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    model_config = {"env_file": str(_ENV_FILE), "extra": "ignore"}


settings = Settings()
