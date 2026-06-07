"""backend/.env preparation."""

from __future__ import annotations

import shutil
from typing import Dict, List, Tuple

from setup_tool.log import LOG
from setup_tool.paths import DEFAULT_POSTGRES_DSN, ENV_EXAMPLE, ENV_FILE


def load_env_file() -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not ENV_FILE.is_file():
        return out
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def persist_env_key(key: str, value: str) -> None:
    lines: List[str] = []
    if ENV_FILE.is_file():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    found = False
    out: List[str] = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")
    LOG.info("[CONFIG] Wrote %s to %s", key, ENV_FILE)


def step_config() -> Tuple[bool, Dict[str, str]]:
    LOG.info("[CONFIG] Preparing %s", ENV_FILE)
    if not ENV_FILE.is_file():
        if not ENV_EXAMPLE.is_file():
            LOG.error("[CONFIG] Missing .env and .env.example in backend/")
            return False, {}
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        LOG.info("[CONFIG] Created %s from .env.example", ENV_FILE)
    else:
        LOG.info("[CONFIG] Found existing %s", ENV_FILE)

    env = load_env_file()
    dsn = env.get("TSOC_POSTGRES_DSN", "").strip()
    if not dsn:
        LOG.warning("[CONFIG] TSOC_POSTGRES_DSN was empty — setting default for docker-compose Postgres")
        persist_env_key("TSOC_POSTGRES_DSN", DEFAULT_POSTGRES_DSN)
        env["TSOC_POSTGRES_DSN"] = DEFAULT_POSTGRES_DSN
    else:
        LOG.info("[CONFIG] TSOC_POSTGRES_DSN configured")

    if not env.get("TSOC_INVENTORY_SOURCE", "").strip():
        persist_env_key("TSOC_INVENTORY_SOURCE", "postgres")
        env["TSOC_INVENTORY_SOURCE"] = "postgres"

    LOG.info("[CONFIG] OK")
    return True, env
