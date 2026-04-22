"""Modèles Pydantic pour leads et rapports d'audit."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_serializer, field_validator


class CrawlResult(BaseModel):
    """Preuves factuelles issues du crawl de la page d'accueil (avant l'appel LLM)."""

    page_fetched: bool = False
    final_url: str = ""
    http_status: int | None = None
    error: str | None = None
    title: str = ""
    h1_texts: list[str] = Field(default_factory=list)
    has_jsonld_script: bool = False
    jsonld_types_found: list[str] = Field(default_factory=list)
    has_relevant_business_schema: bool = False


class AuditResult(BaseModel):
    """Rapport IA (factuel) + analyse GEO experte par site + suggestion JSON-LD offerte au client."""

    risque_marche: str = Field(description="Risque de perte de marché (concurrence moteur génératif).")
    faille_technique: str = Field(
        description="Faille technique, alignée sur les preuves du crawl (JSON-LD, sémantique, etc.)."
    )
    hook_email: str = Field(description="Phrase d'accroche prête à coller dans un email.")
    json_ld_suggestion: str = Field(
        default="",
        description="Un seul objet JSON-LD (script type application/ld+json) LocalBusiness prêt à coller, JSON valide.",
    )
    # Analyse experte « par site » (spécificités GEO, pas un texte générique)
    synthese_expert_geo: str = Field(
        default="",
        description="2–4 phrases : synthèse commerciale GEO pour ce domaine, ce site, ce métier.",
    )
    analyse_donnees_structurees: str = Field(
        default="",
        description="Ce site : @type, JSON-LD, schéma.org, ce qui manque ou est correct (preuves crawl).",
    )
    analyse_exploitabilite_ia: str = Field(
        default="",
        description="Comment un assistant IA / moteur génératif utiliserait (ou ignorerait) ce site.",
    )
    analyse_signal_local: str = Field(
        default="",
        description="Signal local / entreprise (LocalBusiness, cohérence sémantique local pro, NAP implicite).",
    )
    score_opportunite_geo: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Score 0–100 d'opportunité commerciale GEO (0 = rien à vendre, 100 = gros écart + fort potentiel).",
    )
    actions_prioritaires: list[str] = Field(
        default_factory=list,
        description="3 à 5 actions concrètes, ordonnées, adaptées à ce site.",
    )


class LeadRecord(BaseModel):
    """Un prospect identifié, crawl de preuve optionnel, audit optionnel."""

    company_name: str
    url: str
    metier: str
    city: str
    title: str = ""
    crawl: CrawlResult | None = None
    audit: AuditResult | None = None
    error: str | None = None
    source_rank: int = 0
    # Si Groq n'est pas appelé (ex. filtre « cash machine » : schéma business déjà présent)
    skip_ia_reason: str | None = None

    @field_validator("url", mode="before")
    @classmethod
    def url_as_str(cls, v: Any) -> str:
        return str(v) if v is not None else ""

    @field_serializer("audit")
    def ser_audit(self, v: AuditResult | None) -> dict[str, object] | None:
        if v is None:
            return None
        return v.model_dump()

    @field_serializer("crawl")
    def ser_crawl(self, v: CrawlResult | None) -> dict[str, object] | None:
        if v is None:
            return None
        return v.model_dump()


class SearchHit(BaseModel):
    """Lien brut issu du moteur avant qualification finale."""

    url: str
    title: str = ""
    rank: int = 0
