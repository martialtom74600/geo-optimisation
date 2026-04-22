"""
Orchestration : Places → crawl Markdown → audit Groq — exécuté dans Celery via asyncio.run.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from app.activity_log import append_job_log
from app.config import settings
from app.database import AsyncSessionLocal
from app.models import DeepGeoJob, DeepGeoLead
from app.services.deep_crawl import deep_crawl_site
from app.services.groq_rag_audit import run_rag_audit
from app.services.places_google import fetch_places_for_zone

LOG = logging.getLogger(__name__)

_SEM_CRAWL = asyncio.Semaphore(5)
_SEM_GROQ = asyncio.Semaphore(max(1, settings.groq_max_concurrent))


async def _crawl_one(url: str | None) -> tuple[str, str, list]:
    if not url:
        return "", "[]", []
    async with _SEM_CRAWL:
        return await deep_crawl_site(url)


async def _audit_one(
    name: str,
    address: str,
    website: str | None,
    md: str,
) -> object:
    async with _SEM_GROQ:
        return await run_rag_audit(name, address, website, md)


async def run_zone_job_async(job_id: int) -> None:
    try:
        async with AsyncSessionLocal() as db:
            job = await db.get(DeepGeoJob, job_id)
            if not job:
                LOG.error("Job %s introuvable", job_id)
                return
            if job.cancel_requested:
                job.status = "cancelled"
                job.progress_message = "Annulé avant démarrage."
                job.completed_at = datetime.utcnow()
                await db.commit()
                return

            job.status = "processing"
            job.progress_message = "Sourcing Google Places…"
            await append_job_log(
                db,
                job,
                "Démarrage Deep GEO V2 — Places API (text search) puis crawl Markdown et audit RAG (Groq).",
            )
            await db.commit()
            await db.refresh(job)

            try:
                places = await fetch_places_for_zone(
                    job.city,
                    job.metier_category,
                    max_places=max(1, job.max_total) * 2,
                )
            except Exception as e:  # noqa: BLE001
                job.status = "failed"
                job.error = str(e)[:4000]
                job.progress_message = "Échec sourcing Places."
                await append_job_log(db, job, f"Erreur Places : {job.error}")
                job.completed_at = datetime.utcnow()
                await db.commit()
                return

            await append_job_log(
                db,
                job,
                f"Places : {len(places)} établissement(s) distincts (avant plafond job).",
            )
            job.progress_message = f"{len(places)} lieux trouvés — crawl + audits…"
            await db.commit()

            # Plafonner
            cap = max(1, job.max_total)
            places = places[:cap]

            n_done = 0
            for ph in places:
                j = await db.get(DeepGeoJob, job_id)
                if j and j.cancel_requested:
                    job = j
                    job.status = "cancelled"
                    job.progress_message = "Arrêt demandé — finalisation…"
                    await append_job_log(db, job, "Interruption utilisateur : fin du job.")
                    job.completed_at = datetime.utcnow()
                    await db.commit()
                    return

                md, meta_json, _meta = await _crawl_one(ph.website)
                lead = DeepGeoLead(
                    job_id=job_id,
                    place_id=ph.place_id,
                    company_name=ph.name,
                    formatted_address=ph.address,
                    website=ph.website,
                    rating=ph.rating,
                    user_ratings_total=ph.user_ratings_total,
                    types_json=json.dumps(ph.types, ensure_ascii=False) if ph.types else None,
                    markdown_bundle=md or None,
                    crawl_pages_json=meta_json,
                    crawl_error=None
                    if (md and md.strip())
                    else "Aucun contenu exploitable (sans site ou HTML vide).",
                )

                if (md or "").strip() and (ph.website or "").strip():
                    try:
                        audit = await _audit_one(ph.name, ph.address, ph.website, md)
                        lead.entity_clarity_score = audit.entity_clarity_score
                        lead.rag_structure_score = audit.rag_structure_score
                        lead.eat_signals = audit.eat_signals
                        lead.geo_risk_analysis = audit.geo_risk_analysis
                        lead.high_ticket_hook = audit.high_ticket_hook
                        lead.raw_audit_json = audit.model_dump_json()
                    except Exception as e:  # noqa: BLE001
                        lead.skip_audit_reason = str(e)[:500]
                        LOG.exception("Audit Groq %s", ph.place_id)
                else:
                    lead.skip_audit_reason = "Pas de site web ou pas de texte — audit IA ignoré."

                db.add(lead)
                n_done += 1
                job = await db.get(DeepGeoJob, job_id)
                if job:
                    job.lead_count = n_done
                    job.progress_message = f"Traitement {n_done}/{len(places)} — {ph.name[:50]}"
                await db.commit()

            job = await db.get(DeepGeoJob, job_id)
            if job and job.status == "processing":
                job.status = "completed"
                job.progress_message = f"Terminé — {n_done} lead(s) enregistré(s)."
                await append_job_log(db, job, job.progress_message)
                job.completed_at = datetime.utcnow()
                await db.commit()
    except Exception as e:  # noqa: BLE001
        LOG.exception("Job %s crash", job_id)
        async with AsyncSessionLocal() as db:
            job = await db.get(DeepGeoJob, job_id)
            if job:
                job.status = "failed"
                job.error = str(e)[:4000]
                job.progress_message = "Échec interne du pipeline."
                job.completed_at = datetime.utcnow()
                await db.commit()
