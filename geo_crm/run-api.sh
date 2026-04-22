#!/usr/bin/env bash
# Lancement Uvicorn pour GEO-CRM (import geo_stealth_prospector via PYTHONPATH = racine du repo).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
PY="${REPO_ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3 || true)"
fi
if [[ -z "$PY" ]]; then
  echo "ERR: python3 introuvable (creez un venv a la racine : python3 -m venv .venv)" >&2
  exit 1
fi
cd "${REPO_ROOT}/geo_crm/backend"
exec "$PY" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
