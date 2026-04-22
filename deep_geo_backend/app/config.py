from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(Path(__file__).resolve().parents[2] / ".env"),
            str(Path(__file__).resolve().parent.parent / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API
    api_title: str = "Deep GEO API"
    cors_origins: str = "http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:5173,http://localhost:5173"

    # PostgreSQL (async API)
    database_url: str = Field(
        default="postgresql+asyncpg://deepgeo:deepgeo@127.0.0.1:5432/deepgeo",
        description="SQLAlchemy async URL (asyncpg)",
    )
    # Celery / outils sync
    database_url_sync: str = Field(
        default="postgresql+psycopg2://deepgeo:deepgeo@127.0.0.1:5432/deepgeo",
        description="SQLAlchemy sync URL (psycopg2) pour workers Celery",
    )

    redis_url: str = Field(default="redis://127.0.0.1:6379/0", description="Broker + backend Celery")

    # Google Places API (New)
    google_places_api_key: str = Field(default="", description="Clé API Google Cloud (Places API New)")
    google_places_max_per_request: int = 20  # max API
    google_places_max_pages: int = 10  # sécurité pagination

    # Firecrawl (optionnel)
    firecrawl_api_key: str = ""
    firecrawl_base_url: str = "https://api.firecrawl.dev"

    # Groq (lit .env GEO_GROQ_* ou groq_*)
    groq_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GEO_GROQ_API_KEY", "groq_api_key"),
    )
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        validation_alias=AliasChoices("GEO_GROQ_MODEL", "groq_model"),
    )
    groq_max_concurrent: int = 2
    groq_max_input_chars: int = 28_000

    # Crawl
    crawl_timeout_s: float = 35.0
    crawl_max_pages: int = 5
    crawl_user_agent: str = (
        "Mozilla/5.0 (compatible; DeepGeoBot/2.0; +https://example.local) AppleWebKit/537.36"
    )

    # HTTP
    httpx_trust_env: bool = False

    def cors_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


settings = Settings()
