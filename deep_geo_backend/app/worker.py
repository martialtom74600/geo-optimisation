"""
Celery — file d’attente Redis, workers séparés de l’API FastAPI.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

# Charge le .env avant les settings (dev local)
from dotenv import load_dotenv

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_root, ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from celery import Celery

from app.config import settings
from app.pipeline.runner import run_zone_job_async

LOG = logging.getLogger(__name__)

celery_app = Celery(
    "deep_geo",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600 * 6,
    worker_prefetch_multiplier=1,
)

# Windows : le pool prefork (multiprocessing) provoque souvent WinError 5 sur les sémaphores.
# `solo` = un seul processus ; adapté à asyncio.run() dans les tâches.
if sys.platform == "win32":
    celery_app.conf.worker_pool = "solo"
    celery_app.conf.worker_concurrency = 1


@celery_app.task(name="deep_geo.run_zone_job", bind=True)
def run_zone_job_task(self, job_id: int) -> str:
    """Point d’entrée worker : exécute le pipeline async dans l’event loop."""
    LOG.info("Celery task start job_id=%s task_id=%s", job_id, self.request.id)
    try:
        asyncio.run(run_zone_job_async(job_id))
    except Exception:
        LOG.exception("Job %s failed", job_id)
        raise
    return f"job {job_id} done"
