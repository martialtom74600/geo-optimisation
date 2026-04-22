from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

# Charger .env à la racine du monorepo (GEO) pour GEO_GROQ_API_KEY, etc.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(REPO_ROOT / ".env", override=False)
load_dotenv(REPO_ROOT / "geo_crm" / "backend" / ".env", override=False)

from app.config import ApiSettings
from app.database import Base, engine, get_db


def _ensure_sqlite_schema() -> None:
    if not str(engine.url).startswith("sqlite"):
        return
    insp = inspect(engine)
    if "sourcing_jobs" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("sourcing_jobs")}
    if "audit_all" not in cols:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE sourcing_jobs "
                    "ADD COLUMN audit_all BOOLEAN NOT NULL DEFAULT 0"
                )
            )
    cols2 = {c["name"] for c in insp.get_columns("sourcing_jobs")}
    if "cancel_requested" not in cols2:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE sourcing_jobs "
                    "ADD COLUMN cancel_requested BOOLEAN NOT NULL DEFAULT 0"
                )
            )
    cols3 = {c["name"] for c in insp.get_columns("sourcing_jobs")}
    if "activity_log_json" not in cols3:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE sourcing_jobs "
                    "ADD COLUMN activity_log_json TEXT NOT NULL DEFAULT '[]'"
                )
            )
    cols4 = {c["name"] for c in insp.get_columns("sourcing_jobs")}
    if "metier_category" not in cols4:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE sourcing_jobs "
                    "ADD COLUMN metier_category VARCHAR(64) NOT NULL DEFAULT 'high_ticket'"
                )
            )


def _ensure_leads_schema() -> None:
    if not str(engine.url).startswith("sqlite"):
        return
    insp = inspect(engine)
    if "leads" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("leads")}
    alters: list[tuple[str, str]] = [
        ("synthese_expert_geo", "TEXT"),
        ("score_opportunite_geo", "INTEGER"),
        ("geo_dim_structured", "TEXT"),
        ("geo_dim_llm", "TEXT"),
        ("geo_dim_local", "TEXT"),
        ("actions_prioritaires_json", "TEXT"),
        ("user_notes", "TEXT"),
        ("next_action", "TEXT"),
        ("contacted_at", "DATETIME"),
    ]
    for name, typ in alters:
        if name in existing:
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE leads ADD COLUMN {name} {typ}"))


from app.models import Lead
from app.routers import jobs, leads

LOG = logging.getLogger(__name__)
_settings = ApiSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_schema()
    _ensure_leads_schema()
    LOG.info("GEO-CRM API — tables OK — CORS %s", _settings.origins_list())
    yield


app = FastAPI(
    title="GEO-CRM",
    description="Sourcing, preuves, audits GEO — outil de prospection artisan",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.origins_list()
    or [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(jobs.router)
app.include_router(leads.router)


@app.get("/")
def root():
    return {
        "service": "geo-crm-api",
        "message": (
            "En développement, l’app web est sur http://127.0.0.1:8000 (un seul onglet). "
            "Cette instance écoute en 8001 en coulisses."
        ),
        "ui": "http://127.0.0.1:8000",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api")
def api_index():
    return {
        "endpoints": {
            "health": "/api/health",
            "stats": "/api/stats",
            "jobs": "/api/jobs",
            "leads": "/api/leads",
        },
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"ok": True, "service": "geo-crm-api"}


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Lead.id))) or 0
    by_crm: dict[str, int] = {}
    for row in db.execute(
        select(Lead.crm_status, func.count(Lead.id)).group_by(Lead.crm_status)
    ).all():
        by_crm[str(row[0])] = int(row[1])
    by_proof: dict[str, int] = {}
    for row in db.execute(
        select(Lead.proof_status, func.count(Lead.id)).group_by(Lead.proof_status)
    ).all():
        by_proof[str(row[0])] = int(row[1])
    return {"total_leads": total, "by_crm_status": by_crm, "by_proof_status": by_proof}
