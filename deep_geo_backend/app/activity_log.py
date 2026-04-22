from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DeepGeoJob


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def append_job_log(db: AsyncSession, job: DeepGeoJob, message: str) -> None:
    raw = (job.activity_log_json or "[]").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = []
    if not isinstance(data, list):
        data = []
    data.append({"at": _now_iso(), "message": message[:8000]})
    job.activity_log_json = json.dumps(data, ensure_ascii=False)
    await db.flush()
