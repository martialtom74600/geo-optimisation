"""
Deep crawl → Markdown : Firecrawl (si clé), sinon httpx + trafilatura (+ option crawl4ai).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura

from app.config import settings

LOG = logging.getLogger(__name__)

DEFAULT_PATHS = (
    "/",
    "/a-propos",
    "/about",
    "/services",
    "/prestations",
    "/notre-entreprise",
)


@dataclass(slots=True)
class PageChunk:
    url: str
    path: str
    markdown: str


def _origin(url: str) -> str:
    p = urlparse(url if "://" in url else f"https://{url}")
    if not p.scheme:
        p = urlparse(f"https://{url}")
    return f"{p.scheme}://{p.netloc}"


def _html_to_md(html: str, url: str) -> str:
    if not (html or "").strip():
        return ""
    txt = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
        output_format="markdown",
    )
    if txt and txt.strip():
        return txt.strip()
    # secours : texte brut
    t2 = trafilatura.extract(html, url=url, output_format="txt")
    return (t2 or "").strip()


async def _fetch_url(client: httpx.AsyncClient, url: str) -> tuple[str, str | None]:
    try:
        r = await client.get(
            url,
            follow_redirects=True,
            timeout=settings.crawl_timeout_s,
        )
        ct = (r.headers.get("content-type") or "").lower()
        if r.status_code >= 400:
            return "", f"HTTP {r.status_code}"
        if "html" not in ct and "text" not in ct and r.content:
            # tenter quand même
            pass
        raw = r.text or ""
        return raw, None
    except Exception as e:  # noqa: BLE001
        return "", str(e)[:500]


async def _firecrawl_markdown(url: str) -> str | None:
    key = (settings.firecrawl_api_key or "").strip()
    if not key:
        return None
    api = f"{settings.firecrawl_base_url.rstrip('/')}/v1/scrape"
    try:
        async with httpx.AsyncClient(timeout=90.0, trust_env=settings.httpx_trust_env) as c:
            r = await c.post(
                api,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "url": url,
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                },
            )
            r.raise_for_status()
            data = r.json()
            d = data.get("data") or data
            if isinstance(d, dict):
                md = d.get("markdown") or d.get("md")
                if isinstance(md, str) and md.strip():
                    return md.strip()
    except Exception as e:  # noqa: BLE001
        LOG.warning("Firecrawl échec %s : %s", url, e)
    return None


async def deep_crawl_site(website: str) -> tuple[str, str, list[dict[str, Any]]]:
    """
    Retourne (markdown_bundle, crawl_pages_json str, meta list).
    """
    if not (website or "").strip():
        return "", "[]", []

    base = website.strip()
    if not base.startswith("http"):
        base = "https://" + base
    origin = _origin(base)

    pages: list[PageChunk] = []
    meta: list[dict[str, Any]] = []

    # 1) Firecrawl sur la home si configuré
    fc = await _firecrawl_markdown(base)
    if fc:
        pages.append(PageChunk(url=base, path="/", markdown=fc))
        meta.append({"url": base, "path": "/", "chars": len(fc), "source": "firecrawl"})
    else:
        headers = {"User-Agent": settings.crawl_user_agent, "Accept-Language": "fr-FR,fr;q=0.9"}
        limits = httpx.Limits(max_connections=8, max_keepalive_connections=4)
        async with httpx.AsyncClient(
            headers=headers,
            limits=limits,
            follow_redirects=True,
            trust_env=settings.httpx_trust_env,
        ) as client:
            paths = list(DEFAULT_PATHS)[: settings.crawl_max_pages]
            for path in paths:
                u = urljoin(origin + "/", path.lstrip("/"))
                html, err = await _fetch_url(client, u)
                if err and not html:
                    meta.append({"url": u, "path": path, "error": err})
                    continue
                md = _html_to_md(html, u)
                if md:
                    pages.append(PageChunk(url=u, path=path, markdown=md))
                    meta.append({"url": u, "path": path, "chars": len(md), "source": "trafilatura"})
                else:
                    meta.append({"url": u, "path": path, "chars": 0, "skipped": True})
                await asyncio.sleep(0.15)

    if not pages:
        bundle = ""
    else:
        parts = [f"## Page: {p.path}\nSource: {p.url}\n\n{p.markdown}" for p in pages]
        bundle = "\n\n---\n\n".join(parts)

    meta_s = json.dumps(meta, ensure_ascii=False)
    return bundle, meta_s, meta
