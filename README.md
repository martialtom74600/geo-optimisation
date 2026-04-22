# GEO Stealth Prospector

Application CLI (Python) pour **sourcer** des sites d’artisans indépendants (recherche HTML DuckDuckGo, filtres annuaires), **crawler la page d’accueil** (preuves JSON-LD, `<title>`, H1), puis **générer** des **audits commerciaux factuels** et un **snippet JSON-LD `LocalBusiness` de secours** via l’API **Groq** (réponses concurrentes, rate limiting par sémaphore).

## Prérequis

- Python 3.11 ou supérieur
- Un compte Groq et une clé API (pour la phase d’audit IA)

## Installation

```bash
cd /chemin/vers/GEO
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e "."
```

Variables d’environnement (ou fichier `.env` à la racine du projet) :

| Variable | Description |
|----------|-------------|
| `GEO_GROQ_API_KEY` | Clé API Groq (requis sauf mode `--no-audit`) |
| `GEO_GROQ_MODEL` | Modèle (défaut : `llama-3.3-70b-versatile`) |
| `GEO_GROQ_MAX_CONCURRENT` | Parallélisme max des appels Groq (défaut : **2** ; baisser à 1 si 429) |
| `GEO_GROQ_INTER_REQUEST_DELAY_S` | Pause avant chaque requête Groq en s (défaut : **0,2** ; limite les rafales) |
| `GEO_CRAWL_MAX_CONCURRENT` | Parallélisme max des téléchargements de home (défaut : 5) |
| `GEO_CRAWL_TIMEOUT_S` | Timeout HTTP par page crawl (défaut : 25) |
| `GEO_CRAWL_MAX_BYTES` | Taille max lue par page (défaut : 2 000 000) |
| `GEO_DDG_REQUEST_DELAY_S` | Pause entre requêtes DuckDuckGo (défaut : 0.8) |
| `GEO_ZONE_METIER_DELAY_MIN_S` / `MAX_S` | Mode `--zone` : pause aléatoire **entre** chaque métier (défaut : 2 — 5 s) |

Fichier `.env` d’exemple (copiez en `.env` et remplissez) :

```env
GEO_GROQ_API_KEY=gsk_...
GEO_GROQ_MODEL=llama-3.3-70b-versatile
GEO_GROQ_MAX_CONCURRENT=2
GEO_GROQ_INTER_REQUEST_DELAY_S=0.2
```

## Lancement

```bash
source .venv/bin/activate
export GEO_GROQ_API_KEY=gsk_...   # si pas de .env

geo-stealth "Menuisier" "Annecy" -n 10 -o resultats.json
```

**Mode « aspirateur / zone »** (plein de métiers sur une même ville) :

```bash
geo-stealth --zone Annecy -n 40 --max-per-metier 8 -o zone_annecy.json
# Un seul métier dans la zone :
geo-stealth "Architecte" --zone Annecy -n 15
```

En mode `--zone` sans métier, la liste interne `HIGH_TICKET_PROFESSIONS` (~20 secteurs) est enchaînée avec un **délai aléatoire** entre chaque requête DuckDuckGo. Les domaines sont **dédoublonnés** globalement, puis seuls les leads **sans** schéma business pertinent reçoivent un appel Groq (sauf `--audit-all`).

Options utiles :

- `-n, --max` : en mode ciblé, plafond par recherche ; en `--zone`, plafond **global** après déduplication
- `--max-per-metier` : mode `--zone` uniquement, plafond par métier côté moteur
- `--zone` / `-z` : ville cible, liste de métiers haut de gamme par défaut
- `--audit-all` : forcer Groq sur **tous** les leads (ignore le filtre pastille / coût)
- `--no-audit` : sourcing seul (sans clé Groq)
- `--export, -o` : export `.json` ou `.csv`
- `-v` : logs verbeux

Équivalent module :

```bash
python -m geo_stealth_prospector "Menuisier" "Annecy" -n 8 -o leads.csv
```

## Architecture (résumé)

- `duck_search` : `POST` sur `https://html.duckduckgo.com/html/`, parsing des liens `result__a` / résolution `uddg`
- `crawl_proof` : téléchargement streamé de la home, BeautifulSoup, `<script type="application/ld+json">`, `H1`, `<title>`
- `filters` : blocklist d’annuaires et d’hôtes (réseaux sociaux, places, avis, etc.)
- `naming` : nom d’affiche heuristique depuis le domaine (tldextract)
- `professions` : `HIGH_TICKET_PROFESSIONS` (mode `--zone`)
- `zone_sourcing` : boucle par métier + jitter 2 — 5 s
- `lead_dedupe` : unicité sur le **domaine** enregistré (tldextract)
- `audit_groq` : `AsyncGroq` + filtre « cash machine » (skip si JSON-LD business OK)
- `cli` : Typer + barres de progression / panneaux Rich + `rich.Syntax` pour le snippet

Voir la section **Revue de l’architecte** dans la documentation du dépôt ou la réponse d’accompagnement de l’agent pour les limites et pistes d’industrialisation.
