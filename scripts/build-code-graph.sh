#!/usr/bin/env bash
# Build code-review-graph and export public artifacts under docs/code-graph/ (for GitHub).
# https://github.com/tirth8205/code-review-graph
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${ROOT}/.tools/crg-venv"
CRG="${VENV}/bin/code-review-graph"
PUBLIC_DIR="${ROOT}/docs/code-graph"
COMMUNITIES_DIR="${PUBLIC_DIR}/communities"

if [[ ! -x "$CRG" ]]; then
  echo "Creating tooling venv and installing code-review-graph..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -U pip
  "$VENV/bin/pip" install 'code-review-graph[wiki,communities]'
fi

cd "$ROOT"
echo "==> Building knowledge graph..."
"$CRG" build --repo "$ROOT"

echo "==> Graph status"
"$CRG" status --repo "$ROOT"

echo "==> Generating wiki..."
"$CRG" wiki --repo "$ROOT" --force

echo "==> HTML visualization (community mode)"
"$CRG" visualize --repo "$ROOT" --format html --mode community

echo "==> Exporting to docs/code-graph/"
mkdir -p "$COMMUNITIES_DIR"
cp -f "${ROOT}/.code-review-graph/graph.html" "${PUBLIC_DIR}/graph.html"
rm -f "${COMMUNITIES_DIR}"/*.md

for f in "${ROOT}/.code-review-graph/wiki/"*.md; do
  base=$(basename "$f")
  sed "s|${ROOT}/||g" "$f" > "${COMMUNITIES_DIR}/${base}"
done

# index.md: same-folder links for communities/*.md
if [[ -f "${COMMUNITIES_DIR}/index.md" ]]; then
  :
fi

# Write snapshot (see docs/05-codebase-map.md)
"$CRG" status --repo "$ROOT" > "${PUBLIC_DIR}/graph-status.txt" 2>&1 || true

echo "Done."
echo "  Public export: docs/code-graph/graph.html + docs/code-graph/communities/"
echo "  Local index:   .code-review-graph/graph.db"
