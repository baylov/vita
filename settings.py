"""Application settings and configuration."""

import os
from typing import Optional
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    service_account_json_path: str = os.getenv(
        "SERVICE_ACCOUNT_JSON_PATH", "service_account.json"
    )
    google_sheets_id: Optional[str] = os.getenv("GOOGLE_SHEETS_ID")
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    google_cloud_credentials_path: Optional[str] = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS", "service_account.json"
    )
    transcription_timeout: int = int(os.getenv("TRANSCRIPTION_TIMEOUT", "60"))
    notification_retry_attempts: int = int(os.getenv("NOTIFICATION_RETRY_ATTEMPTS", "3"))
    notification_retry_delay_min: int = int(
        os.getenv("NOTIFICATION_RETRY_DELAY_MIN", "2")
    )
    notification_retry_delay_max: int = int(
        os.getenv("NOTIFICATION_RETRY_DELAY_MAX", "10")
    )
    digest_schedule_hour: int = int(os.getenv("DIGEST_SCHEDULE_HOUR", "8"))
    digest_schedule_minute: int = int(os.getenv("DIGEST_SCHEDULE_MINUTE", "0"))
    admin_ids: list[int] = []
    
    # Platform adapter settings
    telegram_bot_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    whatsapp_account_sid: Optional[str] = os.getenv("WHATSAPP_ACCOUNT_SID")
    whatsapp_auth_token: Optional[str] = os.getenv("WHATSAPP_AUTH_TOKEN")
    whatsapp_from_number: Optional[str] = os.getenv("WHATSAPP_FROM_NUMBER")
    instagram_page_access_token: Optional[str] = os.getenv("INSTAGRAM_PAGE_ACCESS_TOKEN")
    instagram_app_secret: Optional[str] = os.getenv("INSTAGRAM_APP_SECRET")
    instagram_verify_token: Optional[str] = os.getenv("INSTAGRAM_VERIFY_TOKEN")

    def __init__(self, **data):
        super().__init__(**data)
        # Parse ADMIN_IDS from environment
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            try:
                self.admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(",")]
            except ValueError:
                self.admin_ids = []


settings = Settings()
