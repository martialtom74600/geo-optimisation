from __future__ import annotations

from datetime import datetime

from geo_stealth_prospector.profession_categories import is_valid_category_id

from pydantic import BaseModel, Field, HttpUrl, field_validator


class LeadOut(BaseModel):
    id: int
    company_name: str
    url: str
    metier: str
    city: str
    title_serp: str = ""
    crm_status: str
    proof_status: str
    skip_ia_reason: str | None = None
    error: str | None = None
    risque_marche: str | None = None
    faille_technique: str | None = None
    hook_email: str | None = None
    json_ld_suggestion: str | None = None
    synthese_expert_geo: str | None = None
    score_opportunite_geo: int | None = None
    geo_dim_structured: str | None = None
    geo_dim_llm: str | None = None
    geo_dim_local: str | None = None
    actions_prioritaires_json: str | None = None
    user_notes: str | None = None
    next_action: str | None = None
    contacted_at: datetime | None = None
    crawl_business_ok: bool = False
    sourcing_job_id: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadUpdate(BaseModel):
    crm_status: str | None = Field(
        default=None, description="new | to_contact | won | lost"
    )
    error: str | None = None
    user_notes: str | None = None
    next_action: str | None = None
    contacted_at: datetime | None = None


class MetierCategoryOut(BaseModel):
    id: str
    label: str


class ZoneJobCreate(BaseModel):
    city: str = Field(..., min_length=1, max_length=200)
    max_total: int = Field(40, ge=1, le=2000)
    max_per_metier: int = Field(8, ge=1, le=30)
    metier_category: str = Field(
        "high_ticket",
        min_length=1,
        max_length=64,
        description="Id catégorie (restauration, sante_medical, high_ticket, …).",
    )
    audit_all: bool = False

    @field_validator("metier_category")
    @classmethod
    def _valid_cat(cls, v: str) -> str:
        s = (v or "").strip() or "high_ticket"
        if not is_valid_category_id(s):
            raise ValueError("Catégorie inconnue — utilisez GET /api/jobs/metier-categories")
        return s


class JobActivityLine(BaseModel):
    """Une entrée du journal humain (horodatage ISO + texte)."""

    at: str
    message: str


class SourcingJobOut(BaseModel):
    id: int
    city: str
    status: str
    progress_message: str
    activity_log: list[JobActivityLine] = Field(default_factory=list)
    error: str | None
    lead_count: int
    max_total: int
    max_per_metier: int
    metier_category: str = "high_ticket"
    audit_all: bool = False
    cancel_requested: bool = False
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True
