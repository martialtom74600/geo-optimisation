"""Export CSV / JSON des leads et audits."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import orjson

from geo_stealth_prospector.models import LeadRecord


def leads_to_dicts(records: list[LeadRecord]) -> list[dict[str, Any]]:
    """Sérialisation plate pour export."""
    out: list[dict[str, Any]] = []
    for r in records:
        c = r.crawl
        row: dict[str, Any] = {
            "company_name": r.company_name,
            "url": r.url,
            "metier": r.metier,
            "city": r.city,
            "title_serp": r.title,
            "crawl_page_ok": c.page_fetched if c else False,
            "crawl_final_url": c.final_url if c else "",
            "crawl_http": c.http_status if c else "",
            "crawl_error": c.error if c else "",
            "crawl_title": c.title if c else "",
            "crawl_h1": " | ".join(c.h1_texts) if c and c.h1_texts else "",
            "crawl_has_jsonld_script": c.has_jsonld_script if c else False,
            "crawl_jsonld_types": ", ".join(c.jsonld_types_found) if c and c.jsonld_types_found else "",
            "crawl_business_schema_ok": c.has_relevant_business_schema if c else False,
            "source_rank": r.source_rank,
            "skip_ia_reason": r.skip_ia_reason or "",
            "error": r.error,
        }
        if r.audit:
            row["risque_marche"] = r.audit.risque_marche
            row["faille_technique"] = r.audit.faille_technique
            row["hook_email"] = r.audit.hook_email
            row["json_ld_suggestion"] = r.audit.json_ld_suggestion
        else:
            row["risque_marche"] = ""
            row["faille_technique"] = ""
            row["hook_email"] = ""
            row["json_ld_suggestion"] = ""
        out.append(row)
    return out


def export_json(path: Path, records: list[LeadRecord]) -> None:
    data = [r.model_dump() for r in records]
    path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))


def export_csv(path: Path, records: list[LeadRecord]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    flat = leads_to_dicts(records)
    fieldnames = list(flat[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(flat)
