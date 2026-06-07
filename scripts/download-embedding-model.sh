#!/usr/bin/env bash
# Pre-download the FastEmbed ONNX model configured in backend/.env (or pass a preset).
# Usage:
#   bash scripts/download-embedding-model.sh              # uses TSOC_EMBEDDING_MODEL from .env
#   bash scripts/download-embedding-model.sh bge-small    # override: small / base / large also work
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "Missing backend/.venv — run: cd backend && pip install -r requirements.txt" >&2
  exit 1
fi

cd "$ROOT/backend"
if [[ -n "${1:-}" ]]; then
  export TSOC_EMBEDDING_MODEL="$1"
fi

exec "$PY" -c "
import asyncio
from config import Settings, clear_settings_cache, get_settings
from services.soc_rag.embeddings import (
    _download_hint,
    ensure_embedding_model,
    fastembed_cache_dir,
    list_embedding_model_options,
    resolve_embedding_model,
)

clear_settings_cache()
override = __import__('os').environ.get('TSOC_EMBEDDING_MODEL', '').strip()
settings = Settings(tsoc_embedding_model=override) if override else get_settings()
resolved = resolve_embedding_model(settings.tsoc_embedding_model)
size = _download_hint(settings.tsoc_embedding_model)
print(f'Downloading FastEmbed model: {settings.tsoc_embedding_model} -> {resolved} ({size})')
print('Supported presets:', ', '.join(o['preset'] for o in list_embedding_model_options()))
asyncio.run(ensure_embedding_model(settings))
print(f'OK — cached under {fastembed_cache_dir(settings)}')
"
