from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from .env and process environment."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Word Format Agent"
    api_prefix: str = "/api"
    file_storage_root: Path = Field(default=Path("../storage"), alias="FILE_STORAGE_ROOT")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str | None = Field(default=None, alias="LLM_MODEL")
    soffice_bin: str | None = Field(default=None, alias="SOFFICE_BIN")

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_model)

    @property
    def soffice_configured(self) -> bool:
        return bool(self.soffice_bin)


@lru_cache
def get_settings() -> Settings:
    return Settings()
