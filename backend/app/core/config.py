from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/codementor"
    sync_database_url: str = "postgresql+psycopg2://postgres:password@localhost:5432/codementor"

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_project: str = "codementor-ai"

    # App
    app_env: str = "development"
    secret_key: str = "change_this_in_production"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def active_llm(self) -> str:
        if self.gemini_api_key:
            return "gemini"
        if self.openai_api_key:
            return "openai"
        return "none"


@lru_cache
def get_settings() -> Settings:
    return Settings()