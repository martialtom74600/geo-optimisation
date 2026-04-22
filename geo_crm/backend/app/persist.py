"""Persistance des LeadRecord Pydantic → modèle ORM."""
from __future__ import annotations

import orjson
from geo_stealth_prospector.models import LeadRecord

from app.models import Lead


def _proof_status(lead: LeadRecord) -> str:
    if (lead.skip_ia_reason or "") == "schema_ok" or (
        lead.crawl and lead.crawl.has_relevant_business_schema
    ):
        return "optimized"
    c = lead.crawl
    if c and c.page_fetched and not c.has_relevant_business_schema:
        return "priority"
    return "unknown"


def lead_row_from_record(lead: LeadRecord, job_id: int | None) -> Lead:
    c = lead.crawl
    audit = lead.audit
    actions_j = "[]"
    if audit and audit.actions_prioritaires:
        actions_j = orjson.dumps(audit.actions_prioritaires).decode()
    return Lead(
        sourcing_job_id=job_id,
        company_name=lead.company_name,
        url=lead.url,
        metier=lead.metier,
        city=lead.city,
        title_serp=lead.title,
        crm_status="new",
        proof_status=_proof_status(lead),
        skip_ia_reason=lead.skip_ia_reason,
        error=lead.error,
        risque_marche=audit.risque_marche if audit else None,
        faille_technique=audit.faille_technique if audit else None,
        hook_email=audit.hook_email if audit else None,
        json_ld_suggestion=audit.json_ld_suggestion if audit else None,
        synthese_expert_geo=audit.synthese_expert_geo if audit else None,
        score_opportunite_geo=audit.score_opportunite_geo if audit else None,
        geo_dim_structured=audit.analyse_donnees_structurees if audit else None,
        geo_dim_llm=audit.analyse_exploitabilite_ia if audit else None,
        geo_dim_local=audit.analyse_signal_local if audit else None,
        actions_prioritaires_json=actions_j,
        user_notes=None,
        next_action=None,
        contacted_at=None,
        crawl_business_ok=bool(c and c.has_relevant_business_schema),
        payload_json=orjson.dumps(lead.model_dump(), option=orjson.OPT_INDENT_2).decode(),
    )
