#!/usr/bin/env python3
"""Evaluate agent/assistant quality on a scenario matrix for hackathon demos."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Tuple

from devtools import TsocSdkClient


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
    parser = argparse.ArgumentParser(description="Evaluate ThinkingSOC agent/assistant outputs on fixed scenarios.")
    parser.add_argument("--matrix", required=True, help="Path to scenario matrix JSON.")
    parser.add_argument("--base-url", default="http://127.0.0.1:9876")
    parser.add_argument("--token", default=None)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--out", default=None, help="Optional output JSON path.")
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

    results: List[Dict[str, Any]] = []
    total = 0
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
        results.append(
            {
                "scenario_index": idx,
                "scenario_name": s.get("name"),
                "score": row_score,
                "details": details,
                "agent_summary": agent_out.get("agent_summary"),
                "spl_source": spl_out.get("source"),
            }
        )

    max_score = 100 * len(scenarios)
    report = {
        "scenario_count": len(scenarios),
        "max_score": max_score,
        "total_score": total,
        "score_percent": round((total / max_score) * 100.0, 2),
        "results": results,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()

