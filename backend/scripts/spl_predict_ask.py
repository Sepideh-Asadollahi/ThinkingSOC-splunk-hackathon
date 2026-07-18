#!/usr/bin/env python3
"""
Ask Splunk AI Assistant via REST /predict (UI path), then run SPL via MCP ``splunk_run_query``.

Uses the same ``services.spl_predict_pipeline`` module as the ThinkingSOC Lite backend.

Time range for execute is always All Time (SPL earliest=1 latest=now; REST earliest_time=0).

Usage:
  python3 scripts/spl_predict_ask.py --botsv1 -v
  python3 scripts/spl_predict_ask.py -q "..." --no-execute
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from config import get_settings
from services.investigation.spl_predict_pipeline import (
    SPL_ALL_TIME_WINDOW,
    execute_spl_via_mcp,
    generate_spl_via_predict,
)
from splunk.mcp.errors import McpNotConfiguredError, McpToolError

LOG = logging.getLogger("spl_predict_ask")

_REPO_ROOT = _BACKEND_ROOT.parent
_BOTSV1_SAMPLE = _REPO_ROOT / "scripts" / "samples" / "splunk-webhook-botsv1-osk-sysmon.json"

_DEFAULT_MAX_ROWS = 50
_DEFAULT_COL_WIDTH = 44
_SECTION = "=" * 80

_PREFERRED_COLUMNS = (
    "_time",
    "host",
    "Image",
    "ParentImage",
    "ParentCommandLine",
    "ProcessId",
    "ParentProcessId",
    "CommandLine",
    "is_osk",
    "is_ps",
)


def _prompt_from_botsv1_sample(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    result = data.get("result") or {}
    search_name = str(data.get("search_name") or "").strip()
    fields = {
        k: result[k]
        for k in (
            "index",
            "host",
            "Computer",
            "User",
            "user",
            "Image",
            "ParentImage",
            "ParentCommandLine",
            "CommandLine",
            "EventCode",
            "source",
            "signature",
        )
        if k in result
    }
    return (
        "Investigate suspicious osk.exe LOLBAS on host we8105desk: find PowerShell invoke.ps1 "
        "and parent process chain for root cause.\n"
        "Search name: {0}\n"
        "Alert fields: {1}".format(search_name, fields)
    )


def _column_order(rows: Sequence[Dict[str, Any]]) -> List[str]:
    seen: set[str] = set()
    cols: List[str] = []
    for name in _PREFERRED_COLUMNS:
        if any(name in row for row in rows):
            cols.append(name)
            seen.add(name)
    for row in rows:
        for key in row:
            if key not in seen:
                cols.append(key)
                seen.add(key)
    return cols


def _cell_str(value: Any, max_width: int) -> str:
    if value is None:
        text = ""
    else:
        text = str(value).replace("\r", " ").replace("\n", " ")
    if len(text) <= max_width:
        return text
    if max_width < 2:
        return text[:max_width]
    return text[: max_width - 1] + "…"


def _format_ascii_table(
    rows: Sequence[Dict[str, Any]],
    columns: Sequence[str],
    *,
    max_col_width: int,
) -> str:
    if not rows:
        return "(no rows)"
    headers = list(columns)
    matrix = [[_cell_str(row.get(col), max_col_width) for col in headers] for row in rows]
    widths = [len(h) for h in headers]
    for row in matrix:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    hline = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def _row(cells: Sequence[str]) -> str:
        return "|" + "|".join(" {0:{1}} ".format(c, w) for c, w in zip(cells, widths)) + "|"

    lines = [hline, _row(headers), hline]
    for row in matrix:
        lines.append(_row(row))
    lines.append(hline)
    return "\n".join(lines)


def _print_spl_block(spl: str) -> None:
    print(_SECTION)
    print("SPL  |  time range: All Time (earliest=1 latest=now)")
    print(_SECTION)
    print(spl)
    print()


def _print_results_table(
    result_rows: Sequence[Dict[str, Any]],
    *,
    total_rows: int,
    truncated: bool,
    max_col_width: int,
) -> None:
    print(_SECTION)
    print("Results  |  All Time (REST earliest_time=0, latest_time=now)")
    print(_SECTION)
    meta = "total_rows={0}  displayed={1}".format(total_rows, len(result_rows))
    if truncated:
        meta += "  (truncated)"
    print(meta)
    print()
    if not result_rows:
        print("(no rows)")
        print()
        return
    print(_format_ascii_table(result_rows, _column_order(result_rows), max_col_width=max_col_width))
    print()


async def ask_once(
    question: str,
    *,
    show_raw: bool,
    timeout_seconds: float,
    poll_interval: float,
    execute: bool,
    max_rows: int,
    max_col_width: int,
    json_rows: bool,
) -> int:
    settings = get_settings()
    if not settings.splunk_username or not settings.splunk_password:
        print("Set SPLUNK_USERNAME and SPLUNK_PASSWORD in backend/.env", file=sys.stderr)
        return 1

    LOG.info(
        "Splunk mgmt=%s user=%s timeout=%.0fs",
        settings.splunk_mgmt_url,
        settings.splunk_username,
        timeout_seconds,
    )
    LOG.info("Question (%d chars): %s", len(question), question[:200])

    rc = await generate_spl_via_predict(
        settings,
        prompt=question.strip(),
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval,
    )
    if rc is None or not rc.spl:
        print("ERROR: /predict did not return SPL", file=sys.stderr)
        if "500" in str(getattr(rc, "explanation", "")):
            print("Hint: HTTP 500 — retry or check Splunk UI chat.", file=sys.stderr)
        return 1

    spl = rc.spl
    if show_raw:
        print("--- RAW (parsed SPL only; full assistant text not stored in pipeline) ---")
        print(spl)
        print()
    _print_spl_block(spl)
    LOG.info("Done spl_len=%d", len(spl))

    if not execute:
        return 0
    try:
        sr = await execute_spl_via_mcp(settings, spl, row_limit=max_rows)
    except (McpNotConfiguredError, McpToolError) as e:
        print("ERROR:", e, file=sys.stderr)
        return 1
    if sr.error:
        print("ERROR: MCP execute failed:", sr.error, file=sys.stderr)
        return 1

    if json_rows:
        print(
            json.dumps(
                {
                    "spl": spl,
                    "time_window": SPL_ALL_TIME_WINDOW,
                    "total_rows": sr.row_count,
                    "rows": sr.rows,
                    "truncated": sr.truncated,
                },
                ensure_ascii=False,
                default=str,
            )
        )
    else:
        _print_results_table(
            sr.rows,
            total_rows=sr.row_count or len(sr.rows),
            truncated=bool(sr.truncated),
            max_col_width=max_col_width,
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SAIA /predict (UI path) + MCP splunk_run_query (All Time)."
    )
    parser.add_argument("-q", "--question", help="Question / prompt (interactive if omitted)")
    parser.add_argument("--raw", action="store_true", help="Print SPL before table")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logs")
    parser.add_argument("--timeout", type=float, default=None, help="SAIA /predict wait (default 90s)")
    parser.add_argument("--poll-interval", type=float, default=None, help="chathistory poll interval")
    parser.add_argument("--no-execute", action="store_true", help="Only generate SPL")
    parser.add_argument("--max-rows", type=int, default=_DEFAULT_MAX_ROWS, help="MCP row_limit")
    parser.add_argument("--col-width", type=int, default=_DEFAULT_COL_WIDTH, help="Table column width")
    parser.add_argument("--json", action="store_true", help="JSON output instead of table")
    parser.add_argument("--botsv1", action="store_true", help="Use botsv1 osk.exe sample JSON")
    parser.add_argument("--sample", type=Path, default=None, help="Webhook JSON sample path")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("tsoc.trace.mcp").setLevel(logging.DEBUG if args.verbose else logging.WARNING)

    settings = get_settings()
    timeout = args.timeout or float(getattr(settings, "tsoc_spl_predict_timeout_seconds", 90.0))
    poll_iv = args.poll_interval or float(
        getattr(settings, "tsoc_spl_predict_poll_interval_seconds", 0.75)
    )
    max_rows = max(1, min(1000, args.max_rows))
    max_col_width = max(12, min(120, args.col_width))
    execute = not args.no_execute

    question = args.question
    if args.botsv1:
        sample_path = _BOTSV1_SAMPLE
        if not sample_path.is_file():
            print("Sample not found: {0}".format(sample_path), file=sys.stderr)
            return 1
        question = _prompt_from_botsv1_sample(sample_path)
    elif args.sample is not None:
        if not args.sample.is_file():
            print("Sample not found: {0}".format(args.sample), file=sys.stderr)
            return 1
        question = _prompt_from_botsv1_sample(args.sample.resolve())

    if question:
        return asyncio.run(
            ask_once(
                question,
                show_raw=args.raw,
                timeout_seconds=timeout,
                poll_interval=poll_iv,
                execute=execute,
                max_rows=max_rows,
                max_col_width=max_col_width,
                json_rows=args.json,
            )
        )

    print("Splunk /predict + MCP execute (All Time). Empty line to quit.\n")
    while True:
        try:
            line = input("Question> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            return 0
        code = asyncio.run(
            ask_once(
                line,
                show_raw=args.raw,
                timeout_seconds=timeout,
                poll_interval=poll_iv,
                execute=execute,
                max_rows=max_rows,
                max_col_width=max_col_width,
                json_rows=args.json,
            )
        )
        if code != 0:
            return code
        print()


if __name__ == "__main__":
    raise SystemExit(main())
