"""
Connecteur Google Places API (New) — Text Search avec pagination.
https://developers.google.com/maps/documentation/places/web-service/text-search
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings

LOG = logging.getLogger(__name__)

PLACES_BASE = "https://places.googleapis.com/v1/places:searchText"

# requêtes `textQuery` (langue naturelle) par catégorie métier (id stable)
CATEGORY_TEXT_QUERY: dict[str, str] = {
    "high_ticket": "independent home service professional contractor in {city} France",
    "restauration": "restaurant cafe brasserie in {city} France",
    "hebergement_tourisme": "hotel bed and breakfast guesthouse in {city} France",
    "beaute_coiffure": "hair salon beauty spa in {city} France",
    "sante_medical": "medical clinic dentist doctor pharmacy in {city} France",
    "sport_fitness": "gym fitness yoga sports club in {city} France",
    "auto_moto": "car repair garage auto mechanic in {city} France",
    "immo_juridique": "real estate agency notary in {city} France",
    "btp_renovation": "plumber electrician construction renovation contractor in {city} France",
    "commerce_proximite": "local grocery store butcher bakery in {city} France",
    "services_b2b": "accounting lawyer consulting agency office in {city} France",
    "education_formation": "driving school training center in {city} France",
    "artisanat_arts": "craft workshop furniture upholstery photographer in {city} France",
}

FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.websiteUri",
        "places.rating",
        "places.userRatingCount",
        "places.types",
    ]
)


@dataclass(slots=True)
class PlaceHit:
    place_id: str
    name: str
    address: str
    website: str | None
    rating: float | None
    user_ratings_total: int | None
    types: list[str]


def _text_query_for_category(city: str, metier_category: str) -> str:
    c = city.strip()
    key = (metier_category or "high_ticket").strip() or "high_ticket"
    template = CATEGORY_TEXT_QUERY.get(key) or CATEGORY_TEXT_QUERY["high_ticket"]
    return template.format(city=c)


def _place_from_api(obj: dict[str, Any]) -> PlaceHit | None:
    pid = (obj.get("id") or obj.get("name") or "").strip()  # name is resource name sometimes
    if not pid:
        return None
    dname = obj.get("displayName") or {}
    name = (dname.get("text") if isinstance(dname, dict) else None) or ""
    name = (name or "").strip() or "Sans nom"
    addr = (obj.get("formattedAddress") or "").strip()
    web = obj.get("websiteUri")
    web = (web.strip() if isinstance(web, str) and web.strip() else None)
    r = obj.get("rating")
    rating = float(r) if isinstance(r, (int, float)) else None
    ur = obj.get("userRatingCount")
    urc = int(ur) if isinstance(ur, (int, float)) else None
    types = obj.get("types")
    tlist: list[str] = [str(x) for x in types] if isinstance(types, list) else []
    return PlaceHit(
        place_id=pid,
        name=name,
        address=addr,
        website=web,
        rating=rating,
        user_ratings_total=urc,
        types=tlist,
    )


async def fetch_places_for_zone(
    city: str,
    metier_category: str,
    *,
    max_places: int = 200,
) -> list[PlaceHit]:
    key = (settings.google_places_api_key or "").strip()
    if not key:
        raise RuntimeError("GOOGLE_PLACES_API_KEY / google_places_api_key manquante (Places API requise).")

    text_query = _text_query_for_category(city, metier_category)
    out: list[PlaceHit] = []
    page_token: str | None = None
    n_pages = 0

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=5)
    async with httpx.AsyncClient(
        http2=False,
        timeout=httpx.Timeout(60.0),
        trust_env=settings.httpx_trust_env,
        limits=limits,
    ) as client:
        while len(out) < max_places and n_pages < settings.google_places_max_pages:
            body: dict[str, Any] = {
                "textQuery": text_query,
                "languageCode": "fr",
                "maxResultCount": min(settings.google_places_max_per_request, max_places - len(out)),
            }
            if page_token:
                body["pageToken"] = page_token

            r = await client.post(
                PLACES_BASE,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": key,
                    "X-Goog-FieldMask": FIELD_MASK,
                },
            )
            r.raise_for_status()
            data = r.json()
            places = data.get("places")
            if not isinstance(places, list):
                places = []
            for p in places:
                if not isinstance(p, dict):
                    continue
                h = _place_from_api(p)
                if h:
                    out.append(h)
            # Pagination (API New)
            page_token = data.get("nextPageToken")
            if not page_token or not places:
                break
            n_pages += 1
            # L'API exige parfois un court délai avant d'utiliser nextPageToken
            if page_token:
                await asyncio.sleep(2.0)
            if len(places) < settings.google_places_max_per_request:
                if not page_token:
                    break

    # Dédup place_id
    seen: set[str] = set()
    deduped: list[PlaceHit] = []
    for h in out:
        if h.place_id in seen:
            continue
        seen.add(h.place_id)
        deduped.append(h)
    return deduped[:max_places]
