from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models import DeepGeoJob, DeepGeoLead
from app.schemas import DeepGeoJobOut, DeepGeoLeadOut, ZoneJobCreateV2
from app.services.places_google import CATEGORY_TEXT_QUERY
from app.worker import celery_app, run_zone_job_task

router = APIRouter(prefix="/api/v2", tags=["deep-geo-v2"])


@router.get("/jobs/metier-categories")
async def metier_categories() -> list[dict[str, str]]:
    return [{"id": k, "label": k.replace("_", " ").title()} for k in CATEGORY_TEXT_QUERY]


@router.post("/jobs/zone", response_model=DeepGeoJobOut)
async def create_zone_job(
    body: ZoneJobCreateV2,
    db: AsyncSession = Depends(get_async_session),
) -> DeepGeoJob:
    if body.metier_category not in CATEGORY_TEXT_QUERY:
        raise HTTPException(
            400,
            f"Catégorie inconnue. Clés valides : {', '.join(sorted(CATEGORY_TEXT_QUERY))}",
        )
    job = DeepGeoJob(
        city=body.city.strip(),
        metier_category=body.metier_category.strip(),
        max_total=body.max_total,
        audit_all=body.audit_all,
        status="pending",
        progress_message="En file d’attente (Celery)…",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    async_result = run_zone_job_task.delay(job.id)
    job.celery_task_id = async_result.id
    job.progress_message = "Tâche Celery lancée — processing dès qu’un worker est libre."
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/jobs", response_model=list[DeepGeoJobOut])
async def list_jobs(
    limit: int = 50,
    db: AsyncSession = Depends(get_async_session),
) -> list[DeepGeoJob]:
    stmt = select(DeepGeoJob).order_by(DeepGeoJob.created_at.desc()).limit(min(limit, 200))
    rows = (await db.scalars(stmt)).all()
    return list(rows)


@router.get("/jobs/{job_id}", response_model=DeepGeoJobOut)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> DeepGeoJob:
    j = await db.get(DeepGeoJob, job_id)
    if not j:
        raise HTTPException(404, "Job introuvable")
    return j


@router.post("/jobs/{job_id}/cancel", response_model=DeepGeoJobOut)
async def cancel_job(
    job_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> DeepGeoJob:
    j = await db.get(DeepGeoJob, job_id)
    if not j:
        raise HTTPException(404, "Job introuvable")
    if j.status in ("completed", "failed", "cancelled"):
        raise HTTPException(400, "Job déjà terminé.")
    j.cancel_requested = True
    j.progress_message = "Annulation demandée…"
    await db.commit()
    await db.refresh(j)
    return j


@router.get("/leads", response_model=list[DeepGeoLeadOut])
async def list_leads(
    job_id: int | None = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_async_session),
) -> list[DeepGeoLead]:
    stmt = select(DeepGeoLead).order_by(DeepGeoLead.id.desc()).limit(min(limit, 2000))
    if job_id is not None:
        stmt = (
            select(DeepGeoLead)
            .where(DeepGeoLead.job_id == job_id)
            .order_by(DeepGeoLead.id.desc())
            .limit(min(limit, 2000))
        )
    rows = (await db.scalars(stmt)).all()
    return list(rows)


@router.get("/health")
async def health_v2() -> dict[str, str]:
    return {"status": "ok", "engine": "deep-geo-v2"}
