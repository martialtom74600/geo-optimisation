"""
Audits asynchrones via l'API Groq (rapide) avec sémaphore de débit.
Le prompt s'appuie sur le crawl factuel (JSON-LD, title, H1) et exige une suggestion JSON-LD.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Callable
from typing import Any

from groq import APIError, APITimeoutError, AsyncGroq, RateLimitError

from geo_stealth_prospector.async_cancel import gather_cancel_siblings, sleep_cancellable
from geo_stealth_prospector.config import Settings
from geo_stealth_prospector.exceptions import JobCancelled
from geo_stealth_prospector.models import AuditResult, CrawlResult, LeadRecord

LOG = logging.getLogger(__name__)

# Tentatives d'un même appel chat.completions en cas de 429 (1 initial + reprises après attente).
GROQ_429_MAX_ATTEMPTS: int = 3
# Si Groq ne donne pas de délai extractible dans le 429, on attend 10s avant réessayer.
GROQ_429_DEFAULT_BACKOFF_S: float = 10.0
# Borne haute d'attente (évite les sleeps absurdes en cas de bug de parsing)
GROQ_429_MAX_BACKOFF_S: float = 120.0

_SYSTEM_PROMPT = """Tu es un consultant senior GEO (Generative Engine Optimization) en France : visibilité dans les réponses des assistants IA (ChatGPT, Gemini, Perplexity, etc.) et des résumés « zero-click », pas seulement le SEO classique.

Règles strictes :
- Tu t'appuies UNIQUEMENT sur les « preuves crawl » (title, H1, JSON-LD). N'invente pas d'autres balises.
- Si la page n'a pas pu être lue, ne dis jamais « pas de H1 / pas de JSON-LD sur le site » : l'état est INCONNU. Parle d'opacité pour les systèmes automatisés.
- Chaque champ « analyse_* » et « synthese_expert_geo » doit refléter les SPÉCIFICITÉS de ce domaine/URL, pas un discours générique.
- sortie = UN SEUL OBJET JSON. INTERDIT : markdown, blocs ```, texte avant/après. Premier caractère {, dernier }.

Clés obligatoires (toutes des chaînes sauf mention) :
"risque_marche", "faille_technique", "hook_email", "json_ld_suggestion" (chaîne d'un seul JSON LocalBusiness ou équivalent, JSON valide, \"@context\": \"https://schema.org\"),
"synthese_expert_geo", "analyse_donnees_structurees", "analyse_exploitabilite_ia", "analyse_signal_local" (4 analyses courtes, françaises, ciblées CE site),
"score_opportunite_geo" (nombre entier 0 à 100 : potentiel de mission GEO pour toi, compte tenu de l'écart constaté),
"actions_prioritaires" (tableau de 3 à 5 courtes chaînes, ordre de priorité).

Détail :
- score_opportunite_geo : 0 si déjà parfaitement optimisé et peu de marge, 100 si gros manques + beaucoup de valeur.
- actions_prioritaires : concrètes (ex. « injecter le script JSON-LD sur la home », « compléter @type + address »), pas vagues.
- json_ld_suggestion : UNE chaîne, contenu d'un seul objet JSON, indenté ou minifié."""


def _strip_markdown_fences(text: str) -> str:
    """Retire les fences ``` / ```json souvent renvoyées par les LLM en dépit des consignes."""
    s = (text or "").strip()
    if not s:
        return s
    s = re.sub(r"^```(?:json|JSON|javascript)?\s*\r?\n?", "", s, count=1)
    s = re.sub(r"\r?\n?```\s*\Z", "", s, count=1)
    return s.strip()


def _normalize_json_ld_suggestion(raw: str) -> str:
    """Reformate la suggestion en JSON indenté si parseable ; sinon renvoie le texte (après strip fences)."""
    s = _strip_markdown_fences((raw or "").strip())
    if not s:
        return ""
    try:
        obj = json.loads(s)
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, TypeError) as e:
        LOG.debug("json_ld_suggestion non JSON strict: %s", e)
        return s


def _parse_root_json_object(text: str) -> dict[str, object]:
    """Extrait l'objet JSON racine (gère texte autour, fences, JSON imbriqué dans des chaînes)."""
    s = _strip_markdown_fences(text)
    if not s:
        raise json.JSONDecodeError("Réponse vide", s, 0)
    i = s.find("{")
    if i < 0:
        raise json.JSONDecodeError("Aucun objet JSON (pas de {)", s, 0)
    decoder = json.JSONDecoder()
    data, _ = decoder.raw_decode(s, i)
    if not isinstance(data, dict):
        raise TypeError("La racine JSON doit être un objet (dict)")
    return data


def _parse_action_list(data: object) -> list[str]:
    if not isinstance(data, list):
        return []
    out: list[str] = []
    for x in data[:8]:
        s = str(x).strip() if x is not None else ""
        if s:
            out.append(s)
    return out


def _parse_score(v: object) -> int:
    if isinstance(v, bool):
        return 0
    if isinstance(v, (int, float)):
        n = int(v)
    else:
        try:
            n = int(str(v).strip())
        except (TypeError, ValueError):
            return 0
    return max(0, min(100, n))


def _parse_audit_json(text: str) -> dict[str, object]:
    data = _parse_root_json_object(text)
    out: dict[str, object] = {
        "risque_marche": str(data.get("risque_marche", "")).strip(),
        "faille_technique": str(data.get("faille_technique", "")).strip(),
        "hook_email": str(data.get("hook_email", "")).strip(),
        "json_ld_suggestion": "",
        "synthese_expert_geo": str(data.get("synthese_expert_geo", "")).strip(),
        "analyse_donnees_structurees": str(
            data.get("analyse_donnees_structurees", "")
        ).strip(),
        "analyse_exploitabilite_ia": str(
            data.get("analyse_exploitabilite_ia", "")
        ).strip(),
        "analyse_signal_local": str(data.get("analyse_signal_local", "")).strip(),
        "score_opportunite_geo": _parse_score(data.get("score_opportunite_geo", 0)),
        "actions_prioritaires": _parse_action_list(data.get("actions_prioritaires", [])),
    }
    js = data.get("json_ld_suggestion", "")
    if isinstance(js, (dict, list)):
        out["json_ld_suggestion"] = json.dumps(js, ensure_ascii=False, indent=2)
    else:
        out["json_ld_suggestion"] = str(js).strip() if js is not None else ""
    return out


def _format_crawl_bloc(lead: LeadRecord, c: CrawlResult | None) -> str:
    if c is None:
        return "Preuves crawl : (non disponibles — bug interne, signaler.)\n"
    http = c.http_status if c.http_status is not None else "—"
    lines: list[str] = [
        "Preuves crawl (page d'accueil, requête HTTP directe) :",
        f"- Téléchargement de la home réussi : {'oui' if c.page_fetched else 'non'} (HTTP {http}, URL finale : {c.final_url})",
    ]
    if c.error:
        lines.append(f"- Erreur / limite réseau : {c.error}")
    not_readable = (not c.page_fetched) or (c.http_status is not None and c.http_status >= 400)
    if not_readable:
        lines.append(
            "- ATTENTION (pour le modèle) : l'analyse du HTML n'est pas fiable ici (page non lue, "
            "refus 403/404, etc.). N'INVENTE PAS l'absence de <title>, de H1 ou de JSON-LD : "
            "l'état de ces balises est INCONNU tant que la page n'est pas lue. "
            "Décris plutôt le risque d'invisibilité / le blocage d'audit technique."
        )
    title_src = c.title or "(non mesuré ou vide sur l'échantillon lu)"
    lines.append(f"- <title> de la page (si HTML lu) : {title_src}")
    serp = (lead.title or "").strip()
    if serp:
        lines.append(f"- Titre issu du moteur de sourcing (aide contexte) : {serp}")
    h1j = " ; ".join(c.h1_texts) if c.h1_texts else "(aucun H1 sur l'échantillon HTML lu)"
    lines.append(f"- H1 (jusqu'à 5) : {h1j}")
    lines.append(
        f"- Balise(s) <script type=application/ld+json> : {'oui' if c.has_jsonld_script else 'non'}"
    )
    if c.jsonld_types_found:
        types_ = ", ".join(c.jsonld_types_found)
    else:
        types_ = "(aucun @type parseable sur l'échantillon lu)"
    lines.append(f"- @type détectés dans JSON-LD : {types_}")
    lines.append(
        f"- Schéma « entreprise / lieu » pertinent (LocalBusiness, Organization, …) : "
        f"{'oui' if c.has_relevant_business_schema else 'non'}"
    )
    return "\n".join(lines) + "\n"


def _retry_delay_s_from_429(err: RateLimitError) -> float:
    """
    Délai suggéré pour un 429 : header Retry-After, texte 'try again in X.XXXs', sinon défaut.
    """
    # Header HTTP (secondes, ou date — on ne gère ici que l'entier secondes)
    try:
        ra = err.response.headers.get("Retry-After")
        if ra and ra.strip().isdigit():
            s = float(ra.strip())
            if s > 0:
                return min(s, GROQ_429_MAX_BACKOFF_S)
    except (ValueError, TypeError, AttributeError):
        pass
    for text in (getattr(err, "message", None) or "", str(err)):
        m = re.search(r"try again in\s*([\d.]+)\s*s", text, re.IGNORECASE)
        if m:
            s = float(m.group(1))
            if s > 0:
                return min(max(s, 0.5), GROQ_429_MAX_BACKOFF_S)
    if isinstance(err.body, dict):
        em = _deep_find_try_again_in_s(err.body)
        if em is not None and em > 0:
            return min(max(em, 0.5), GROQ_429_MAX_BACKOFF_S)
    return GROQ_429_DEFAULT_BACKOFF_S


def _deep_find_try_again_in_s(obj: Any, depth: int = 0) -> float | None:
    if depth > 4:
        return None
    if isinstance(obj, dict):
        m = obj.get("message")
        if isinstance(m, str):
            mm = re.search(r"try again in\s*([\d.]+)\s*s", m, re.IGNORECASE)
            if mm:
                return float(mm.group(1))
        e = obj.get("error")
        if e is not None:
            v = _deep_find_try_again_in_s(e, depth + 1)
            if v is not None:
                return v
    return None


async def _groq_chat_completion_create(
    client: AsyncGroq,
    settings: Settings,
    *,
    messages: list[dict[str, str]],
    on_cancel: Callable[[], bool] | None = None,
) -> Any:
    """
    Un appel ``chat.completions.create`` avec reprises sur 429 (TPM / rate).
    Jusqu'à ``GROQ_429_MAX_ATTEMPTS`` essais, puis propage l'exception.
    """
    last: RateLimitError | None = None
    for attempt in range(1, GROQ_429_MAX_ATTEMPTS + 1):
        try:
            return await client.chat.completions.create(
                model=settings.groq_model,
                temperature=0.28,
                max_tokens=4500,
                messages=messages,
            )
        except RateLimitError as e:
            last = e
            if attempt >= GROQ_429_MAX_ATTEMPTS:
                break
            wait = _retry_delay_s_from_429(e)
            LOG.warning(
                "Groq 429 (tentative %s/%s), attente %.2fs avant nouvel essai — %s",
                attempt,
                GROQ_429_MAX_ATTEMPTS,
                wait,
                getattr(e, "message", e) or e,
            )
            await sleep_cancellable(wait, on_cancel)
    assert last is not None
    raise last


async def run_audit(
    lead: LeadRecord,
    client: AsyncGroq,
    settings: Settings,
    *,
    on_cancel: Callable[[], bool] | None = None,
) -> AuditResult:
    """Un appel API Groq pour un seul lead (crawl requis en amont, sauf état dégradé)."""
    crawl: CrawlResult = lead.crawl or CrawlResult(error="Crawl manquant (interne)")

    user = (
        f"Entreprise (heuristique domaine) : {lead.company_name}\n"
        f"URL initiale (sourcing) : {lead.url}\n"
        f"Métier cible (prospecteur) : {lead.metier}\n"
        f"Ville (prospecteur) : {lead.city}\n\n"
        f"{_format_crawl_bloc(lead, crawl)}\n"
        "Tâches (tout le JSON) :\n"
        "1) risque_marche, faille_technique, hook_email : courts, français, ancrés dans les preuves.\n"
        "2) json_ld_suggestion : UNE chaîne = un seul JSON LocalBusiness (ou cohérent) prêt à coller (placeholders autorisés).\n"
        "3) synthese_expert_geo : synthèse d'opportunité commerciale GEO pour CE site.\n"
        "4) analyse_donnees_structurees : JSON-LD / schema.org, ce que tu vois sur CE domaine, ce qu'il manque techniquement.\n"
        "5) analyse_exploitabilite_ia : comment un LLM / assistant consommerait (ou non) la home pour recommander l'artisan — "
        "cite les manques (pas de @type, pas d'entité, etc.) si les preuves le permettent.\n"
        "6) analyse_signal_local : cohérence local / entité (ville, activité) pour les réponses « près de moi » / cartes sémantiques.\n"
        "7) score_opportunite_geo : entier 0–100 (marge de vente pour un prestataire GEO).\n"
        "8) actions_prioritaires : tableau 3–5 actions ordonnées, spécifiques à ce site.\n"
    )
    comp = await _groq_chat_completion_create(
        client,
        settings,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        on_cancel=on_cancel,
    )
    raw = (comp.choices[0].message.content or "").strip()
    try:
        d = _parse_audit_json(raw)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        LOG.warning("JSON audit illisible: %s — %s", e, raw[:200])
        raise
    if not d.get("risque_marche") and not d.get("faille_technique"):
        raise ValueError("Réponse modèle vide")
    sugg = _normalize_json_ld_suggestion(str(d.get("json_ld_suggestion", "")))
    actions = d.get("actions_prioritaires", [])
    if not isinstance(actions, list):
        actions = []
    score = d.get("score_opportunite_geo", 0)
    if not isinstance(score, int):
        score = _parse_score(score)
    return AuditResult(
        risque_marche=str(d.get("risque_marche", "")),
        faille_technique=str(d.get("faille_technique", "")),
        hook_email=str(d.get("hook_email", "")),
        json_ld_suggestion=sugg,
        synthese_expert_geo=str(d.get("synthese_expert_geo", "")),
        analyse_donnees_structurees=str(d.get("analyse_donnees_structurees", "")),
        analyse_exploitabilite_ia=str(d.get("analyse_exploitabilite_ia", "")),
        analyse_signal_local=str(d.get("analyse_signal_local", "")),
        score_opportunite_geo=score,
        actions_prioritaires=_parse_action_list(actions),
    )


def _eligible_for_groq(lead: LeadRecord, cash_machine: bool) -> bool:
    """Faux si filtre « cash machine » : schéma business déjà présent sur la home (pas d’appel payant)."""
    if not cash_machine:
        return True
    c = lead.crawl
    if c is not None and c.has_relevant_business_schema:
        return False
    return True


async def audit_leads_concurrent(
    leads: list[LeadRecord],
    settings: Settings,
    *,
    cash_machine: bool = True,
    on_status: Callable[[str], None] | None = None,
    on_cancel: Callable[[], bool] | None = None,
) -> list[LeadRecord]:
    """
    Audite les leads en parallèle (sémaphore). Par défaut (``cash_machine``),
    n’appelle pas Groq si le crawl indique un schéma business pertinent (pastille verte).
    """
    if not settings.has_groq():
        for lead in leads:
            lead.error = lead.error or "GEO_GROQ_API_KEY manquant — auditer ignoré."
        return leads

    targets: list[LeadRecord] = []
    for lead in leads:
        if not _eligible_for_groq(lead, cash_machine):
            lead.skip_ia_reason = "schema_ok"
            LOG.debug("Optimisé (JSON-LD business OK), skip Groq : %s", lead.url)
            continue
        targets.append(lead)

    if not targets:
        return leads

    n_t = len(targets)
    if on_status:
        on_status(
            f"Audits Groq : {n_t} appel(s) LLM prévu(s) (débit limité — peut prendre plusieurs minutes)…"
        )

    # Goulot serré : 1 (ou 2) audits Groq « en vol » en même temps, pour respecter le TPM.
    sem = asyncio.Semaphore(max(1, settings.groq_max_concurrent))
    client = AsyncGroq(api_key=settings.groq_api_key)
    delay = settings.groq_inter_request_delay_s
    post_ok = float(settings.groq_post_success_delay_s)
    done = 0
    lock = asyncio.Lock()
    step = max(1, n_t // 10) if n_t > 10 else 1

    async def one(lead: LeadRecord) -> None:
        nonlocal done
        if on_cancel and on_cancel():
            raise JobCancelled()
        async with sem:
            if on_cancel and on_cancel():
                raise JobCancelled()
            if delay > 0:
                await sleep_cancellable(delay, on_cancel)
            if on_cancel and on_cancel():
                raise JobCancelled()
            try:
                lead.audit = await run_audit(lead, client, settings, on_cancel=on_cancel)
                if post_ok > 0:
                    # Laisse le quota reprendre de la marge avant le prochain audit.
                    await sleep_cancellable(post_ok, on_cancel)
            except JobCancelled:
                raise
            except (
                APIError,
                APITimeoutError,
                json.JSONDecodeError,
                ValueError,
                TypeError,
                OSError,
            ) as e:
                LOG.warning("Échec audit pour %s: %s", lead.url, e)
                lead.error = (str(e) or type(e).__name__) if e else "Erreur audit"
            except Exception as e:  # noqa: BLE001 — ne jamais faire tomber le batch
                LOG.exception("Erreur inattendue audit %s", lead.url)
                lead.error = str(e) if str(e) else type(e).__name__
        if on_status:
            async with lock:
                done += 1
                d = done
            if d == n_t or d % step == 0 or d <= 2:
                pct = round(100 * d / n_t)
                on_status(f"Audits Groq : {d}/{n_t} ({pct} %) — risque / hook / JSON-LD")

    await gather_cancel_siblings([one(lead) for lead in targets])
    return leads
