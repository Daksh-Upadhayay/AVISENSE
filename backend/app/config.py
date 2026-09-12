import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or backend/.env."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # The backend talks to Supabase with the public anon key plus the caller's
    # own access token, so row-level security applies to every query. It never
    # needs the service-role key.
    supabase_url: str
    supabase_anon_key: str

    # In the environment: ALLOWED_ORIGINS=https://a.app,https://b.app (a JSON list also works)
    allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:5180"]
    model_dir: Path = BACKEND_DIR / "models" / "current"
    data_dir: Path = BACKEND_DIR / "data" / "cmapss"
    max_upload_bytes: int = 25_000_000  # the largest NASA C-MAPSS file is ~10 MB
    max_history_cycles: int = 2000
    log_level: str = "INFO"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("supabase_url")
    @classmethod
    def strip_slash(cls, v: str) -> str:
        return v.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
