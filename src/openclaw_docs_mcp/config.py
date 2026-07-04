from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / "config.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mcp_host: str = Field(default="0.0.0.0", alias="MCP_HOST")
    mcp_port: int = Field(default=8000, alias="MCP_PORT")
    mcp_path: str = Field(default="/mcp", alias="MCP_PATH")
    api_key: str = Field(alias="API_KEY")

    database_url: str = Field(alias="DATABASE_URL")

    docs_base_url: str = Field(default="https://docs.openclaw.ai", alias="DOCS_BASE_URL")
    docs_locales: str = Field(default="en", alias="DOCS_LOCALES")
    ingest_concurrency: int = Field(default=5, alias="INGEST_CONCURRENCY")
    ingest_rate_limit_ms: int = Field(default=200, alias="INGEST_RATE_LIMIT_MS")

    chunk_size: int = Field(default=512, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=64, alias="CHUNK_OVERLAP")
    chunk_min_size: int = Field(default=100, alias="CHUNK_MIN_SIZE")

    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")

    search_default_limit: int = Field(default=8, alias="SEARCH_DEFAULT_LIMIT")
    search_min_score: float = Field(default=0.0, alias="SEARCH_MIN_SCORE")
    hybrid_search: bool = Field(default=True, alias="HYBRID_SEARCH")

    sync_enabled: bool = Field(default=True, alias="SYNC_ENABLED")
    sync_schedule: str = Field(default="daily", alias="SYNC_SCHEDULE")

    @property
    def locale_prefixes(self) -> set[str]:
        locales = {loc.strip() for loc in self.docs_locales.split(",") if loc.strip()}
        return {loc for loc in locales if loc != "en"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
