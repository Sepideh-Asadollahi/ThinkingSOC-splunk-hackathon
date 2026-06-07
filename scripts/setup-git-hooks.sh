#!/usr/bin/env bash
# Point this repo at scripts/git-hooks/ (blocks Cursor Co-authored-by trailers).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
chmod +x "$ROOT/scripts/git-hooks/prepare-commit-msg"
git -C "$ROOT" config core.hooksPath scripts/git-hooks
echo "Git hooks enabled: core.hooksPath=scripts/git-hooks"
