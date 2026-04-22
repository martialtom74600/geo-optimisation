"""
Déduplication de leads sur le domaine enregistré (évite de crawler/auditer deux fois la même entreprise).
"""

from __future__ import annotations

import logging

from geo_stealth_prospector.models import LeadRecord
from geo_stealth_prospector.tldx import tld

LOG = logging.getLogger(__name__)


def dedupe_leads_by_registered_domain(leads: list[LeadRecord]) -> list[LeadRecord]:
    """
    Conserve la première occurrence par « registered domain » (tldextract), ordre préservé.
    Les URL sans domaine exploitable sont conservées en secours (clé = host brut ou url).
    """
    seen: dict[str, LeadRecord] = {}
    order: list[str] = []
    for r in leads:
        ext = tld(r.url)
        key = (ext.registered_domain or ext.domain or "").lower().strip()
        if not key:
            key = f"_raw_{r.url}"
        if key not in seen:
            seen[key] = r
            order.append(key)
        else:
            LOG.debug("Doublon ignoré: %s (déjà vu via %s)", r.url, seen[key].url)
    out = [seen[k] for k in order]
    for i, r in enumerate(out, start=1):
        r.source_rank = i
    return out
