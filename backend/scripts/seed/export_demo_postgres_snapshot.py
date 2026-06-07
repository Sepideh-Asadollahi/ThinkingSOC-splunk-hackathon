#!/usr/bin/env python3
"""Export current PostgreSQL data to backend/data/demo/postgres_snapshot/."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


async def _main(
    out_dir: Path | None,
    *,
    record_limit: int,
    correlation_limit: int,
    full: bool,
) -> int:
    from dotenv import load_dotenv

    load_dotenv(_BACKEND / ".env", override=True)
    from config import get_settings
    from services.demo.postgres_snapshot import export_postgres_snapshot

    settings = get_settings()
    if not (settings.tsoc_postgres_dsn or "").strip():
        print("TSOC_POSTGRES_DSN is not set", file=sys.stderr)
        return 1

    target = await export_postgres_snapshot(
        settings,
        out_dir=out_dir,
        record_limit=record_limit,
        correlation_limit=correlation_limit,
        full=full,
    )
    if full:
        print(f"Exported FULL demo snapshot to {target} (all rows, all tables)")
    else:
        print(
            f"Exported moment demo to {target} "
            f"(full Asset/Identity + last {record_limit} records + "
            f"{correlation_limit} correlation finding(s))"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Override output directory (default: backend/data/demo/postgres_snapshot)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Export ALL rows from every demo table (no limits)",
    )
    parser.add_argument(
        "--record-limit",
        type=int,
        default=6,
        help="Latest tsoc_records to include when not using --full (default: 6; 0 = unlimited)",
    )
    parser.add_argument(
        "--correlation-limit",
        type=int,
        default=1,
        help="Latest graph_findings when not using --full (default: 1; 0 = unlimited)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    return asyncio.run(
        _main(
            args.out_dir,
            record_limit=args.record_limit,
            correlation_limit=args.correlation_limit,
            full=args.full,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
