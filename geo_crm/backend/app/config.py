from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GEO_CRM_",
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),  # geo_crm/.env or repo root
        extra="ignore",
    )

    database_url: str = ""  # vide = SQLite dans backend/data/geo_crm.db
    cors_origins: str = (
        "http://127.0.0.1:8000,http://localhost:8000,"
        "http://127.0.0.1:5173,http://localhost:5173"
    )

    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
