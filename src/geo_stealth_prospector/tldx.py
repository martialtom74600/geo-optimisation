"""tldextract avec répertoire de cache dans le projet (évite avertissements / sandbox)."""

from __future__ import annotations

from pathlib import Path

import tldextract

_root = Path(__file__).resolve().parents[2]
_cache_dir = _root / ".tldcache"
_cache_dir.mkdir(parents=True, exist_ok=True)

tld: tldextract.TLDExtract = tldextract.TLDExtract(cache_dir=str(_cache_dir))
