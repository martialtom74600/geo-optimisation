"""
Pipeline réutilisable (CLI, API CRM) : mode zone uniquement (ville + métiers high-ticket).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from geo_stealth_prospector.audit_groq import audit_leads_concurrent
from geo_stealth_prospector.config import Settings
from geo_stealth_prospector.crawl_proof import crawl_leads_concurrent
from geo_stealth_prospector.exceptions import JobCancelled
from geo_stealth_prospector.lead_dedupe import dedupe_leads_by_registered_domain
from geo_stealth_prospector.models import LeadRecord
from geo_stealth_prospector.professions import HIGH_TICKET_PROFESSIONS
from geo_stealth_prospector.zone_sourcing import zone_sourcing_multimetier

LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ZonePipelineConfig:
    """Paramètres pour un run « aspirateur » sur une ville."""

    city: str
    max_total: int
    max_per_metier: int
    audit_all: bool = False
    skip_crawl_audit: bool = False  # sourcing + dédup seulement


async def run_zone_pipeline(
    settings: Settings,
    config: ZonePipelineConfig,
    *,
    on_status: Callable[[str], None] | None = None,
    on_cancel: Callable[[], bool] | None = None,
) -> list[LeadRecord]:
    """
    Enchaîne : sourcing multi-métiers → dédup → plafond global → crawl → audits Groq (filtre cash machine).
    ``on_status`` reçoit des messages courts pour UI / logs (thread-safe : appeler depuis la boucle async).
    """
    city = config.city.strip()
    metiers = list(HIGH_TICKET_PROFESSIONS)
    if settings.zone_max_metiers > 0:
        metiers = metiers[: settings.zone_max_metiers]

    cap = max(1, config.max_total)
    stop_after_raw: int | None
    if settings.zone_sourcing_disable_early_stop:
        stop_after_raw = None
    else:
        # Marge sur le plafond final : inutile de parcourir 20 métiers si on a assez de matière avant dédup.
        stop_after_raw = min(500, max(64, cap * 5))

    def status(msg: str) -> None:
        if on_cancel and on_cancel():
            raise JobCancelled()
        LOG.info(msg)
        if on_status:
            on_status(msg)

    status(
        f"Sourcing : {len(metiers)} familles de métiers « high-ticket » pour « {city} » "
        f"(plafond final visé : {cap} prospect(s), jusqu’à {max(1, config.max_per_metier)} URL(s) distinctes par famille)."
    )

    leads = await zone_sourcing_multimetier(
        city,
        metiers,
        settings,
        max_per_metier=max(1, config.max_per_metier),
        progress=None,
        task_id=None,
        on_status=on_status,
        on_cancel=on_cancel,
        stop_after_raw_hits=stop_after_raw,
    )
    if not leads:
        status(
            "Aucun site retenu après le sourcing. Causes fréquentes : (1) chaque requête vers DuckDuckGo a échoué "
            "(regardez le terminal API : une ligne commence par « DuckDuckGo requête échouée » avec le détail "
            "du type d’erreur, du code HTTP et parfois un extrait de page) ; (2) proxy ou variables "
            "HTTP_PROXY cassées : essayez GEO_HTTPX_TRUST_ENV=false dans le .env à la racine du repo ; "
            "(3) moteur ou réseau qui bloque l’automatisation ; (4) ville / filtres qui ne remontent vraiment aucun site indépendant."
        )
        return []

    n_raw = len(leads)
    leads = dedupe_leads_by_registered_domain(leads)
    status(
        f"Déduplication par domaine : {n_raw} pistes brutes → {len(leads)} site(s) distinct(s) "
        f"(un domaine = une entreprise pour la suite du pipeline)."
    )

    if len(leads) > cap:
        leads = leads[:cap]
        status(
            f"Application de votre plafond : on ne garde que les {cap} premiers prospects "
            f"(ordre du sourcing conservé)."
        )

    if config.skip_crawl_audit:
        return leads

    status(
        "Crawl : téléchargement de chaque page d’accueil pour lire title, H1 et JSON-LD — "
        "c’est la base factuelle avant toute analyse IA."
    )
    await crawl_leads_concurrent(
        leads, settings, on_status=on_status, on_cancel=on_cancel
    )

    n_green = sum(1 for r in leads if r.crawl and r.crawl.has_relevant_business_schema)
    n_groq = (
        len(leads)
        if config.audit_all
        else sum(
            1
            for r in leads
            if not (r.crawl and r.crawl.has_relevant_business_schema)
        )
    )
    status(
        f"Crawl terminé : {n_green} site(s) affichent déjà un schéma « entreprise / lieu » pertinent ; "
        f"{n_groq} audit(s) IA au plus (souvent moins si vous n’avez pas coché « auditer tout le monde »)."
    )

    if not settings.has_groq():
        status(
            "Clé Groq absente (GEO_GROQ_API_KEY) : le pipeline s’arrête après le crawl — aucun appel LLM."
        )
        return leads

    status(
        "Audits Groq : analyse commerciale GEO (risque, hooks, suggestion JSON-LD) sur les cibles éligibles ; "
        "débit limité pour respecter les quotas API."
    )
    await audit_leads_concurrent(
        leads,
        settings,
        cash_machine=not config.audit_all,
        on_status=on_status,
        on_cancel=on_cancel,
    )
    status("Dernier passage : tout le pipeline « zone » est terminé pour ce run.")
    return leads
