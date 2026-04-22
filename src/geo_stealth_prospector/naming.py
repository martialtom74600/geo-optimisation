"""Déduction heuristique du nom d'entreprise à partir d'une URL."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

from geo_stealth_prospector import tldx

# Hébergeurs / marques à ignorer en tant que "nom" si c'est le seul segment
_GENERIC_LABELS: frozenset[str] = frozenset(
    {
        "www",
        "site",
        "web",
        "blog",
        "shop",
        "boutique",
        "ecommerce",
        "store",
    }
)


def _strip_accents(s: str) -> str:
    nf = unicodedata.normalize("NFD", s)
    return "".join(c for c in nf if unicodedata.category(c) != "Mn")


def derive_company_name(url: str) -> str:
    """
    Produit un libellé lisible (Title Case) à partir du domaine, sans requête HTTP.
    Exemples: menuiserie-martin.fr -> Menuiserie Martin ; atelier.bois-soleil.com -> Bois Soleil
    """
    if not url or not url.strip():
        return "Inconnu"
    raw = url.strip()
    if not raw.lower().startswith(("http://", "https://")):
        raw = f"https://{raw}"
    ext = tldx.tld(raw)
    registered = (ext.domain or "").strip().lower()
    if not registered or registered in _GENERIC_LABELS:
        # fallback sur le sous-domaine le plus "parlant" (ex. client.sitebuilder.fr)
        sub = (ext.subdomain or "").lower()
        parts = [p for p in sub.split(".") if p and p not in _GENERIC_LABELS]
        if parts:
            registered = parts[-1]
    if not registered:
        host = urlparse(raw).netloc or urlparse(raw).path
        host = re.sub(r"^www\.", "", host, flags=re.I)
        registered = host.split(".")[0] if host else "Inconnu"

    registered = re.sub(r"[_]+", "-", registered)
    words = re.split(r"[-_]+", registered)
    words = [w for w in words if w and w not in _GENERIC_LABELS]
    if not words:
        return "Inconnu"
    out: list[str] = []
    for w in words:
        w = _strip_accents(w)
        if not w:
            continue
        out.append(w[0].upper() + w[1:].lower() if len(w) > 1 else w.upper())
    return " ".join(out)
