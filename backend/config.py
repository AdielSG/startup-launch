from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env regardless of working directory.
# Checks backend/.env first, then falls back to project-root .env.
_BACKEND_DIR = Path(__file__).parent
_ROOT_DIR    = _BACKEND_DIR.parent

_ENV_FILE = (
    str(_BACKEND_DIR / ".env") if (_BACKEND_DIR / ".env").exists()
    else str(_ROOT_DIR / ".env")
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key:    str = ""
    apify_api_token:   str = ""
    database_url:      str = "sqlite:///./launches.db"  # overridden by DATABASE_URL env var in production


settings = Settings()
