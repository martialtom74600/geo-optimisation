"""
Familles de métiers pour le mode « zone » : une catégorie = plusieurs intitulés
envoyés au moteur (DuckDuckGo) pour couvrir le secteur dans la ville cible.
"""

from __future__ import annotations

from geo_stealth_prospector.professions import HIGH_TICKET_PROFESSIONS

# id stable -> (libellé UI, requêtes moteur par « famille »)
PROFESSION_CATEGORY_DEFINITIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "high_ticket": (
        "Artisans & pros high-ticket (défaut historique)",
        HIGH_TICKET_PROFESSIONS,
    ),
    "restauration": (
        "Restauration, bars & cafés",
        (
            "Restaurant",
            "Brasserie",
            "Bar restaurant",
            "Café",
            "Pizzeria",
            "Crêperie",
            "Boulangerie",
            "Traiteur",
            "Food truck",
            "Glacier",
        ),
    ),
    "hebergement_tourisme": (
        "Hôtellerie & hébergement",
        (
            "Hôtel",
            "Chambre d'hôtes",
            "Gîte",
            "Auberge",
            "Résidence hôtelière",
            "Village vacances",
            "Camping",
        ),
    ),
    "beaute_coiffure": (
        "Beauté, coiffure & bien-être",
        (
            "Coiffeur",
            "Salon de coiffure",
            "Barbier",
            "Institut de beauté",
            "Onglerie",
            "Extension de cils",
            "Spa",
            "Massage",
            "Centre esthétique",
        ),
    ),
    "sante_medical": (
        "Santé & paramédical",
        (
            "Médecin généraliste",
            "Dentiste",
            "Orthodontiste",
            "Kinésithérapeute",
            "Ostéopathe",
            "Pharmacie",
            "Laboratoire d'analyse médicale",
            "Podologue",
            "Vétérinaire",
            "Pédicure",
        ),
    ),
    "sport_fitness": (
        "Sport & fitness",
        (
            "Salle de sport",
            "Salle de musculation",
            "Crossfit",
            "Club de sport",
            "Coach sportif",
            "Cours de yoga",
            "Piscine",
        ),
    ),
    "auto_moto": (
        "Auto, moto & mobilité",
        (
            "Garage automobile",
            "Carrossier",
            "Pneus",
            "Mécanique auto",
            "Concession automobile",
            "Moto",
            "Lavage auto",
        ),
    ),
    "immo_juridique": (
        "Immobilier & juridique",
        (
            "Agence immobilière",
            "Notaire",
            "Syndic de copropriété",
            "Diagnostic immobilier",
            "Agent immobilier",
        ),
    ),
    "btp_renovation": (
        "BTP, réno & second œuvre",
        (
            "Plombier",
            "Électricien",
            "Maçon",
            "Menuisier",
            "Couvreur",
            "Ravalement façade",
            "Chauffagiste",
            "Carreleur",
            "Peinture bâtiment",
        ),
    ),
    "commerce_proximite": (
        "Commerce de proximité & alimentaire",
        (
            "Épicerie",
            "Primeur",
            "Caviste",
            "Fleuriste",
            "Boucherie",
            "Fromagerie",
            "Magasin bio",
        ),
    ),
    "services_b2b": (
        "Services aux entreprises",
        (
            "Expert-comptable",
            "Avocat d'affaires",
            "Conseil en gestion",
            "Agence web",
            "Agence communication",
            "Nettoyage bureaux",
            "Domiciliation entreprise",
        ),
    ),
    "education_formation": (
        "Éducation & formation",
        (
            "Auto-école",
            "Organisme de formation",
            "Cours de langue",
            "Soutien scolaire",
        ),
    ),
    "artisanat_arts": (
        "Artisanat, déco & création",
        (
            "Ébéniste",
            "Marbrerie",
            "Verrerie",
            "Céramique",
            "Atelier serrurier",
            "Tapissier",
            "Photographe",
        ),
    ),
}


def list_category_choices() -> list[tuple[str, str]]:
    """Liste (id, libellé) pour API / UI — ordre d’insertion du dict (Py3.7+)."""
    return [(cid, label) for cid, (label, _) in PROFESSION_CATEGORY_DEFINITIONS.items()]


def is_valid_category_id(category_id: str) -> bool:
    return bool(category_id) and category_id in PROFESSION_CATEGORY_DEFINITIONS


def resolve_zone_metiers(category_id: str | None) -> tuple[str, list[str]]:
    """
    Retourne (libellé catégorie, liste des intitulés moteur).
    Id inconnu -> ValueError.
    """
    key = (category_id or "high_ticket").strip() or "high_ticket"
    if not is_valid_category_id(key):
        valid = ", ".join(PROFESSION_CATEGORY_DEFINITIONS)
        raise ValueError(
            f"Catégorie « {key} » inconnue. Utilisez un de : {valid}"
        )
    label, metiers = PROFESSION_CATEGORY_DEFINITIONS[key]
    return label, list(metiers)
