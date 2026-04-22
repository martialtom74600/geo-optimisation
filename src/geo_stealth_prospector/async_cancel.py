"""Aides async pour annulation rapide (sleep fragmenté, annulation tâches sœurs)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import TypeVar

import httpx

from geo_stealth_prospector.exceptions import JobCancelled

T = TypeVar("T")


async def sleep_cancellable(
    total_s: float,
    on_cancel: Callable[[], bool] | None,
    *,
    step_s: float = 0.45,
) -> None:
    """
    Comme ``asyncio.sleep`` mais interrompible : vérifie ``on_cancel`` ~chaque *step_s*.
    Lève :exc:`JobCancelled` si l’annulation est demandée.
    """
    if on_cancel and on_cancel():
        raise JobCancelled()
    if total_s <= 0:
        return
    remaining = float(total_s)
    while remaining > 0:
        if on_cancel and on_cancel():
            raise JobCancelled()
        chunk = min(float(step_s), remaining)
        await asyncio.sleep(chunk)
        remaining -= chunk


async def gather_cancel_siblings(
    coros: list[Coroutine[object, object, T]],
) -> list[T]:
    """
    Comme ``asyncio.gather`` sur des tâches explicites, mais propage
    :exc:`JobCancelled` en annulant les coroutines sœurs encore en cours
    (crawls / audits qui attendent le sémaphore ou n’ont pas démarré).
    """
    if not coros:
        return []
    tasks = [asyncio.create_task(c) for c in coros]
    try:
        return list(await asyncio.gather(*tasks))
    except JobCancelled:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise


async def run_httpx_close_on_cancel(
    client: httpx.AsyncClient,
    on_cancel: Callable[[], bool] | None,
    *,
    poll_s: float = 0.15,
) -> None:
    """
    Surveille l’annulation et ferme le client httpx, ce qui interrompt
    les requêtes HTTP en cours dès que le transport le permet.
    """
    if not on_cancel:
        return
    try:
        while True:
            await asyncio.sleep(poll_s)
            if on_cancel():
                try:
                    await client.aclose()
                except (RuntimeError, OSError, httpx.HTTPError, ValueError, TypeError):
                    pass
                return
    except asyncio.CancelledError:
        return
