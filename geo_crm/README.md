# GEO-CRM

Application web locale : **sourcing par zone**, filtrage **JSON-LD LocalBusiness**, génération **Groq** (hook, risque, snippet), et **CRM** (statuts, copie rapide).

## Prérequis

- Python **3.11+** (un venv est recommandé)
- **Node.js 18+** avec `npm` sur le `PATH` (obligatoire pour le frontend). Sur macOS sans Node : [nodejs.org](https://nodejs.org/) ou `brew install node` — vérifier avec `which node` et `which npm`
- À la racine du dépôt `GEO` : `pip install -e .` (package `geo-stealth-prospector`, requis par l’API)

## Installation

Activez d’abord votre environnement (ex. `source .venv/bin/activate` depuis `GEO`).

```bash
cd ~/Documents/Codage/GEO   # ou : le chemin réel de votre clone

# Moteur de pipeline (sourcing, crawl, Groq)
python -m pip install -e .

# API FastAPI
python -m pip install -e geo_crm/backend

# Frontend (nécessite Node/npm installé sur la machine, pas seulement le venv Python)
cd geo_crm/frontend && npm install && cd ../..
```

> Ne copiez pas bêtement chaque ligne dans le terminal : les lignes qui commencent par `#` sont des commentaires. Si vous collez un bloc d’un seul coup, zsh ne doit pas exécuter le caractère `#` seul comme commande. En cas de doute, lancez **une seule commande** à la fois.

Variables d’environnement (racine `GEO/.env` ou `geo_crm/backend/.env`) :

- `GEO_GROQ_API_KEY` — clé Groq (obligatoire pour les audits IA sur les cibles prioritaires)
- `GEO_CRM_CORS_ORIGINS` — optionnel, liste séparée par des virgules (défaut : `http://127.0.0.1:8000`, etc.)

## Lancer (recommandé : API + site en **une** commande)

Remplacez le chemin par **celui de votre copie** du dépôt (ex. macOS : `~/Documents/Codage/GEO`). Exemple concret :

```bash
cd ~/Documents/Codage/GEO/geo_crm/frontend
npm run dev:all
```

(« `/chemin/vers/GEO` » dans d’anciennes docs était un **placeholder** — ne pas le coller tel quel.)

Ou, depuis le dossier `geo_crm` de ce dépôt :

```bash
cd ~/Documents/Codage/GEO/geo_crm
bash dev.sh
```

- **App (un seul onglet)** : [http://127.0.0.1:8000](http://127.0.0.1:8000) — l’UI Vite et les requêtes `/api` passent par cette URL (l’API FastAPI tourne en coulisses sur le port **8001**).  
- **Arrêt** : un seul **Ctrl+C** termine l’API et Vite (grâce à `concurrently -k`).

`run-api.sh` active automatiquement `PYTHONPATH` sur la racine du repo et utilise `.venv/bin/python` s’il existe.

## Lancer l’API seule (optionnel)

```bash
cd ~/Documents/Codage/GEO
bash geo_crm/run-api.sh
```

Ou manuellement avec le venv activé : `cd geo_crm/backend` puis `PYTHONPATH=$(cd ../.. && pwd) python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001` (l’UI reste sur le port 8000 via Vite, pas la peine d’ouvrir le 8001 dans le navigateur)

## Dépannage

| Message | Action |
|--------|--------|
| `command not found: uvicorn` | Préférer `python -m uvicorn ...`. Vérifier : `python -m pip show uvicorn` (sinon : `python -m pip install -e geo_crm/backend`). |
| `command not found: npm` | **Node n’est pas installé** (ou pas dans le `PATH`). Installez Node.js, rouvrez le terminal, puis `which npm`. Le venv Python ne fournit jamais `npm`. |
| `command not found: #` | Souvent un mauvais copier-coller. Exécuter les commandes **sans** la ligne de commentaire, une par une. |

**Frontend seul** (si l’API tourne déjà ailleurs) : `cd geo_crm/frontend && npm run dev`

- Santé API (via le proxy, même URL que l’app) : `GET http://127.0.0.1:8000/api/health`
- Base SQLite par défaut : `geo_crm/backend/data/geo_crm.db`

## Build production (frontend)

```bash
cd geo_crm/frontend && npm run build
```

Les fichiers statiques sont dans `geo_crm/frontend/dist`. Pour les servir avec l’API, montez `StaticFiles` sur FastAPI ou utilisez un reverse proxy (hors scope du setup local minimal).
