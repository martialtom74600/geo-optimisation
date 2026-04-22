from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.activity_log import append_job_activity
from app.database import get_db
from app.models import SourcingJob
from app.schemas import SourcingJobOut, ZoneJobCreate
from app.services.job_runner import run_zone_sourcing_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/zone", response_model=SourcingJobOut)
def create_zone_job(
    body: ZoneJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> SourcingJob:
    job = SourcingJob(
        city=body.city.strip(),
        status="queued",
        progress_message="En file d'attente…",
        max_total=body.max_total,
        max_per_metier=body.max_per_metier,
        audit_all=body.audit_all,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(run_zone_sourcing_job, job.id)
    return job


@router.get("", response_model=list[SourcingJobOut])
def list_jobs(
    limit: int = 50, db: Session = Depends(get_db)
) -> list[SourcingJob]:
    stmt = select(SourcingJob).order_by(SourcingJob.created_at.desc()).limit(min(limit, 200))
    return list(db.scalars(stmt).all())


@router.get("/{job_id}", response_model=SourcingJobOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> SourcingJob:
    j = db.get(SourcingJob, job_id)
    if not j:
        raise HTTPException(404, "Job introuvable")
    return j


@router.post("/{job_id}/cancel", response_model=SourcingJobOut)
def cancel_job(job_id: int, db: Session = Depends(get_db)) -> SourcingJob:
    j = db.get(SourcingJob, job_id)
    if not j:
        raise HTTPException(404, "Job introuvable")
    if j.status not in ("queued", "running"):
        raise HTTPException(
            400, "Seules les recherches en attente ou en cours peuvent être arrêtées."
        )
    j.cancel_requested = True
    if j.status == "queued":
        j.status = "cancelled"
        j.progress_message = "Recherche annulée avant le démarrage."
        j.completed_at = datetime.utcnow()
        append_job_activity(
            db,
            j,
            "Annulation immédiate : le job n’avait pas encore démarré, rien n’a été exécuté.",
        )
    else:
        j.progress_message = "Arrêt demandé — fermeture des connexions et des tâches en attente…"
        append_job_activity(
            db,
            j,
            "Vous avez demandé l’arrêt : le pipeline reçoit le signal, ferme les sessions HTTP "
            "ouvertes (DuckDuckGo, crawls) et annule les tâches qui n’avaient pas encore commencé.",
        )
    db.add(j)
    db.commit()
    db.refresh(j)
    return j
