from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobActivityLine(BaseModel):
    at: str
    message: str


class ZoneJobCreateV2(BaseModel):
    city: str = Field(..., min_length=1, max_length=200)
    metier_category: str = Field(default="restauration", min_length=1, max_length=64)
    max_total: int = Field(100, ge=1, le=2000)
    audit_all: bool = False


class DeepGeoJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    city: str
    metier_category: str
    progress_message: str
    activity_log: list[JobActivityLine] = Field(default_factory=list)
    error: str | None
    lead_count: int
    max_total: int
    audit_all: bool
    celery_task_id: str | None
    cancel_requested: bool
    created_at: datetime
    completed_at: datetime | None


class DeepGeoLeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    place_id: str | None
    company_name: str
    formatted_address: str
    website: str | None
    rating: float | None
    user_ratings_total: int | None
    types_json: str | None
    markdown_bundle: str | None
    crawl_pages_json: str | None
    crawl_error: str | None
    entity_clarity_score: int | None
    rag_structure_score: int | None
    eat_signals: bool | None
    geo_risk_analysis: str | None
    high_ticket_hook: str | None
    raw_audit_json: str | None
    skip_audit_reason: str | None
    crm_status: str
    created_at: datetime
    updated_at: datetime


class RAGAuditResult(BaseModel):
    entity_clarity_score: int = Field(ge=0, le=100)
    rag_structure_score: int = Field(ge=0, le=100)
    eat_signals: bool
    geo_risk_analysis: str
    high_ticket_hook: str

    @field_validator("entity_clarity_score", "rag_structure_score", mode="before")
    @classmethod
    def _clamp_score(cls, v: Any) -> int:
        if v is None:
            return 0
        n = int(v) if not isinstance(v, bool) else 0
        return max(0, min(100, n))

    @field_validator("eat_signals", mode="before")
    @classmethod
    def _boolish(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "oui", "yes")
        return bool(v)
