from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_CORS_ORIGINS = [
    *(f"http://127.0.0.1:{port}" for port in range(5173, 5200)),
    *(f"http://localhost:{port}" for port in range(5173, 5200)),
]


class Settings(BaseSettings):
    """Runtime settings loaded from .env and process environment."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Word Format Agent"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(default=DEFAULT_CORS_ORIGINS, alias="CORS_ORIGINS")
    file_storage_root: Path = Field(default=Path("../storage"), alias="FILE_STORAGE_ROOT")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str | None = Field(default=None, alias="LLM_MODEL")
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")
    llm_timeout_seconds: int = Field(default=120, ge=1, le=600, alias="LLM_TIMEOUT_SECONDS")
    llm_health_timeout_seconds: int = Field(default=15, ge=1, le=120, alias="LLM_HEALTH_TIMEOUT_SECONDS")
    soffice_bin: str | None = Field(default=None, alias="SOFFICE_BIN")

    @field_validator("cors_origins")
    @classmethod
    def include_local_vite_fallback_origins(cls, value: list[str]) -> list[str]:
        origins = list(value)
        for origin in DEFAULT_CORS_ORIGINS:
            if origin not in origins:
                origins.append(origin)
        return origins

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_model)

    @property
    def soffice_configured(self) -> bool:
        return bool(self.soffice_bin)


@lru_cache
def get_settings() -> Settings:
    return Settings()
