from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./safety.db"
    ANTHROPIC_API_KEY: str = ""
    ENVIRONMENT: str = "development"
    PLANT_CONFIG_PATH: str = "plant.config.yaml"
    ALERT_WEBHOOK_URL: str = ""

    # "auto" (Claude if ANTHROPIC_API_KEY is set, else the local Ollama model),
    # "claude" (force Claude, error out to the static fallback if no key), or
    # "ollama" (force the local model regardless of whether a Claude key exists) —
    # switch anytime without touching code.
    LLM_PROVIDER: str = "ollama"
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
