#!/usr/bin/env python3
"""Evaluate agent/assistant quality on a scenario matrix for hackathon demos."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Tuple

from devtools import TsocSdkClient
from devtools.workflows import build_doctor_report


def _score_connectivity(doctor: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """Score platform connectivity (max 100)."""
    checks = doctor.get("checks") or {}
    score = 0
    details: Dict[str, Any] = {}

    backend = checks.get("backend") or {}
    if backend.get("ok"):
        score += 25
        details["backend_ok"] = True
    else:
        details["backend_ok"] = False

    mcp = checks.get("mcp") or {}
    if mcp.get("ok"):
        score += 35
        details["mcp_ok"] = True
    else:
        details["mcp_ok"] = False
    if mcp.get("saia_available"):
        score += 15
        details["saia_available"] = True
    else:
        details["saia_available"] = False

    llm = checks.get("llm") or {}
    if llm.get("ok"):
        score += 15
        details["llm_ok"] = True
    else:
        details["llm_ok"] = False

    chat = checks.get("soc_chat") or {}
    if chat.get("ok"):
        score += 10
        details["soc_chat_ok"] = True
    else:
        details["soc_chat_ok"] = False

    graph = checks.get("graph") or {}
    if graph.get("ok"):
        score += 5
        details["graph_ok"] = True
    else:
        details["graph_ok"] = False

    inventory = checks.get("inventory") or {}
    if inventory.get("ok"):
        score += 5
        details["inventory_ok"] = True
    else:
        details["inventory_ok"] = False

    return min(score, 100), details


def _score_mcp_spl(mcp_spl: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """Score MCP SAIA SPL generation (max 100)."""
    score = 0
    details: Dict[str, Any] = {}
    source = str(mcp_spl.get("source") or "")
    spl_text = str(mcp_spl.get("spl") or "")

    if source == "splunk_mcp_saia":
        score += 40
        details["source_ok"] = True
    else:
        details["source_ok"] = False

    if "search" in spl_text and len(spl_text) >= 20:
        score += 40
        details["spl_ok"] = True
    else:
        details["spl_ok"] = False

    if mcp_spl.get("explanation"):
        score += 20
        details["explanation_ok"] = True
    else:
        details["explanation_ok"] = False

    return score, details


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _score_row(expected_track: str, agent: Dict[str, Any], spl: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    score = 0
    details: Dict[str, Any] = {
        "expected_track": expected_track,
        "actual_track": agent.get("track"),
    }

    if agent.get("track") == expected_track:
        score += 30
        details["track_match"] = True
    else:
        details["track_match"] = False

    cls = agent.get("classification") or {}
    if isinstance(cls.get("confidence"), (int, float)) and float(cls.get("confidence")) >= 0.6:
        score += 15
        details["confidence_ok"] = True
    else:
        details["confidence_ok"] = False

    actions = agent.get("next_actions") or []
    if isinstance(actions, list) and len(actions) >= 3:
        score += 15
        details["actions_ok"] = True
    else:
        details["actions_ok"] = False

    if expected_track == "security":
        ok = agent.get("security_result") is not None
    elif expected_track == "observability":
        ok = agent.get("observability_result") is not None
    else:
        ok = agent.get("security_result") is not None and agent.get("observability_result") is not None
    if ok:
        score += 20
        details["pipeline_output_ok"] = True
    else:
        details["pipeline_output_ok"] = False

    rc = (spl.get("root_cause_spl") or {}) if isinstance(spl, dict) else {}
    spl_text = str(rc.get("spl") or "")
    if "search" in spl_text and len(spl_text) >= 30:
        score += 20
        details["spl_ok"] = True
    else:
        details["spl_ok"] = False

    return score, details


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate ThinkingSOC Lite agent/assistant outputs on fixed scenarios.")
    parser.add_argument("--matrix", required=True, help="Path to scenario matrix JSON.")
    parser.add_argument("--base-url", default="http://127.0.0.1:9876")
    parser.add_argument("--token", default=None)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--out", default=None, help="Optional output JSON path.")
    parser.add_argument(
        "--check-mcp",
        action="store_true",
        help="Run MCP SAIA SPL generation per scenario (when mcp_query set).",
    )
    args = parser.parse_args()

    token = args.token or os.environ.get("TSOC_INGEST_TOKEN")
    matrix = _load_json(args.matrix)
    scenarios: List[Dict[str, Any]] = list(matrix.get("scenarios") or [])
    if not scenarios:
        raise SystemExit("No scenarios found in matrix.")

    client = TsocSdkClient(
        base_url=args.base_url,
        ingest_token=token,
        timeout_seconds=args.timeout,
        max_retries=args.retries,
    )

    doctor = client.doctor()
    connectivity_score, connectivity_details = _score_connectivity(doctor)

    results: List[Dict[str, Any]] = []
    total = 0
    mcp_total = 0
    mcp_count = 0
    for idx, s in enumerate(scenarios):
        expected_track = str(s.get("expected_track") or "unknown")
        body = {
            "search_name": s.get("search_name"),
            "normalized": s.get("normalized") or {},
            "operator_goal": s.get("operator_goal"),
            "users": s.get("users"),
            "assets": s.get("assets"),
            "relationships": s.get("relationships"),
        }
        agent_out = client.run_agent_triage(body).model_dump(mode="json")
        spl_out = client.suggest_spl(
            {
                "search_name": s.get("search_name"),
                "normalized": s.get("normalized") or {},
                "objective": s.get("operator_goal") or "collect root cause evidence",
            }
        ).model_dump(mode="json")
        row_score, details = _score_row(expected_track, agent_out, spl_out)
        total += row_score

        mcp_row: Dict[str, Any] = {}
        mcp_query = s.get("mcp_query")
        if args.check_mcp and mcp_query:
            try:
                mcp_out = client.mcp_generate_spl({"query": str(mcp_query)}).model_dump(mode="json")
                mcp_score, mcp_details = _score_mcp_spl(mcp_out)
                mcp_total += mcp_score
                mcp_count += 1
                mcp_row = {"score": mcp_score, "details": mcp_details, "source": mcp_out.get("source")}
            except Exception as exc:
                mcp_row = {"score": 0, "error": str(exc)}

        results.append(
            {
                "scenario_index": idx,
                "scenario_name": s.get("name"),
                "score": row_score,
                "details": details,
                "agent_summary": agent_out.get("agent_summary"),
                "spl_source": spl_out.get("source"),
                "mcp": mcp_row or None,
            }
        )

    max_score = 100 * len(scenarios)
    report: Dict[str, Any] = {
        "scenario_count": len(scenarios),
        "max_score": max_score,
        "total_score": total,
        "score_percent": round((total / max_score) * 100.0, 2),
        "connectivity": {
            "score": connectivity_score,
            "max_score": 100,
            "ready_for_demo": doctor.get("ready_for_demo"),
            "details": connectivity_details,
            "doctor": doctor,
        },
        "results": results,
    }
    if mcp_count:
        report["mcp_saia"] = {
            "scenario_count": mcp_count,
            "max_score": 100 * mcp_count,
            "total_score": mcp_total,
            "score_percent": round((mcp_total / (100 * mcp_count)) * 100.0, 2),
        }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()

