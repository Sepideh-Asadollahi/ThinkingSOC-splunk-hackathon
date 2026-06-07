"""Project tree validation."""

from __future__ import annotations

from setup_tool.log import LOG
from setup_tool.paths import BACKEND_DIR, DEMO_DATA_DIR, REQUIREMENTS, SCHEMA_SQL


def step_project_layout() -> bool:
    LOG.info("[LAYOUT] Checking project tree")
    ok = True
    for path, label in (
        (BACKEND_DIR, "backend/"),
        (REQUIREMENTS, "backend/requirements.txt"),
        (BACKEND_DIR / "main.py", "backend/main.py"),
        (SCHEMA_SQL, "backend/db/schema.sql"),
        (DEMO_DATA_DIR, "backend/data/demo"),
    ):
        if path.exists():
            LOG.info("[LAYOUT]   OK %s", label)
        else:
            LOG.error("[LAYOUT]   MISSING %s (%s)", label, path)
            ok = False
    return ok
