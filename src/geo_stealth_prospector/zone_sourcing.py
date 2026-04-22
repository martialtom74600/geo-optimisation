"""
Orchestrateur mode « zone » : enchaîne les requêtes DuckDuckGo par métier avec jitter anti-ban.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Callable
from contextlib import suppress

import httpx
from rich.progress import Progress, TaskID

from geo_stealth_prospector.async_cancel import run_httpx_close_on_cancel, sleep_cancellable
from geo_stealth_prospector.config import Settings
from geo_stealth_prospector.duck_search import (
    bootstrap_duck_html_session,
    search_leads_furtif_with_client,
)
from geo_stealth_prospector.exceptions import JobCancelled
from geo_stealth_prospector.models import LeadRecord
from geo_stealth_prospector.naming import derive_company_name

LOG = logging.getLogger(__name__)


async def zone_sourcing_multimetier(
    city: str,
    metiers: list[str],
    settings: Settings,
    *,
    max_per_metier: int,
    progress: Progress | None = None,
    task_id: TaskID | int | None = None,
    on_status: Callable[[str], None] | None = None,
    on_cancel: Callable[[], bool] | None = None,
    stop_after_raw_hits: int | None = None,
) -> list[LeadRecord]:
    """
    Pour chaque métier, appelle le sourcing furtif ; délai aléatoire entre chaque métier (hors le premier).
    `max_per_metier` plafonne les domaines uniques retournés par un passage DuckDuckGo.
    **Une** session HTTP + un bootstrap DDG pour tout l’enchaînement (évite 20x la même ouverture).
    Si ``stop_after_raw_hits`` est défini, arrête dès assez de pistes brutes (avant dédup / plafond job).
    """
    out: list[LeadRecord] = []
    city_s = city.strip()
    n = max(1, max_per_metier)
    r_global = 0
    mlist = [m.strip() for m in metiers if m.strip()]

    limits = httpx.Limits(max_connections=5, max_keepalive_connections=3)
    async with httpx.AsyncClient(
        http2=False,
        limits=limits,
        trust_env=settings.httpx_trust_env,
    ) as ddg_client:
        await bootstrap_duck_html_session(ddg_client, settings, on_cancel=on_cancel)
        close_watch = asyncio.create_task(
            run_httpx_close_on_cancel(ddg_client, on_cancel)
        )
        try:
            for i, metier in enumerate(mlist):
                if on_cancel and on_cancel():
                    raise JobCancelled()
                if i > 0:
                    lo, hi = settings.zone_metier_delay_min_s, settings.zone_metier_delay_max_s
                    if hi < lo:
                        lo, hi = hi, lo
                    delay = random.uniform(lo, hi)
                    if on_status:
                        on_status(
                            f"Pause anti-ban {delay:.1f}s avant métier {i + 1}/{len(mlist)} "
                            f"— « {metier} » · {city_s} — ce délai limite le risque de blocage côté moteur."
                        )
                    LOG.info("Jitter zone %.2fs avant métier %s", delay, metier)
                    await sleep_cancellable(delay, on_cancel)
                    if on_cancel and on_cancel():
                        raise JobCancelled()
                if on_status:
                    on_status(
                        f"Sourcing moteur : métier {i + 1}/{len(mlist)} — « {metier} » · {city_s} "
                        f"(jusqu’à {n} URL(s) distinctes pour ce métier)."
                    )
                if on_cancel and on_cancel():
                    raise JobCancelled()
                hits = await search_leads_furtif_with_client(
                    ddg_client,
                    metier,
                    city_s,
                    settings,
                    max_results=n,
                    on_cancel=on_cancel,
                )
                for h in hits:
                    r_global += 1
                    out.append(
                        LeadRecord(
                            company_name=derive_company_name(h.url),
                            url=h.url,
                            metier=metier,
                            city=city_s,
                            title=h.title,
                            source_rank=r_global,
                        )
                    )
                if on_status:
                    on_status(
                        f"Sourcing « {metier} » : {len(hits)} URL(s) retenue(s) — total cumulé {len(out)} piste(s) brute(s)."
                    )
                if progress is not None and task_id is not None:
                    progress.update(
                        task_id,
                        completed=i + 1,
                        total=len(mlist),
                        description=f"Zone — métier {i + 1}/{len(mlist)} : [bold]{metier}[/] · {city_s}",
                    )
                if stop_after_raw_hits is not None and len(out) >= stop_after_raw_hits:
                    if on_status:
                        on_status(
                            f"Objectif atteint ({len(out)} pistes brutes ≥ {stop_after_raw_hits}) : "
                            f"on n’interroge pas les métiers restants pour aller plus vite vers la suite."
                        )
                    break
        finally:
            close_watch.cancel()
            with suppress(asyncio.CancelledError):
                await close_watch

    return out
