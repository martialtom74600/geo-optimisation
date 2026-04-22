"""
Crawl ciblé de la page d'accueil : preuves factuelles (JSON-LD, title, H1).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from contextlib import suppress
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from geo_stealth_prospector.async_cancel import gather_cancel_siblings, run_httpx_close_on_cancel
from geo_stealth_prospector.config import Settings
from geo_stealth_prospector.exceptions import JobCancelled
from geo_stealth_prospector.models import CrawlResult

LOG = logging.getLogger(__name__)

# @type considérés comme « preuve » d’entité structurée côté business / lieu
# (pastille verte si au moins l’un d’eux apparaît dans un bloc JSON-LD valide)
RELEVANT_SCHEMA_TYPES: frozenset[str] = frozenset(
    {
        "LocalBusiness",
        "Organization",
        "Store",
        "HomeAndConstructionBusiness",
        "ProfessionalService",
        "Plumber",
        "Electrician",
        "HVACBusiness",
        "FoodEstablishment",
        "AutomotiveBusiness",
    }
)


def _iter_jsonld_types(obj: Any) -> list[str]:
    """Parcourt un objet JSON et collecte toutes les valeurs @type (récursif, @graph inclus)."""
    out: list[str] = []
    if obj is None:
        return out
    if isinstance(obj, dict):
        t = obj.get("@type")
        if isinstance(t, str):
            out.append(t)
        elif isinstance(t, list):
            for x in t:
                if isinstance(x, str):
                    out.append(x)
        for v in obj.values():
            out.extend(_iter_jsonld_types(v))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_iter_jsonld_types(item))
    return out


def _parse_jsonld_blocks(raw: str) -> tuple[list[str], set[str]]:
    """
    Tente de parser le texte d’un <script> application/ld+json.
    Retourne (types trouvés, set des @type en chaîne).
    """
    found_types: list[str] = []
    type_set: set[str] = set()
    s = raw.strip()
    if not s:
        return found_types, type_set
    try:
        data = json.loads(s)
    except json.JSONDecodeError as e:
        # Parfois plusieurs objets collés (ou junk) : essayer d’isoler le premier { ... }
        m = re.search(r"(\{[\s\S]*\})", s)
        if m:
            try:
                data = json.loads(m.group(1))
            except json.JSONDecodeError:
                LOG.debug("JSON-LD illisible: %s", e)
                return found_types, type_set
        else:
            LOG.debug("JSON-LD non parseable: %s", e)
            return found_types, type_set
    for t in _iter_jsonld_types(data):
        t_clean = t.strip()
        if t_clean and t_clean not in type_set:
            type_set.add(t_clean)
            found_types.append(t_clean)
    return found_types, type_set


def _extract_title_soup(soup: BeautifulSoup) -> str:
    t = soup.find("title")
    if t and t.get_text(strip=True):
        return t.get_text(" ", strip=True)
    og = soup.find("meta", property=re.compile(r"^og:title$", re.I), attrs={"content": True})
    if og and og.get("content"):
        return str(og["content"]).strip()
    return ""


def _extract_h1s(soup: BeautifulSoup, limit: int = 5) -> list[str]:
    out: list[str] = []
    for h in soup.find_all("h1", limit=limit * 2):
        txt = h.get_text(" ", strip=True)
        if txt and txt not in out:
            out.append(txt)
        if len(out) >= limit:
            break
    return out


async def _read_body_limited(
    response: httpx.Response,
    max_bytes: int,
) -> bytes:
    buf = bytearray()
    count = 0
    async for chunk in response.aiter_bytes():
        if not chunk:
            break
        need = min(len(chunk), max_bytes - count)
        if need <= 0:
            break
        buf.extend(chunk[:need])
        count += need
        if count >= max_bytes:
            break
    return bytes(buf)


async def crawl_homepage(
    url: str,
    client: httpx.AsyncClient,
    settings: Settings,
) -> CrawlResult:
    """
    Télécharge l’URL (redirections suivies), parse le HTML, extrait preuves JSON-LD, title, H1.
    """
    raw = (url or "").strip()
    if not raw.lower().startswith(("http://", "https://")):
        raw = f"https://{raw}"

    r = CrawlResult(page_fetched=False, final_url=raw)
    encoding = "utf-8"
    data = b""
    try:
        async with client.stream(
            "GET",
            raw,
            follow_redirects=True,
            timeout=settings.crawl_timeout_s,
        ) as resp:
            r.http_status = resp.status_code
            r.final_url = str(resp.url)
            encoding = (resp.encoding or "utf-8") if resp.encoding else "utf-8"
            if resp.status_code >= 400:
                r.error = f"HTTP {resp.status_code}"
                return r
            data = await _read_body_limited(resp, settings.crawl_max_bytes)
        r.page_fetched = True
    except (httpx.HTTPError, OSError) as e:
        r.error = str(e) or type(e).__name__
        return r

    try:
        html = data.decode(encoding, errors="replace")
    except (LookupError, TypeError, ValueError):
        html = data.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    r.title = _extract_title_soup(soup)
    r.h1_texts = _extract_h1s(soup)
    r.has_jsonld_script = False
    r.jsonld_types_found = []

    for script in soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)}):
        r.has_jsonld_script = True
        inner = script.string or script.get_text() or ""
        types_list, tset = _parse_jsonld_blocks(inner)
        for t in types_list:
            if t not in r.jsonld_types_found:
                r.jsonld_types_found.append(t)

    r.has_relevant_business_schema = _has_relevant_business_type(r.jsonld_types_found)
    return r


def _has_relevant_business_type(types_found: list[str]) -> bool:
    """Vrai si un @type explicite un schéma « entreprise / lieu » (y compris IRI https://schema.org/...)."""
    for t in types_found:
        u = t.strip()
        if not u:
            continue
        if u in RELEVANT_SCHEMA_TYPES:
            return True
        if "schema.org" in u:
            local = u.rsplit("/", 1)[-1]
            if local in RELEVANT_SCHEMA_TYPES:
                return True
    return False


async def crawl_leads_concurrent(
    leads: list[Any],
    settings: Settings,
    *,
    on_status: Callable[[str], None] | None = None,
    on_cancel: Callable[[], bool] | None = None,
) -> None:
    """
    Remplit ``lead.crawl`` pour chaque lead, avec un sémaphore.
    `leads` est une liste de ``LeadRecord``.
    """
    if not leads:
        return
    n = len(leads)
    sem = asyncio.Semaphore(settings.crawl_max_concurrent)
    lim = httpx.Limits(max_connections=settings.crawl_max_concurrent + 2, max_keepalive_connections=4)
    done = 0
    lock = asyncio.Lock()
    step = max(1, n // 10) if n > 10 else 1

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": settings.user_agent},
        limits=lim,
    ) as client:
        close_watch = asyncio.create_task(
            run_httpx_close_on_cancel(client, on_cancel)
        )

        async def one(lead: Any) -> None:
            nonlocal done
            if on_cancel and on_cancel():
                raise JobCancelled()
            async with sem:
                if on_cancel and on_cancel():
                    raise JobCancelled()
                try:
                    lead.crawl = await crawl_homepage(lead.url, client, settings)
                except JobCancelled:
                    raise
                except Exception as e:  # noqa: BLE001
                    if on_cancel and on_cancel():
                        raise JobCancelled() from e
                    LOG.warning("Crawl %s: %s", lead.url, e)
                    lead.crawl = CrawlResult(
                        page_fetched=False,
                        final_url=lead.url,
                        error=str(e) or type(e).__name__,
                    )
            if on_status:
                async with lock:
                    done += 1
                    d = done
                if d == n or d % step == 0 or d <= 2:
                    pct = round(100 * d / n)
                    on_status(f"Crawl pages d'accueil : {d}/{n} ({pct} %) — JSON-LD / title / H1")

        try:
            await gather_cancel_siblings([one(L) for L in leads])
        finally:
            close_watch.cancel()
            with suppress(asyncio.CancelledError):
                await close_watch
