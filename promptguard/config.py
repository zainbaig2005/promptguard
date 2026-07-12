from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PROMPTGUARD_", extra="ignore")
    database_url: str = "sqlite:///promptguard.db"
    log_level: str = "INFO"
    evidence_dir: Path = Path("./evidence")
    default_timeout: int = 30
    max_concurrency: int = Field(default=3, ge=1, le=20)
    store_raw_external_responses: bool = False
    report_dir: Path = Path("./reports")


@lru_cache
def get_settings() -> Settings:
    return Settings()
