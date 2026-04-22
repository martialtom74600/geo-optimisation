from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SourcingJob(Base):
    __tablename__ = "sourcing_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="queued"
    )  # queued, running, completed, failed
    progress_message: Mapped[str] = mapped_column(Text, default="")
    activity_log_json: Mapped[str] = mapped_column(Text, default="[]")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_count: Mapped[int] = mapped_column(Integer, default=0)
    max_total: Mapped[int] = mapped_column(Integer, default=40)
    max_per_metier: Mapped[int] = mapped_column(Integer, default=8)
    # Id de catégorie (geo_stealth_prospector.profession_categories), ex. restauration, high_ticket
    metier_category: Mapped[str] = mapped_column(String(64), default="high_ticket")
    audit_all: Mapped[bool] = mapped_column(Boolean, default=False)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    leads: Mapped[list["Lead"]] = relationship("Lead", back_populates="job")

    @property
    def activity_log(self) -> list[dict[str, str]]:
        """Lecture seule : lignes {at, message} pour l'API (pas une colonne SQL)."""
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


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sourcing_job_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sourcing_jobs.id"), nullable=True
    )

    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    metier: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(200), default="", index=True)
    title_serp: Mapped[str] = mapped_column(String(1000), default="")

    # CRM: new | to_contact | won | lost
    crm_status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    # proof: optimized | priority | unknown
    proof_status: Mapped[str] = mapped_column(String(32), default="unknown", index=True)

    skip_ia_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    risque_marche: Mapped[str | None] = mapped_column(Text, nullable=True)
    faille_technique: Mapped[str | None] = mapped_column(Text, nullable=True)
    hook_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    json_ld_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)

    synthese_expert_geo: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_opportunite_geo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    geo_dim_structured: Mapped[str | None] = mapped_column(Text, nullable=True)
    geo_dim_llm: Mapped[str | None] = mapped_column(Text, nullable=True)
    geo_dim_local: Mapped[str | None] = mapped_column(Text, nullable=True)
    actions_prioritaires_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    crawl_business_ok: Mapped[bool] = mapped_column(default=False)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    job: Mapped[SourcingJob | None] = relationship("SourcingJob", back_populates="leads")
