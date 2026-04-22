#!/usr/bin/env bash
# Lance API + Vite en un seul terminal (equivalent: cd frontend && npm run dev:all).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE/frontend"
exec npm run dev:all
