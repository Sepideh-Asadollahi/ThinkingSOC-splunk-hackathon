#!/usr/bin/env python3
"""Validate the installable demo bundle and its complete Runbook judge tour."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

SCENARIO_ID = "judge-tour-runbook-v1"
SEARCH_NAME = "Judge Demo: Suspicious OAuth Token Replay"
SOURCE_SID = "demo-runbook-source-20260716"
TARGET_SID = "demo-runbook-target-20260716"
CHAT_ID = "demo-runbook-judge-tour-v1"
REQUIRED_TYPES = {
    "soc_analysis",
    "investigation_analyst_action",
    "verified_runbook_draft",
    "verified_runbook_approval",
    "verified_runbook_shadow_run",
    "verified_runbook_run",
    "verified_runbook_response_preview",
    "verified_runbook_response_decision",
    "verified_runbook_autopilot_session",
}
BASELINE_SEARCH_NAMES = {
    "New TesT",
    "PaloAlto: Outbound Connection to Known C2 (t8372)",
    "Suspicious Process - osk.exe Sysmon EID 1 (botsv1)",
    "Host CPU spike with latency - payment-api (web-prod-01)",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("payload")
    return value if isinstance(value, dict) else {}


def _one(records: list[dict[str, Any]], record_type: str) -> dict[str, Any]:
    matches = [row for row in records if row.get("tsoc_record_type") == record_type]
    _require(len(matches) == 1, f"expected one {record_type}, got {len(matches)}")
    return _payload(matches[0])


def validate_contract(
    *,
    records: list[dict[str, Any]],
    rag_documents: list[dict[str, Any]],
    conversations: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    counts: dict[str, int],
) -> dict[str, Any]:
    scenario = [row for row in records if _payload(row).get("demo_scenario_id") == SCENARIO_ID]
    _require(len(scenario) == 10, f"judge tour must contain 10 records, got {len(scenario)}")
    _require(REQUIRED_TYPES <= {str(row.get("tsoc_record_type")) for row in scenario}, "judge tour record types incomplete")

    analyses = [row for row in scenario if row.get("tsoc_record_type") == "soc_analysis"]
    _require(len(analyses) == 2, "judge tour must contain source and target analyses")
    _require({str(row.get("sid")) for row in analyses} == {SOURCE_SID, TARGET_SID}, "source/target SIDs are missing")
    _require({str(row.get("search_name")) for row in analyses} == {SEARCH_NAME}, "source/target Alert Names differ")
    _require(SOURCE_SID != TARGET_SID, "source and target SID must differ")

    draft = _one(scenario, "verified_runbook_draft")
    _require(draft.get("status") == "SOURCE_VERIFIED", "runbook draft is not source verified")
    _require(int(draft.get("parser_valid_step_count") or 0) == 3, "runbook parser-valid count is not 3")
    _require(int(draft.get("successful_step_count") or 0) == 3, "runbook successful count is not 3")
    _require(int(draft.get("total_evidence_rows") or 0) == 3, "runbook evidence row count is not 3")
    source_results = draft.get("source_results") or []
    _require(len(source_results) == 3, "runbook must contain three source results")
    _require(
        all(
            isinstance(item, dict)
            and str(item.get("spl") or "").lstrip().startswith("search ")
            and isinstance(item.get("validation"), dict)
            and item["validation"].get("valid") is True
            and isinstance(item.get("spl_results"), dict)
            and not item["spl_results"].get("error")
            and int(item["spl_results"].get("row_count") or 0) > 0
            for item in source_results
        ),
        "runbook source results must be safe, parser-valid, and evidence-bearing",
    )

    approval = _one(scenario, "verified_runbook_approval")
    shadow = _one(scenario, "verified_runbook_shadow_run")
    run = _one(scenario, "verified_runbook_run")
    preview = _one(scenario, "verified_runbook_response_preview")
    decision = _one(scenario, "verified_runbook_response_decision")
    autopilot = _one(scenario, "verified_runbook_autopilot_session")
    _require(approval.get("decision") == "approve", "human approval missing")
    _require(shadow.get("status") == "EVIDENCE_FOUND", "shadow run has no evidence")
    _require(shadow.get("source_sid") != shadow.get("target_sid"), "shadow run reused the same SID")
    _require(run.get("status") == "REUSED", "approved runbook was not reused")
    _require(preview.get("execution_supported") is False, "response preview must remain non-executable")
    _require(decision.get("automatic_execution_performed") is False, "response decision auto-executed")
    _require(autopilot.get("status") == "COMPLETED", "Autopilot session is incomplete")
    _require(len(autopilot.get("agents") or []) == 5, "Autopilot must show five agents")
    _require(len(autopilot.get("trace") or []) >= 10, "Autopilot trace is incomplete")
    _require(autopilot.get("human_approval_required") is True, "Autopilot human gate missing")
    _require(autopilot.get("automatic_execution_performed") is False, "Autopilot auto-executed a response")

    judge_rag = [doc for doc in rag_documents if doc.get("search_name") == SEARCH_NAME]
    _require(len(judge_rag) >= 9, f"expected at least 9 judge RAG documents, got {len(judge_rag)}")
    _require(any(str(row.get("conversation_id")) == CHAT_ID for row in conversations), "judge Chat conversation missing")
    judge_messages = [row for row in messages if str(row.get("conversation_id")) == CHAT_ID]
    _require([str(row.get("role")) for row in judge_messages] == ["user", "assistant"], "judge Chat messages are incomplete")

    stored_names = {str(row.get("search_name")) for row in records if row.get("search_name")}
    _require(BASELINE_SEARCH_NAMES <= stored_names, "one or more pre-existing demo scenarios were removed")
    _require(counts.get("tsoc_users", 0) >= 7, "baseline demo users are incomplete")
    _require(counts.get("tsoc_assets", 0) >= 7, "baseline demo assets are incomplete")
    _require(counts.get("tsoc_relationships", 0) >= 8, "baseline demo relationships are incomplete")

    from config import Settings
    from services.investigation.spl_tstats_sanitize import sanitize_spl_draft

    malformed = (
        'search index=firewall | eval is_benign=if(isnotnull(Sub_Status) '
        '(Sub_Status="Valid" OR Sub_Status="Trusted"),1,0) | table is_benign'
    )
    repaired = sanitize_spl_draft(malformed)
    _require("isnotnull(Sub_Status) AND (" in repaired, "deterministic SPL repair failed")
    settings = Settings()
    _require(settings.tsoc_spl_llm_refine_on_error is True, "SPL error refine is disabled")
    _require(settings.tsoc_spl_execute_refine_max_attempts == 3, "SPL refine attempts must be 3")

    return {
        "records": len(records),
        "judge_records": len(scenario),
        "judge_rag_documents": len(judge_rag),
        "judge_chat_messages": len(judge_messages),
        "autopilot_agents": len(autopilot.get("agents") or []),
        "autopilot_trace_events": len(autopilot.get("trace") or []),
        "spl_auto_repair": True,
        "spl_refine_attempts": settings.tsoc_spl_execute_refine_max_attempts,
    }


def validate_snapshot(snapshot_dir: Path) -> dict[str, Any]:
    manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
    tables: dict[str, list[dict[str, Any]]] = {}
    counts: dict[str, int] = {}
    for entry in manifest.get("tables") or []:
        name = str(entry["name"])
        rows = json.loads((snapshot_dir / str(entry["file"])).read_text(encoding="utf-8"))
        _require(isinstance(rows, list), f"snapshot table {name} is not a list")
        _require(len(rows) == int(entry["rows"]), f"manifest count mismatch for {name}")
        tables[name] = rows
        counts[name] = len(rows)
    return validate_contract(
        records=tables["tsoc_records"],
        rag_documents=tables["tsoc_rag_documents"],
        conversations=tables["tsoc_chat_conversations"],
        messages=tables["tsoc_chat_messages"],
        counts=counts,
    )


async def validate_database(dsn: str) -> dict[str, Any]:
    import asyncpg

    conn = await asyncpg.connect(dsn)
    try:
        async def rows(table: str) -> list[dict[str, Any]]:
            result = await conn.fetch(f"SELECT * FROM {table}")
            return [dict(row) for row in result]

        records = await rows("tsoc_records")
        for row in records:
            if isinstance(row.get("payload"), str):
                row["payload"] = json.loads(row["payload"])
        rag_documents = await rows("tsoc_rag_documents")
        conversations = await rows("tsoc_chat_conversations")
        messages = await rows("tsoc_chat_messages")
        counts = {
            name: int(await conn.fetchval(f"SELECT COUNT(*) FROM {name}"))
            for name in ("tsoc_users", "tsoc_assets", "tsoc_relationships")
        }
        return validate_contract(
            records=records,
            rag_documents=rag_documents,
            conversations=conversations,
            messages=messages,
            counts=counts,
        )
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", type=Path)
    parser.add_argument("--database-url")
    args = parser.parse_args()
    _require(bool(args.snapshot_dir) ^ bool(args.database_url), "select exactly one validation source")
    report = (
        validate_snapshot(args.snapshot_dir)
        if args.snapshot_dir
        else asyncio.run(validate_database(str(args.database_url)))
    )
    print(json.dumps({"ok": True, **report}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
