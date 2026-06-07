"""Graph correlation settings — always uses unified backend ``config.Settings``."""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"


def _ensure_backend_on_path() -> None:
    if _BACKEND_DIR.is_dir():
        path = str(_BACKEND_DIR)
        if path not in sys.path:
            sys.path.insert(0, path)


_ensure_backend_on_path()
from config import Settings, get_settings as _backend_get_settings  # noqa: E402


@lru_cache
def get_settings() -> Settings:
    return _backend_get_settings()
