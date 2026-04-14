import os
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings


def _is_running_in_docker() -> bool:
    return os.path.exists("/.dockerenv")


def _normalize_database_url_for_docker(url: str) -> str:
    return (
        url.replace("@localhost", "@host.docker.internal")
        .replace("@127.0.0.1", "@host.docker.internal")
    )


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:b2k!J^5eoG98@localhost:5432/edtech"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    JWT_SECRET_KEY: str = "change-me-to-a-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRATION_MINUTES: int = 60
    JWT_REFRESH_EXPIRATION_DAYS: int = 7

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _adapt_database_url_for_container(self):
        if _is_running_in_docker():
            self.DATABASE_URL = _normalize_database_url_for_docker(self.DATABASE_URL)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
