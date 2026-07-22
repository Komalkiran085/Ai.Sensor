from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./safety.db"
    ANTHROPIC_API_KEY: str = ""
    ENVIRONMENT: str = "development"
    PLANT_CONFIG_PATH: str = "plant.config.yaml"
    ALERT_WEBHOOK_URL: str = ""

    # Real phone call (Twilio Programmable Voice) for extreme-severity alerts only —
    # a webhook can sit unread, a phone ringing can't. All four required for a call to
    # actually go out; missing any one just logs and skips (same degrade-gracefully
    # pattern as ALERT_WEBHOOK_URL).
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    ALERT_PHONE_NUMBER: str = ""

    # Real-time mobile text alert via Telegram Bot API — free, no trial credit to run
    # out, no verified-number restriction (unlike Twilio SMS). Delivers to a Telegram
    # chat rather than the phone's actual SMS inbox. Both required or this is skipped.
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
