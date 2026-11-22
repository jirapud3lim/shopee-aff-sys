from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = f"sqlite:///{Path(__file__).resolve().parents[1] / 'local.db'}"

    @field_validator("database_url")
    @classmethod
    def use_psycopg(cls, value: str) -> str:
        return (
            value.replace("postgresql://", "postgresql+psycopg://", 1)
            if value.startswith("postgresql://")
            else value
        )

    session_ttl_days: int = 30
    password_min_length: int = 12
    meta_test_page_id: str = ""
    meta_graph_api_version: str = "v27.0"
    meta_page_access_token: SecretStr = SecretStr("")
    meta_app_secret: SecretStr = SecretStr("")
    meta_ca_file: str = ""
    meta_studio_workspace_id: str = ""
    meta_studio_page_name: str = ""
    meta_studio_example_reel_id: str = ""
    meta_studio_publish_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
