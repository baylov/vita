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


settings = Settings()
