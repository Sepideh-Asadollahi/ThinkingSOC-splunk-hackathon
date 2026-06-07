"""CLI argument parsing."""

from __future__ import annotations

import argparse
from pathlib import Path

from setup_tool.paths import DEFAULT_LOG_FILE, REPO_ROOT


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Full ThinkingSOC setup: venv, pip, Postgres, schema (does not start API)",
    )
    p.add_argument(
        "--start-postgres",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Start Postgres via docker compose if not running (default: true)",
    )
    p.add_argument("--skip-pip", action="store_true", help="Skip pip install (still verify imports)")
    p.add_argument("--skip-docker", action="store_true", help="Do not manage Docker/Postgres")
    p.add_argument("--skip-schema", action="store_true", help="Do not apply schema.sql")
    p.add_argument("--no-seed", action="store_true", help="Do not seed inventory from CSV")
    p.add_argument(
        "--log-file",
        type=Path,
        default=DEFAULT_LOG_FILE,
        help="Write log to file (default: setup.log in repo root)",
    )
    p.add_argument("--no-log-file", action="store_true", help="Do not write setup.log")
    p.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    return p.parse_args()


def resolve_log_path(args: argparse.Namespace) -> Path | None:
    if args.no_log_file:
        return None
    log_path = args.log_file
    if log_path and not log_path.is_absolute():
        log_path = REPO_ROOT / log_path
    return log_path
