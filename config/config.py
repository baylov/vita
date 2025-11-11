import os
from pathlib import Path
from typing import Optional, List

from pydantic import BaseModel, Field
from dotenv import load_dotenv


load_dotenv(".env")


class DatabaseSettings(BaseModel):
    """Database configuration settings."""
    
    url: Optional[str] = Field(default=None)
    echo: bool = Field(default=False)
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=20)
    pool_timeout: int = Field(default=30)
    pool_recycle: int = Field(default=3600)
    
    @property
    def connection_url(self) -> str:
        """Get the database connection URL, fallback to local SQLite if not provided."""
        if self.url:
            return self.url
        db_path = Path.cwd() / "data" / "vitaplus_bot.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"


class ApiKeys(BaseModel):
    """API keys and credentials configuration."""
    
    telegram_bot_token: str
    gemini_api_key: str
    google_application_credentials: Optional[str] = None
    google_sheet_id: Optional[str] = None
    twilio_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    instagram_app_id: Optional[str] = None
    instagram_app_secret: Optional[str] = None


class NotificationSettings(BaseModel):
    """Notification configuration settings."""
    
    healthcheck_interval: int = Field(default=300)
    retry_limit: int = Field(default=3)
    retry_timeout: int = Field(default=60)
    request_timeout: int = Field(default=30)


class AppSettings(BaseModel):
    """Main application settings."""
    
    app_name: str = "VitaPlus Admin Bot"
    log_level: str = "INFO"
    admin_ids: List[int] = Field(default_factory=list)
    
    database: DatabaseSettings
    api_keys: ApiKeys
    notifications: NotificationSettings


def get_settings() -> AppSettings:
    """Load and return application settings from environment."""
    db_url = os.getenv("DB_URL")
    
    database = DatabaseSettings(url=db_url)
    
    api_keys = ApiKeys(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        google_application_credentials=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        google_sheet_id=os.getenv("GOOGLE_SHEET_ID"),
        twilio_sid=os.getenv("TWILIO_SID"),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        instagram_app_id=os.getenv("INSTAGRAM_APP_ID"),
        instagram_app_secret=os.getenv("INSTAGRAM_APP_SECRET"),
    )
    
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    admin_ids = []
    if admin_ids_str:
        try:
            admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(",") if id_str.strip()]
        except ValueError:
            admin_ids = []
    
    notifications = NotificationSettings(
        healthcheck_interval=int(os.getenv("HEALTHCHECK_INTERVAL", "300")),
        retry_limit=3,
        retry_timeout=60,
        request_timeout=30,
    )
    
    return AppSettings(
        app_name="VitaPlus Admin Bot",
        log_level=log_level,
        admin_ids=admin_ids,
        database=database,
        api_keys=api_keys,
        notifications=notifications,
    )
