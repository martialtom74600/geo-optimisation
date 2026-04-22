# Deep GEO — backend V2 (enterprise)

- **API** : FastAPI + SQLAlchemy 2 (async) + **PostgreSQL** (`asyncpg`)
- **Tâches** : **Celery** + **Redis** (scraping/audits hors requête HTTP)
- **Sourcing** : **Google Places API (New)** — Text Search paginé (plus de DuckDuckGo)
- **Crawl** : `httpx` + **trafilatura** (Markdown) ; **Firecrawl** optionnel si `FIRECRAWL_API_KEY`
- **Audit** : **Groq** — 5 piliers RAG readiness (`entity_clarity_score`, `rag_structure_score`, `eat_signals`, `geo_risk_analysis`, `high_ticket_hook`)

## Prérequis

1. `docker compose up -d` à la **racine du dépôt** (PostgreSQL + Redis).
2. Clés : `GOOGLE_PLACES_API_KEY`, `GEO_GROQ_API_KEY` (déjà `GEO_*` dans le `.env` racine).
3. Python 3.11+, venv.

## Installation

```bash
cd deep_geo_backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e "."
```

Variables (fichier `.env` à la racine du monorepo ou ici) :

```
DATABASE_URL=postgresql+asyncpg://deepgeo:deepgeo@127.0.0.1:5432/deepgeo
DATABASE_URL_SYNC=postgresql+psycopg2://deepgeo:deepgeo@127.0.0.1:5432/deepgeo
REDIS_URL=redis://127.0.0.1:6379/0
GOOGLE_PLACES_API_KEY=...
GEO_GROQ_API_KEY=...
# optionnel
FIRECRAWL_API_KEY=...
```

## Lancer (une seule commande, recommandé)

À la **racine du dépôt** : **Docker** + **API** + **Celery** dans un seul terminal (logs `web` / `worker` via [honcho](https://github.com/nickstenning/honcho)) :

```powershell
.\start-deep-geo.ps1
```

Prérequis : venv du repo avec `pip install -e ./deep_geo_backend` (inclut **honcho**), Docker Desktop, `.env` correct (`DATABASE_URL`, `REDIS_URL`, clés). **Arrêt** : `Ctrl+C`.

- **Interface web d’essai (formulaire : ville, métier, suivi de job)** : http://127.0.0.1:8010/essai  
- Docs (Swagger) : http://127.0.0.1:8010/docs  
- Santé : `GET /api/v2/health`  
- Job : `POST /api/v2/jobs/zone` (`city`, `metier_category`, `max_total`, …)

### Manuel (2 terminaux)

```bash
cd deep_geo_backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
# autre terminal (sur **Windows** le pool par défaut échoue : ajouter --pool=solo) :
python -m celery -A app.worker.celery_app worker --loglevel=info --pool=solo --concurrency=1
```

L’**ancien** CRM (`geo_crm/frontend` sur le port 8000) n’est **pas** branché sur cette API : le frontend devra consommer `/api/v2/*` quand tu l’adapteras.

## Tables

`deep_geo_jobs`, `deep_geo_leads` — créées au démarrage API (`create_all`). Pour la prod, prévoir **Alembic** et migrations versionnées.
