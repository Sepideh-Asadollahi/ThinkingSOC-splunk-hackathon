#!/usr/bin/env python3
"""
Full project setup (does not start the API server).

  python3 setup.py                  # venv + pip + postgres + schema + seed
  python3 setup.py --log-file setup.log -v

Implementation lives in the ``setup_tool`` package (modular steps).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from setup_tool.runner import main

if __name__ == "__main__":
    raise SystemExit(main())
