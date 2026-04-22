"""Journal d'activité des jobs (JSON côté DB, listes côté API)."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import SourcingJob

_MAX_LINES = 800


def _iso_utc() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def append_job_activity(db: Session, job: SourcingJob, message: str) -> None:
    """Ajoute une ligne au journal JSON du job (même entité, pas de re-fetch si déjà liée)."""
    try:
        log = json.loads(job.activity_log_json or "[]")
    except json.JSONDecodeError:
        log = []
    if not isinstance(log, list):
        log = []
    log.append({"at": _iso_utc(), "message": message})
    if len(log) > _MAX_LINES:
        log = log[-_MAX_LINES :]
    job.activity_log_json = json.dumps(log, ensure_ascii=False)
    db.add(job)
