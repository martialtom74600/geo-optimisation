from __future__ import annotations

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncConnection

from app.config import settings
from app.database import Base, async_engine
from app.models import DeepGeoJob, DeepGeoLead  # noqa: F401 — tables enregistrées
from app.routers import v2


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await async_engine.dispose()


app = FastAPI(title=settings.api_title, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list() or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v2.router)

_STATIC = Path(__file__).resolve().parent / "static" / "essai.html"


@app.get("/essai", response_class=HTMLResponse, include_in_schema=False)
async def essai_v2() -> str:
    """Interface web simple (formulaire + suivi de job) — même processus que l’API."""
    if not _STATIC.is_file():
        return "<!DOCTYPE html><html><body><p>Fichier essai.html manquant.</p></body></html>"
    return _STATIC.read_text(encoding="utf-8")


@app.get("/")
async def root():
    return {
        "service": "deep-geo-backend",
        "docs": "/docs",
        "v2": "/api/v2/health",
        "essai_ui": "/essai",
    }
