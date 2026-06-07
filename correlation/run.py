#!/usr/bin/env python3
"""Deprecated: Correlation runs inside the unified backend (backend/run.py)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_RUN = REPO_ROOT / "backend" / "run.py"


def main() -> None:
    sys.stderr.write(
        "Correlation is integrated into the unified backend.\n"
        "Starting backend/run.py (API at /api/v1/graph on TSOC_HTTP_PORT, default 9876) …\n"
    )
    os.execv(sys.executable, [sys.executable, str(BACKEND_RUN), *sys.argv[1:]])


if __name__ == "__main__":
    main()
