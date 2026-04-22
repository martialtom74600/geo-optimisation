"""
Recherche via la version HTML de DuckDuckGo (POST, pas d'API Google).
Évite d'abuser des endpoints JSON non documentés et limite le profil "bot" évident.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time
import urllib.parse
from html import unescape

import httpx
from collections.abc import Callable

from geo_stealth_prospector import tldx
from bs4 import BeautifulSoup

from geo_stealth_prospector.async_cancel import sleep_cancellable
from geo_stealth_prospector.config import Settings
from geo_stealth_prospector.exceptions import JobCancelled
from geo_stealth_prospector.filters import is_probably_independent_site
from geo_stealth_prospector.models import SearchHit

LOG = logging.getLogger(__name__)

DDG_HTML_URL = "https://html.duckduckgo.com/html/"

# Client HTTP : au moins 30 s (connect + read) pour DuckDuckGo
_DDG_MIN_TIMEOUT_S = 30.0
# Avant chaque requête de recherche (POST) — aléatoire, ne pas raccourcir
_DDG_ANTI_BOT_DELAY_MIN_S = 4.0
_DDG_ANTI_BOT_DELAY_MAX_S = 8.0
# Entre chaque échec (1re→2e, 2e→3e tentative)
_RETRY_BACKOFF_S = (1.0, 2.0, 4.0)
_DDG_MAX_ATTEMPTS = 3

_RETRIABLE = (
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.PoolTimeout,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.RemoteProtocolError,
    httpx.WriteError,
)


def _httpx_ddg_timeout(settings: Settings) -> httpx.Timeout:
    t = max(_DDG_MIN_TIMEOUT_S, float(settings.http_timeout_s))
    return httpx.Timeout(t)


def _ddg_accept_language() -> str:
    return "fr-FR,fr;q=0.9"


def _ddg_bootstrap_headers(settings: Settings) -> dict[str, str]:
    return {
        "User-Agent": settings.user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": _ddg_accept_language(),
    }


def _ddg_post_headers(settings: Settings) -> dict[str, str]:
    return {
        "User-Agent": settings.user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": _ddg_accept_language(),
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": str(settings.ddg_referer),
        "Origin": "https://html.duckduckgo.com",
    }


def _format_http_error(e: BaseException) -> str:
    """httpx a souvent str(e) vide — on ajoute le type, le code HTTP et un extrait de corps si dispo."""
    parts: list[str] = [type(e).__name__]
    s = str(e).strip()
    if s:
        parts.append(s)
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            parts.append(f"status={resp.status_code}")
            body = (resp.text or "")[:600].replace("\n", " ")
            if body.strip():
                parts.append(f"corps (extrait)={body!r}")
        except Exception:  # noqa: BLE001
            parts.append("(corps de réponse non lu)")
    return " | ".join(parts)


async def bootstrap_duck_html_session(
    client: httpx.AsyncClient,
    settings: Settings,
    *,
    on_cancel: Callable[[], bool] | None = None,
) -> None:
    """
    GET d'amorçage (cookies) — comme avant, en cas d'échec final on log et on enchaîne le POST
    (plusieurs essais : timeouts, erreurs HTTP).
    """
    for attempt in range(_DDG_MAX_ATTEMPTS):
        if on_cancel and on_cancel():
            raise JobCancelled()
        try:
            r = await client.get(
                DDG_HTML_URL,
                headers=_ddg_bootstrap_headers(settings),
                follow_redirects=True,
                timeout=_httpx_ddg_timeout(settings),
            )
            r.raise_for_status()
            return
        except JobCancelled:
            raise
        except _RETRIABLE as e:  # type: ignore[misc]
            if attempt < _DDG_MAX_ATTEMPTS - 1:
                LOG.warning(
                    "DuckDuckGo bootstrap (GET) — %s, retry %s/%s",
                    _format_http_error(e),
                    attempt + 1,
                    _DDG_MAX_ATTEMPTS,
                )
                await sleep_cancellable(_RETRY_BACKOFF_S[attempt], on_cancel)
            else:
                LOG.warning(
                    "Bootstrap DuckDuckGo ignoré après %s essais — %s",
                    _DDG_MAX_ATTEMPTS,
                    _format_http_error(e),
                )
        except httpx.HTTPStatusError as e:
            if attempt < _DDG_MAX_ATTEMPTS - 1:
                st = e.response.status_code if e.response else 0
                LOG.warning(
                    "DuckDuckGo bootstrap (GET) — HTTP %s, retry %s/%s",
                    st,
                    attempt + 1,
                    _DDG_MAX_ATTEMPTS,
                )
                await sleep_cancellable(_RETRY_BACKOFF_S[attempt], on_cancel)
            else:
                LOG.warning(
                    "Bootstrap DuckDuckGo ignoré (HTTP) — %s", _format_http_error(e)
                )
        except Exception as e:  # noqa: BLE001
            if attempt < _DDG_MAX_ATTEMPTS - 1:
                LOG.warning(
                    "DuckDuckGo bootstrap (GET) — %s, retry %s/%s",
                    _format_http_error(e),
                    attempt + 1,
                    _DDG_MAX_ATTEMPTS,
                )
                await sleep_cancellable(_RETRY_BACKOFF_S[attempt], on_cancel)
            else:
                LOG.warning("Bootstrap DuckDuckGo ignoré — %s", _format_http_error(e))
    return


def _resolve_duck_redirect(href: str) -> str | None:
    """
    Les résultats pointent souvent vers /l/?uddg=... — extraire l'URL cible.
    """
    if not href:
        return None
    h = href.strip()
    if h.startswith("//"):
        h = "https:" + h
    p = urllib.parse.urlparse(h)
    q = urllib.parse.parse_qs(p.query)
    uddg = q.get("uddg", [None])[0]
    if uddg:
        return urllib.parse.unquote(uddg)
    if p.scheme in ("http", "https") and p.netloc and p.netloc != "duckduckgo.com":
        return h
    m = re.search(r"uddg=([^&]+)", h)
    if m:
        return urllib.parse.unquote(m.group(1))
    return None


def _extract_hits_from_html(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    pairs: list[tuple[str, str]] = []
    for a in soup.find_all("a", class_=re.compile(r"result__a", re.I)):
        href = a.get("href") or ""
        if not href or href == "#":
            continue
        resolved = _resolve_duck_redirect(href) or (href if href.startswith("http") else None)
        if not resolved or "duckduckgo.com" in resolved:
            continue
        title = unescape(a.get_text(" ", strip=True))
        pairs.append((resolved, title))
    if pairs:
        return pairs
    for a in soup.select("a.result__a, .web-result a, .result a"):
        href = a.get("href") or ""
        if not href or href == "#":
            continue
        resolved = _resolve_duck_redirect(href) or (href if href.startswith("http") else None)
        if not resolved or "duckduckgo.com" in resolved:
            continue
        title = unescape(a.get_text(" ", strip=True))
        pairs.append((resolved, title))
    return pairs


async def _ddg_post_search_once(
    client: httpx.AsyncClient, query: str, settings: Settings
) -> str:
    data = {
        "q": query,
        "b": "",
        "kl": "fr-fr",
    }
    r = await client.post(
        DDG_HTML_URL,
        data=data,
        headers=_ddg_post_headers(settings),
        follow_redirects=True,
        timeout=_httpx_ddg_timeout(settings),
    )
    r.raise_for_status()
    return r.text


async def _ddg_post_search_with_retry(
    client: httpx.AsyncClient,
    query: str,
    settings: Settings,
    *,
    on_cancel: Callable[[], bool] | None = None,
) -> str:
    for attempt in range(_DDG_MAX_ATTEMPTS):
        if on_cancel and on_cancel():
            raise JobCancelled()
        try:
            raw = await _ddg_post_search_once(client, query, settings)
            if len((raw or "").strip()) < 200:
                LOG.warning(
                    "DuckDuckGo : HTML très court (%s car.) pour %r — moteur dégradé / anti-bot possible.",
                    len(raw or ""),
                    query[:80],
                )
            return raw
        except JobCancelled:
            raise
        except _RETRIABLE as e:  # type: ignore[misc]
            if attempt < _DDG_MAX_ATTEMPTS - 1:
                LOG.warning(
                    "DuckDuckGo POST — %s, retry %s/%s",
                    _format_http_error(e),
                    attempt + 1,
                    _DDG_MAX_ATTEMPTS,
                )
                await sleep_cancellable(_RETRY_BACKOFF_S[attempt], on_cancel)
            else:
                raise
        except httpx.HTTPStatusError as e:
            st = e.response.status_code if e.response is not None else 0
            if attempt < _DDG_MAX_ATTEMPTS - 1:
                LOG.warning(
                    "DuckDuckGo POST — HTTP %s, retry %s/%s",
                    st,
                    attempt + 1,
                    _DDG_MAX_ATTEMPTS,
                )
                await sleep_cancellable(_RETRY_BACKOFF_S[attempt], on_cancel)
            else:
                raise
        except Exception as e:  # noqa: BLE001
            if on_cancel and on_cancel():
                raise JobCancelled() from e
            if attempt < _DDG_MAX_ATTEMPTS - 1:
                LOG.warning(
                    "DuckDuckGo POST — %s, retry %s/%s",
                    _format_http_error(e),
                    attempt + 1,
                    _DDG_MAX_ATTEMPTS,
                )
                await sleep_cancellable(_RETRY_BACKOFF_S[attempt], on_cancel)
            else:
                raise
    raise RuntimeError("DuckDuckGo POST: aucune exception levée en fin de boucle (ne devrait pas arriver).")


def _default_queries(metier: str, city: str) -> list[str]:
    m, c = metier.strip(), city.strip()
    return [
        f"{m} {c} artisan site",
        f"{m} {c} entreprise locale",
        f'"{m}" {c} site officiel -pagesjaunes -facebook',
    ]


async def search_leads_furtif_with_client(
    client: httpx.AsyncClient,
    metier: str,
    city: str,
    settings: Settings,
    max_results: int = 15,
    extra_delay_s: float = 0.0,
    *,
    on_cancel: Callable[[], bool] | None = None,
) -> list[SearchHit]:
    if max_results < 1:
        return []
    queries = _default_queries(metier, city)
    seen_rd: set[str] = set()
    hits: list[SearchHit] = []
    rank = 0
    extra = max(0.0, float(extra_delay_s))

    for q in queries:
        if on_cancel and on_cancel():
            raise JobCancelled()
        if len(hits) >= max_results:
            break
        delay_s = (
            random.uniform(_DDG_ANTI_BOT_DELAY_MIN_S, _DDG_ANTI_BOT_DELAY_MAX_S) + extra
        )
        await sleep_cancellable(delay_s, on_cancel)
        if on_cancel and on_cancel():
            raise JobCancelled()
        try:
            html = await _ddg_post_search_with_retry(
                client, q, settings, on_cancel=on_cancel
            )
        except (JobCancelled, httpx.HTTPError) as e:
            if on_cancel and on_cancel():
                raise JobCancelled() from e
            if isinstance(e, JobCancelled):
                raise
            LOG.warning(
                "DuckDuckGo requête échouée pour %r (après retries) — %s",
                q,
                _format_http_error(e),
            )
            continue
        except OSError as e:
            if on_cancel and on_cancel():
                raise JobCancelled() from e
            LOG.warning(
                "DuckDuckGo requête échouée pour %r — %s",
                q,
                _format_http_error(e),
            )
            continue

        pairs = _extract_hits_from_html(html)
        t0 = time.perf_counter()
        for url, title in pairs:
            if len(hits) >= max_results:
                break
            ext = tldx.tld(url)
            rd = ext.registered_domain or ext.domain
            if not rd:
                continue
            if not is_probably_independent_site(url, ext.registered_domain or None):
                continue
            key = rd.lower()
            if key in seen_rd:
                continue
            seen_rd.add(key)
            rank += 1
            hits.append(SearchHit(url=url, title=title, rank=rank))
        if time.perf_counter() - t0 < 0.1:
            await asyncio.sleep(0.2)

    return hits[:max_results]


async def search_leads_furtif(
    metier: str,
    city: str,
    settings: Settings,
    max_results: int = 15,
    extra_delay_s: float = 0.0,
    *,
    on_cancel: Callable[[], bool] | None = None,
) -> list[SearchHit]:
    limits = httpx.Limits(max_connections=5, max_keepalive_connections=3)
    async with httpx.AsyncClient(
        http2=False,
        limits=limits,
        trust_env=settings.httpx_trust_env,
    ) as client:
        await bootstrap_duck_html_session(
            client, settings, on_cancel=on_cancel
        )
        return await search_leads_furtif_with_client(
            client,
            metier,
            city,
            settings,
            max_results,
            extra_delay_s,
            on_cancel=on_cancel,
        )
