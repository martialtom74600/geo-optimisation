"""Filtres d'annuaires et d'agrégateurs pour ne conserver que des sites d'artisans indépendants."""

from __future__ import annotations

import re
from urllib.parse import urlparse

# Domaines (suffixes) à exclure : annuaires, réseaux sociaux, marketplaces, cartes, etc.
# Normalisés en minuscules, sans point initial (comparaison sur registered domain).
BLOCKED_DOMAIN_SUFFIXES: frozenset[str] = frozenset(
    {
        # Annuaires FR / EU courants
        "pagesjaunes.fr",
        "societe.com",
        "verif.com",
        "web.local.fr",
        "mappy.com",
        "pappers.fr",
        "trouveartisan.fr",
        "ici-artisan.fr",
        "ville-data.com",
        "rdvartisans.fr",
        "lemenuisier.fr",
        "menuisier.info",
        "lafourchette.com",
        "tupalo.co",
        "cylex.france.fr",
        "cylex.fr",
        "kompass.com",
        "europages.fr",
        "wikipedia.org",
        "annuaire-horaire.fr",
        "118000.fr",
        "hoodspot.com",
        # Généralistes / avis
        "google.com",
        "google.fr",
        "gstatic.com",
        "bing.com",
        "yahoo.com",
        "duckduckgo.com",
        "yelp.com",
        "yelp.fr",
        "yelp.ch",
        "tripadvisor.fr",
        "tripadvisor.com",
        "trustpilot.com",
        "foursquare.com",
        "opendi.fr",
        "hotfrog.fr",
        "starofservice.com",
        "bark.com",
        "waze.com",
        "apple.com",
        "bingplaces.com",
        "houzz.com",
        "houzz.fr",
        # Social / UGC
        "facebook.com",
        "fb.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "tiktok.com",
        "youtube.com",
        "pinterest.com",
        "threads.net",
        "snapchat.com",
        # Petites annonces & leads payants
        "leboncoin.fr",
        "indeed.com",
        "apec.fr",
        "welcometothejungle.com",
        "hellowork.com",
        "meteojob.com",
        "viadeo.com",
        "wikipedia.org",
    }
)

# Sous-chaînes dans l'URL complète (host + path) — agresse les annuaires thématiques
BLOCKED_URL_SUBSTRINGS: tuple[str, ...] = (
    "/annuaire/",
    "trouveartisan",
    "pappers",
    "ville-data",
    "annuaire-",
    "starofservice",
    "cylex",
    "europages",
    "rdvartisans",
    "entreprise_localisation",
    "menuisier.info",
)

# Sous-chaînes dans le host (pour attraper fb.me, bing maps, etc.)
BLOCKED_HOST_SUBSTRINGS: tuple[str, ...] = (
    "pagesjaunes",
    "yelp",
    "facebook",
    "google.",
    "goo.gl",
    "wikipedia",
    "linkedin",
    "instagram",
    "twitter",
    "tripadvisor",
    "mappy",
    "houzz",
    "waze",
    "apple",
    "bing",
    "yahoo",
    "duckduckgo",
    "lacentrale",
    "seloger",
    "jalis",
    "over-blog",
    "canalblog",
    "pappers",
    "trouveartisan",
    "ville-data",
    "leboncoin",
    "cylex",
    "menuisier.info",
)


def _normalize_host(url: str) -> str:
    p = urlparse(url if "://" in url else f"https://{url}")
    host = (p.netloc or p.path or "").lower().split("@")[-1]
    if host.startswith("www."):
        host = host[4:]
    return host.rstrip(".")


def is_blocked_domain(host: str) -> bool:
    """
    Indique si le host (ou sa chaîne) correspond à un annuaire connu.
    Vérifie d'abord les sous-chaînes, puis le suffixe enregistré.
    """
    h = host.lower()
    for sub in BLOCKED_HOST_SUBSTRINGS:
        if sub in h:
            return True
    parts = h.split(".")
    if len(parts) >= 2:
        # comparer domaine registré type foo.bar.fr
        for n in (2, 3):
            if len(parts) >= n:
                candidate = ".".join(parts[-n:])
                if candidate in BLOCKED_DOMAIN_SUFFIXES:
                    return True
    return h in BLOCKED_DOMAIN_SUFFIXES


_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def is_probably_independent_site(url: str, registered_domain: str | None) -> bool:
    """
    Filtre fin : exclut IP nues, hébergeurs gratuits évidents, annuaires.
    `registered_domain` provient de tldextract.
    """
    u = (url or "").lower()
    for sub in BLOCKED_URL_SUBSTRINGS:
        if sub in u:
            return False
    host = _normalize_host(url)
    if not host or _IP_RE.match(host):
        return False
    if is_blocked_domain(host):
        return False
    if registered_domain and is_blocked_domain(registered_domain):
        return False
    return True
