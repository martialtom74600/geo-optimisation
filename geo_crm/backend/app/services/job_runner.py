from __future__ import annotations

import logging
import time
from datetime import datetime

from sqlalchemy.orm import Session

from app.activity_log import append_job_activity
from app.database import SessionLocal
from app.models import SourcingJob
from app.persist import lead_row_from_record
from geo_stealth_prospector.config import Settings
from geo_stealth_prospector.exceptions import JobCancelled
from geo_stealth_prospector.pipeline import ZonePipelineConfig, run_zone_pipeline

LOG = logging.getLogger(__name__)

_STATUS_COMMIT_INTERVAL_S = 0.48


_INTRO_LINES = (
    "Vue d’ensemble : le moteur va enchaîner plusieurs étapes pour vous. "
    "D’abord, un moteur de recherche (DuckDuckGo) est interrogé pour chaque famille de métiers « à ticket élevé », "
    "afin de lister des sites d’entreprises locales. Ensuite, les doublons par domaine sont fusionnés et on applique votre plafond de prospects. "
    "Puis chaque page d’accueil est téléchargée pour vérifier si le site expose déjà des données structurées (JSON-LD / schema.org). "
    "Enfin, pour les sites qui ne sont pas déjà bien fournis, un modèle d’IA (Groq) peut produire une analyse GEO détaillée. "
    "Les pauses courtes entre métiers limitent le risque de blocage côté moteur.",
    "Étape 1 — Sourcing par métier : une seule session réseau est réutilisée pour toutes les requêtes DuckDuckGo (plus rapide qu’avant). "
    "Dès qu’assez de « pistes brutes » sont collectées pour votre plafond, on peut s’arrêter avant d’avoir parcouru toute la liste de métiers.",
    "Étape 2 — Déduplication : on ne garde qu’une entrée par nom de domaine enregistré, pour éviter les doublons entre requêtes.",
    "Étape 3 — Crawl : téléchargement des pages d’accueil (preuves techniques : titres, JSON-LD).",
    "Étape 4 — Audits IA (optionnel) : appels Groq ciblés ; le filtre « cash machine » évite de re-facturer les sites déjà optimisés.",
)


async def run_zone_sourcing_job(job_id: int) -> None:
    """Tâche de fond : pipeline zone async + écriture SQLite."""
    db: Session = SessionLocal()
    last_commit = 0.0

    def flush_job() -> None:
        nonlocal last_commit
        try:
            db.commit()
            last_commit = time.monotonic()
        except Exception:  # noqa: BLE001
            db.rollback()
            LOG.exception("Maj statut job")

    try:
        job = db.get(SourcingJob, job_id)
        if not job:
            return
        if job.status in ("completed", "failed", "cancelled"):
            return
        if job.cancel_requested:
            job.status = "cancelled"
            job.progress_message = "Recherche annulée avant le démarrage."
            job.completed_at = datetime.utcnow()
            append_job_activity(
                db,
                job,
                "Annulation : le job était encore en file ; aucune étape n’a été lancée.",
            )
            db.commit()
            return

        job.status = "running"
        job.progress_message = "Démarrage du pipeline…"
        for line in _INTRO_LINES:
            append_job_activity(db, job, line)
        flush_job()

        settings = Settings()

        def on_status(msg: str) -> None:
            nonlocal last_commit
            j = db.get(SourcingJob, job_id)
            if j and j.cancel_requested:
                raise JobCancelled()
            if not j:
                return
            j.progress_message = msg
            append_job_activity(db, j, msg)
            now = time.monotonic()
            if now - last_commit >= _STATUS_COMMIT_INTERVAL_S:
                flush_job()

        def is_cancelled() -> bool:
            j = db.get(SourcingJob, job_id)
            return bool(j and j.cancel_requested)

        cat = (job.metier_category or "high_ticket").strip() or "high_ticket"
        cfg = ZonePipelineConfig(
            city=job.city,
            max_total=max(1, job.max_total),
            max_per_metier=max(1, job.max_per_metier),
            audit_all=bool(job.audit_all),
            skip_crawl_audit=False,
            metier_category=cat,
        )

        rows = await run_zone_pipeline(
            settings,
            cfg,
            on_status=on_status,
            on_cancel=is_cancelled,
        )

        flush_job()

        for rec in rows:
            db.add(lead_row_from_record(rec, job_id))
        j = db.get(SourcingJob, job_id)
        if j:
            j.status = "completed"
            j.lead_count = len(rows)
            final = f"Terminé — {len(rows)} lead(s) enregistré(s) en base."
            j.progress_message = final
            append_job_activity(db, j, final)
            j.completed_at = datetime.utcnow()
        db.commit()
        LOG.info("Job %s OK, %s leads", job_id, len(rows))
    except JobCancelled:
        try:
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        try:
            j = db.get(SourcingJob, job_id)
            if j:
                j.status = "cancelled"
                j.progress_message = "Recherche arrêtée sur demande."
                append_job_activity(
                    db,
                    j,
                    "Interruption confirmée : plus aucune nouvelle étape n’est lancée. "
                    "Les requêtes réseau encore ouvertes ont été coupées ou annulées ; le job est clos.",
                )
                j.error = None
                j.completed_at = datetime.utcnow()
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            LOG.exception("Maj job annulé %s", job_id)
        LOG.info("Job %s annulé par l'utilisateur", job_id)
    except Exception as e:  # noqa: BLE001
        LOG.exception("Job %s", job_id)
        try:
            db.rollback()
            j = db.get(SourcingJob, job_id)
            if j:
                j.status = "failed"
                j.error = str(e)[:4000]
                j.completed_at = datetime.utcnow()
                append_job_activity(
                    db,
                    j,
                    f"Erreur fatale : {j.error}",
                )
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
    finally:
        db.close()
