"""Application settings, loaded from environment / .env file."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database: PostgreSQL in production, SQLite for local demo
    database_url: str = "sqlite:////data/nailcrm.db"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_expire_days: int = 30
    owner_login: str = "admin"
    owner_password: str = "admin123"

    # Salon timezone (all times in the app are wall-clock times of the salon)
    tz: str = "Europe/Moscow"

    # Telegram bot (optional). If empty, reminders are disabled.
    telegram_bot_token: str = ""
    telegram_owner_chat_id: str = ""

    # Seed demo data (clients/appointments) on first start. NEVER enable in production.
    demo_seed: bool = False

    static_dir: str = str(BASE_DIR / "static")


settings = Settings()

# Make sure SQLite directory exists
if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.split("///")[-1]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
