"""Application settings and configuration."""

import os
from typing import Optional
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra='allow')

    # Database
    database_url: str = "sqlite:///./vitaplus.db"
    
    service_account_json_path: str = "service_account.json"
    google_sheets_id: Optional[str] = None
    gemini_api_key: Optional[str] = None
    google_cloud_credentials_path: Optional[str] = "service_account.json"
    transcription_timeout: int = 60
    notification_retry_attempts: int = 3
    notification_retry_delay_min: int = 2
    notification_retry_delay_max: int = 10
    digest_schedule_hour: int = 8
    digest_schedule_minute: int = 0
    
    # Platform adapter settings
    telegram_bot_token: Optional[str] = None
    whatsapp_account_sid: Optional[str] = None
    whatsapp_auth_token: Optional[str] = None
    whatsapp_from_number: Optional[str] = None
    instagram_page_access_token: Optional[str] = None
    instagram_app_secret: Optional[str] = None
    instagram_verify_token: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize admin_ids attribute (not a pydantic field to avoid parsing issues)
        self.admin_ids: list[int] = []
        # Parse ADMIN_IDS from environment (handles both env and .env)
        admin_ids_str = os.getenv("ADMIN_IDS", "").strip()
        if admin_ids_str:
            try:
                self.admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(",") if id_str.strip()]
            except ValueError:
                self.admin_ids = []


settings = Settings()
