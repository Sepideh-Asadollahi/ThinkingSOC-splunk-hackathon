#!/usr/bin/env python3
"""Add the complete, non-destructive Runbook judge tour to PostgreSQL demo data."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


async def _main(*, no_rag: bool) -> int:
    from dotenv import load_dotenv

    load_dotenv(_BACKEND / ".env", override=True)
    from config import get_settings
    from services.demo.runbook_judge_demo import seed_runbook_judge_demo
    from services.splunk_json_store.pg import close_store

    settings = get_settings()
    if not (settings.tsoc_postgres_dsn or "").strip():
        print("TSOC_POSTGRES_DSN is not set", file=sys.stderr)
        return 1
    try:
        report = await seed_runbook_judge_demo(settings, backfill_rag=not no_rag)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 0
    finally:
        await close_store()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-rag",
        action="store_true",
        help="Skip RAG backfill (useful only for isolated validation).",
    )
    args = parser.parse_args()
    return asyncio.run(_main(no_rag=args.no_rag))


if __name__ == "__main__":
    raise SystemExit(main())
