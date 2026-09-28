from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application configuration, sourced from environment
    variables / .env. No other module should read os.environ directly.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "changeme"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_allowed_origins: str = "http://localhost:5173"

    database_url: str = "postgresql+psycopg2://postgres:changeme@localhost:5432/clinical_reviewer"

    upload_max_size_mb: int = 25
    upload_storage_dir: str = "./backend/storage"

    ai_provider: str = "placeholder"
    ai_model_name: str = "placeholder"
    ai_api_key: str = "changeme"
    ai_api_base_url: str = ""

    # OCR is a separate, local/offline concern from the AI_PROVIDER above —
    # see docs/decisions/007-ocr.md. "tesseract" is the only value
    # implemented today; the setting exists so swapping engines later is a
    # config change, not a code change.
    ocr_engine: str = "tesseract"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def upload_max_size_bytes(self) -> int:
        return self.upload_max_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
