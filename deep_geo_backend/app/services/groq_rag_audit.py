"""
Audit IA « RAG Readiness » — Groq, sortie JSON stricte (5 piliers).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from groq import AsyncGroq

from app.config import settings
from app.schemas import RAGAuditResult

LOG = logging.getLogger(__name__)

_SYSTEM = """Tu es un auditeur senior GEO (Generative Engine Optimization) et « RAG readiness » pour le marché français.
Tu reçois le contenu TEXTUEL (Markdown) extrait d’un site professionnel — ce que des systèmes comme Perplexity ou les moteurs avec RAG pourraient indexer.

Règles :
- Base-toi UNIQUEMENT sur le texte fourni. Si le texte est vide ou trop court, indique-le et mets des scores bas.
- Réponds par UN SEUL objet JSON. Aucun markdown, aucun texte hors JSON. Pas de ```.

Schéma JSON obligatoire (toutes les clés) :
{
  "entity_clarity_score": <entier 0-100>,
  "rag_structure_score": <entier 0-100>,
  "eat_signals": <booléen>,
  "geo_risk_analysis": "<paragraphe en français, ton cash, pourquoi les IA vont favoriser un concurrent plus clair>",
  "high_ticket_hook": "<une phrase d’accroche email ciblant la faille sémantique la plus lourde>"
}

Définitions :
- entity_clarity_score : le modèle comprend-il QUI est l’entreprise, POUR QUI, OÙ, et QUOI (offre) sans ambiguïté ?
- rag_structure_score : le texte est-il structuré pour être cité (titres, listes, FAQ, preuves) vs blabla indigeste ?
- eat_signals : présence de signaux d’expertise crédible dans le texte (labels, diplômes, méthode, preuves, chiffres, références) ?

Les scores doivent refléter le site réel, pas un discours générique."""


def _strip_fences(s: str) -> str:
    t = (s or "").strip()
    t = re.sub(r"^```(?:json|JSON)?\s*\n?", "", t, count=1)
    t = re.sub(r"\n?```\s*\Z", "", t, count=1)
    return t.strip()


def _parse_json_object(s: str) -> dict[str, Any]:
    t = _strip_fences(s)
    i = t.find("{")
    if i < 0:
        raise json.JSONDecodeError("no {", t, 0)
    return json.JSONDecoder().raw_decode(t, i)[0]


async def run_rag_audit(
    company_name: str,
    address: str,
    website: str | None,
    markdown_bundle: str,
) -> RAGAuditResult:
    if not (settings.groq_api_key or "").strip():
        raise RuntimeError("Clé Groq manquante (GEO_GROQ_API_KEY)")

    body = (markdown_bundle or "").strip()
    if len(body) > settings.groq_max_input_chars:
        body = body[: settings.groq_max_input_chars] + "\n\n[… contenu tronqué pour la limite de contexte …]"

    user = f"""Contexte entreprise (Places / crawl) :
- Nom affiché : {company_name}
- Adresse : {address}
- Site : {website or "non renseigné"}

Contenu site (Markdown agrégé) :
---
{body or "(aucun contenu textuel utile n’a pu être extrait — signale un risque d’invisibilité RAG/GEO max)"}
---
"""

    client = AsyncGroq(api_key=settings.groq_api_key)
    comp = await client.chat.completions.create(
        model=settings.groq_model,
        temperature=0.2,
        max_tokens=3500,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user},
        ],
    )
    raw = (comp.choices[0].message.content or "").strip()
    data = _parse_json_object(raw)
    if not isinstance(data, dict):
        raise ValueError("Réponse LLM: racine n'est pas un objet")
    return RAGAuditResult.model_validate(
        {
            "entity_clarity_score": data.get("entity_clarity_score", 0),
            "rag_structure_score": data.get("rag_structure_score", 0),
            "eat_signals": bool(data.get("eat_signals", False)),
            "geo_risk_analysis": str(data.get("geo_risk_analysis", "")).strip() or "Analyse manquante.",
            "high_ticket_hook": str(data.get("high_ticket_hook", "")).strip() or "À qualifier après relecture du site.",
        }
    )
