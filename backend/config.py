from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./safety.db"
    ANTHROPIC_API_KEY: str = ""
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
