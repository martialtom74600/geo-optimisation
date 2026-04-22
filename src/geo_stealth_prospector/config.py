"""Chargement de la configuration via variables d'environnement."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres runtime (fichier .env optionnel, préfixe GEO_)."""

    model_config = SettingsConfigDict(
        env_prefix="GEO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = Field(
        default="",
        description="Clé API Groq (requis pour les audits).",
    )
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Modèle Groq (Llama 3.3 70B ou équivalent).",
    )
    groq_max_concurrent: int = Field(
        default=1,
        ge=1,
        le=32,
        description="Nombre max d'appels Groq en parallèle (sémaphore). 1 recommandé si erreurs 429 (TPM).",
    )
    groq_inter_request_delay_s: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="Pause (s) avant chaque requête Groq (en plus de la pause post-audit).",
    )
    groq_post_success_delay_s: float = Field(
        default=2.0,
        ge=0.0,
        le=60.0,
        description="Pause (s) après chaque audit Groq réussi pour laisser respirer le quota TPM.",
    )
    crawl_max_concurrent: int = Field(
        default=5,
        ge=1,
        le=32,
        description="Nombre max de pages d'accueil en téléchargement simultané.",
    )
    crawl_timeout_s: float = Field(
        default=25.0,
        ge=3.0,
        le=120.0,
        description="Timeout HTTP pour le crawl d'une page.",
    )
    crawl_max_bytes: int = Field(
        default=2_000_000,
        ge=100_000,
        le=20_000_000,
        description="Taille max lue côté HTML (protection mémoire).",
    )
    http_timeout_s: float = Field(
        default=45.0,
        ge=5.0,
        le=120.0,
        description="Timeout httpx (s) ; côté DuckDuckGo on applique au moins 30s.",
    )
    httpx_trust_env: bool = Field(
        default=True,
        description="httpx : respecter les variables d'environnement de proxy. "
        "Mettre false (env GEO_HTTPX_TRUST_ENV=false) si toutes les requêtes DDG échouent (localhost, proxy, VPN).",
    )
    ddg_request_delay_s: float = Field(
        default=0.8,
        ge=0.0,
        le=10.0,
        description="Pause entre requêtes HTTP vers DuckDuckGo (réduit les risques de blocage).",
    )
    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        description="User-Agent type Chrome récent (DuckDuckGo HTML / stealth). Surchageable par GEO_USER_AGENT.",
    )
    ddg_referer: str = Field(
        default="https://html.duckduckgo.com/",
        description="Referer explicite pour la requête HTML DuckDuckGo.",
    )
    zone_metier_delay_min_s: float = Field(
        default=2.0,
        ge=0.0,
        le=120.0,
        description="Mode --zone : délai aléatoire min entre chaque métier (secondes).",
    )
    zone_metier_delay_max_s: float = Field(
        default=5.0,
        ge=0.0,
        le=120.0,
        description="Mode --zone : délai aléatoire max entre chaque métier (secondes).",
    )
    zone_max_metiers: int = Field(
        default=0,
        ge=0,
        le=100,
        description="0 = tous les métiers high-ticket ; n>0 = n'itérer que sur les n premiers (tests / accélération).",
    )
    zone_sourcing_disable_early_stop: bool = Field(
        default=False,
        description="Si vrai, enchaîner tous les métiers même si assez de pistes brutes (plus lent, couverture max).",
    )

    @field_validator("groq_api_key", mode="before")
    @classmethod
    def strip_key(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    def has_groq(self) -> bool:
        return bool(self.groq_api_key)
