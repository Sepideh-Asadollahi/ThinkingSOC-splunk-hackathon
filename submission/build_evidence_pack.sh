#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${TSOC_BASE_URL:-http://127.0.0.1:9876}"
TIMEOUT="${TSOC_EVIDENCE_TIMEOUT:-120}"
HEAVY_TIMEOUT="${TSOC_EVIDENCE_HEAVY_TIMEOUT:-1800}"
RETRIES="${TSOC_EVIDENCE_RETRIES:-0}"
HEAVY_RETRIES="${TSOC_EVIDENCE_HEAVY_RETRIES:-0}"
VERBOSE="${TSOC_EVIDENCE_VERBOSE:-1}"

export PYTHONPATH="backend:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1

args=(
  submission/generate_evidence_pack.py
  --base-url "$BASE_URL"
  --timeout "$TIMEOUT"
  --heavy-timeout "$HEAVY_TIMEOUT"
  --retries "$RETRIES"
  --heavy-retries "$HEAVY_RETRIES"
  --examples-dir backend/devtools/examples
  --out-dir submission/evidence
)

if [[ -n "${TSOC_INGEST_TOKEN:-}" ]]; then
  args+=(--token "$TSOC_INGEST_TOKEN")
fi

if [[ "$VERBOSE" == "1" || "$VERBOSE" == "true" || "$VERBOSE" == "yes" ]]; then
  args+=(--verbose)
fi

python3 "${args[@]}"
