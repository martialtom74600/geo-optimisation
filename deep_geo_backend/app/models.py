from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeepGeoJob(Base):
    """Job de zone — pipeline Places → crawl → audit (tâche Celery)."""

    __tablename__ = "deep_geo_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(
        String(32), default="pending"
    )  # pending | processing | completed | failed | cancelled
    city: Mapped[str] = mapped_column(String(200), nullable=False)
    metier_category: Mapped[str] = mapped_column(String(64), default="high_ticket")
    max_total: Mapped[int] = mapped_column(Integer, default=100)
    progress_message: Mapped[str] = mapped_column(Text, default="")
    activity_log_json: Mapped[str] = mapped_column(Text, default="[]")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lead_count: Mapped[int] = mapped_column(Integer, default=0)
    audit_all: Mapped[bool] = mapped_column(Boolean, default=False)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    leads: Mapped[list["DeepGeoLead"]] = relationship(
        "DeepGeoLead", back_populates="job", cascade="all, delete-orphan"
    )

    @property
    def activity_log(self) -> list[dict[str, str]]:
        raw = (self.activity_log_json or "[]").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        out: list[dict[str, str]] = []
        for x in data:
            if not isinstance(x, dict):
                continue
            m = str(x.get("message", "")).strip()
            t = str(x.get("at", "")).strip()
            if m:
                out.append({"at": t, "message": m})
        return out


class DeepGeoLead(Base):
    """Prospect enrichi — données Places + crawl Markdown + audit RAG."""

    __tablename__ = "deep_geo_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("deep_geo_jobs.id", ondelete="CASCADE"), index=True
    )

    # Google Places
    place_id: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    company_name: Mapped[str] = mapped_column(String(500), default="")
    formatted_address: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_ratings_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    types_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list

    # Deep crawl
    markdown_bundle: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # concat pages → Markdown
    crawl_pages_json: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # [{url, path, chars}]
    crawl_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit IA (5 piliers)
    entity_clarity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rag_structure_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eat_signals: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    geo_risk_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    high_ticket_hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_audit_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    skip_audit_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # CRM (compatible futur front)
    crm_status: Mapped[str] = mapped_column(String(32), default="new", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    job: Mapped[DeepGeoJob] = relationship("DeepGeoJob", back_populates="leads")
