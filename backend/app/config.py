from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    gemini_api_key: SecretStr | None = None

    investigator_model: str = "gemini-3.6-flash"
    classifier_model: str = "gemini-3.1-flash-lite"
    embedding_model: str = "gemini-embedding-2"
    # Requested output size. pgvector can only index `vector` columns up to 2000 dims.
    embedding_dim: int = 768

    # Per-incident caps for the triage loop.
    max_fix_proposals: int = 2
    max_resubmits: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
