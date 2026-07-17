#!/usr/bin/env python3
"""Generate a submission-ready evidence pack for Devpost."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

# Ensure local backend packages win over any site-packages `devtools`.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_BACKEND_DIR = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from devtools import TsocSdkClient


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _vlog(verbose: bool, msg: str) -> None:
    if verbose:
        print(msg, flush=True)


def _result_hint(data: Dict[str, Any]) -> str:
    if "error" in data:
        return "error={0}".format(data.get("error"))
    for key in ("track", "classification", "agent_summary", "source", "connected", "configured"):
        if key in data and data[key] is not None:
            return "{0}={1}".format(key, data[key])
    return "ok"


def _safe_call(label: str, fn: Callable[[], Dict[str, Any]], *, verbose: bool = False) -> Dict[str, Any]:
    # Keep evidence generation resilient: a single endpoint failure (e.g. timeout)
    # must not abort the whole pack. Failures are recorded as error payloads.
    _vlog(verbose, "[start] {0}".format(label))
    started = time.monotonic()
    try:
        result = fn()
        elapsed = time.monotonic() - started
        _vlog(verbose, "[ok]    {0} ({1:.1f}s) {2}".format(label, elapsed, _result_hint(result)))
        return result
    except Exception as exc:
        elapsed = time.monotonic() - started
        print("[warn] {0} failed after {1:.1f}s: {2}".format(label, elapsed, exc), file=sys.stderr)
        _vlog(verbose, "[fail]  {0} ({1:.1f}s) {2}: {3}".format(label, elapsed, type(exc).__name__, exc))
        return {"error": type(exc).__name__, "message": str(exc)}


def _score_row(expected_track: str, agent: Dict[str, Any], spl: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    score = 0
    details: Dict[str, Any] = {"expected_track": expected_track, "actual_track": agent.get("track")}
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
        pipeline_ok = agent.get("security_result") is not None
    elif expected_track == "observability":
        pipeline_ok = agent.get("observability_result") is not None
    else:
        pipeline_ok = agent.get("security_result") is not None and agent.get("observability_result") is not None
    if pipeline_ok:
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


def _run_eval_matrix(client: TsocSdkClient, matrix: Dict[str, Any], *, verbose: bool = False) -> Dict[str, Any]:
    scenarios = list(matrix.get("scenarios") or [])
    if not scenarios:
        _vlog(verbose, "[skip]  eval_matrix: no scenarios")
        return {
            "scenario_count": 0,
            "max_score": 0,
            "total_score": 0,
            "score_percent": 0.0,
            "results": [],
        }
    _vlog(verbose, "[start] eval_matrix ({0} scenarios)".format(len(scenarios)))
    results = []
    total = 0
    for idx, s in enumerate(scenarios):
        scenario_name = s.get("name") or "scenario-{0}".format(idx)
        expected_track = str(s.get("expected_track") or "unknown")
        _vlog(verbose, "[step]  eval[{0}] {1} expected_track={2}".format(idx, scenario_name, expected_track))
        agent_req = {
            "search_name": s.get("search_name"),
            "normalized": s.get("normalized") or {},
            "operator_goal": s.get("operator_goal"),
            "users": s.get("users"),
            "assets": s.get("assets"),
            "relationships": s.get("relationships") or [],
            "identity_rules": s.get("identity_rules"),
        }
        spl_req = {
            "search_name": s.get("search_name"),
            "normalized": s.get("normalized") or {},
            "objective": s.get("operator_goal") or "collect root cause evidence",
        }
        agent_out = _safe_call(
            "eval[{0}] agent".format(idx),
            lambda: client.run_agent_triage(agent_req).model_dump(mode="json"),
            verbose=verbose,
        )
        spl_out = _safe_call(
            "eval[{0}] spl".format(idx),
            lambda: client.suggest_spl(spl_req).model_dump(mode="json"),
            verbose=verbose,
        )
        row_score, details = _score_row(expected_track, agent_out, spl_out)
        total += row_score
        _vlog(
            verbose,
            "[score] eval[{0}] {1} score={2} track_match={3} spl_ok={4}".format(
                idx,
                scenario_name,
                row_score,
                details.get("track_match"),
                details.get("spl_ok"),
            ),
        )
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
    _vlog(
        verbose,
        "[done]  eval_matrix total={0}/{1} ({2}%)".format(
            report["total_score"],
            report["max_score"],
            report["score_percent"],
        ),
    )
    return report


def _count_errors(*payloads: Dict[str, Any]) -> int:
    return sum(1 for p in payloads if isinstance(p, dict) and "error" in p)


def _summary_md(report: Dict[str, Any]) -> str:
    return (
        "# Evidence Summary\n\n"
        "- Scenario count: `{0}`\n"
        "- Total score: `{1}` / `{2}`\n"
        "- Score percent: `{3}%`\n\n"
        "## Scenarios\n\n".format(
            report.get("scenario_count"),
            report.get("total_score"),
            report.get("max_score"),
            report.get("score_percent"),
        )
        + "\n".join(
            "- `{0}` score={1} track_match={2} confidence_ok={3} pipeline_output_ok={4} spl_ok={5}".format(
                r.get("scenario_name"),
                r.get("score"),
                (r.get("details") or {}).get("track_match"),
                (r.get("details") or {}).get("confidence_ok"),
                (r.get("details") or {}).get("pipeline_output_ok"),
                (r.get("details") or {}).get("spl_ok"),
            )
            for r in report.get("results", [])
        )
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build submission evidence pack from live API outputs.")
    parser.add_argument("--base-url", default="http://127.0.0.1:9876")
    parser.add_argument("--token", default=None)
    parser.add_argument("--timeout", type=float, default=120.0, help="Timeout for fast endpoints (classify, spl, mcp)")
    parser.add_argument(
        "--heavy-timeout",
        type=float,
        default=None,
        help="Timeout for heavy endpoints (route, triage, eval). Default: max(timeout, 1800) = 30 min",
    )
    parser.add_argument("--retries", type=int, default=0, help="Retries for fast endpoints")
    parser.add_argument(
        "--heavy-retries",
        type=int,
        default=0,
        help="Retries for heavy endpoints (keep 0 to avoid duplicate LLM runs)",
    )
    parser.add_argument(
        "--examples-dir",
        default="backend/devtools/examples",
        help="Path containing classify.json/route.json/agent.json/spl.json/eval_matrix.json",
    )
    parser.add_argument("--out-dir", default="submission/evidence")
    parser.add_argument(
        "--forge-source-record-id",
        type=int,
        default=None,
        help="Acknowledged soc_analysis record used to compile and approve a Forge runbook.",
    )
    parser.add_argument(
        "--forge-target-record-id",
        type=int,
        default=None,
        help="Different soc_analysis record with the same search_name used for Forge reuse.",
    )
    parser.add_argument(
        "--forge-manual-minutes",
        type=int,
        default=25,
        help="Visible manual-investigation baseline for the measured savings artifact (5..120).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Print step-by-step progress to stdout")
    args = parser.parse_args()
    verbose = args.verbose
    heavy_timeout = args.heavy_timeout if args.heavy_timeout is not None else max(args.timeout, 1800.0)

    token = args.token or os.environ.get("TSOC_INGEST_TOKEN")
    client = TsocSdkClient(
        base_url=args.base_url,
        ingest_token=token,
        timeout_seconds=args.timeout,
        max_retries=args.retries,
    )
    heavy_client = TsocSdkClient(
        base_url=args.base_url,
        ingest_token=token,
        timeout_seconds=heavy_timeout,
        max_retries=args.heavy_retries,
    )

    examples_dir = Path(args.examples_dir)
    out_root = Path(args.out_dir)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    _vlog(verbose, "=== ThinkingSOC evidence pack ===")
    _vlog(verbose, "base_url={0} timeout={1}s heavy_timeout={2}s retries={3} heavy_retries={4}".format(
        args.base_url, args.timeout, heavy_timeout, args.retries, args.heavy_retries,
    ))
    _vlog(verbose, "examples_dir={0}".format(examples_dir.resolve()))
    _vlog(verbose, "out_dir={0}".format(out_dir.resolve()))
    _vlog(verbose, "token={0}".format("set" if token else "not set"))

    _vlog(verbose, "[load]  example payloads")
    classify_req = _load_json(examples_dir / "classify.json")
    route_req = _load_json(examples_dir / "route.json")
    agent_req = _load_json(examples_dir / "agent.json")
    spl_req = _load_json(examples_dir / "spl.json")
    eval_matrix = _load_json(examples_dir / "eval_matrix.json")
    _vlog(verbose, "[load]  eval_matrix scenarios={0}".format(len(eval_matrix.get("scenarios") or [])))
    _vlog(verbose, "[note]  heavy endpoints (route/triage/eval) may take several minutes with LLM pipeline")

    classify_res = _safe_call(
        "classify_alert",
        lambda: client.classify_alert(classify_req).model_dump(mode="json"),
        verbose=verbose,
    )
    route_res = _safe_call(
        "route_analysis",
        lambda: heavy_client.route_analysis(route_req).model_dump(mode="json"),
        verbose=verbose,
    )
    agent_res = _safe_call(
        "run_agent_triage",
        lambda: heavy_client.run_agent_triage(agent_req).model_dump(mode="json"),
        verbose=verbose,
    )
    spl_res = _safe_call(
        "suggest_spl",
        lambda: client.suggest_spl(spl_req).model_dump(mode="json"),
        verbose=verbose,
    )
    eval_report = _run_eval_matrix(heavy_client, eval_matrix, verbose=verbose)
    mcp_status = _safe_call("mcp_status", client.mcp_status, verbose=verbose)

    forge_not_requested = {
        "error": "not_requested",
        "message": "Pass --forge-source-record-id and --forge-target-record-id to capture live Forge evidence.",
    }
    forge_source: Dict[str, Any] = dict(forge_not_requested)
    forge_compile: Dict[str, Any] = dict(forge_not_requested)
    forge_approval: Dict[str, Any] = dict(forge_not_requested)
    forge_run: Dict[str, Any] = dict(forge_not_requested)
    if args.forge_source_record_id is not None and args.forge_target_record_id is not None:
        if not 5 <= args.forge_manual_minutes <= 120:
            parser.error("--forge-manual-minutes must be between 5 and 120")
        forge_source = _safe_call(
            "forge_source_record",
            lambda: client.get_event(args.forge_source_record_id),
            verbose=verbose,
        )
        forge_compile = _safe_call(
            "forge_compile",
            lambda: heavy_client.build_verified_runbook(
                args.forge_source_record_id
            ).model_dump(mode="json"),
            verbose=verbose,
        )
        runbook_id = forge_compile.get("runbook_id")
        if runbook_id:
            forge_approval = _safe_call(
                "forge_approval",
                lambda: client.decide_verified_runbook(
                    args.forge_source_record_id,
                    {
                        "runbook_id": runbook_id,
                        "decision": "approve",
                        "note": "Evidence-pack run: queries and stop conditions reviewed",
                    },
                ).model_dump(mode="json"),
                verbose=verbose,
            )
            if forge_approval.get("decision") == "approve":
                forge_run = _safe_call(
                    "forge_target_run",
                    lambda: heavy_client.run_verified_runbook(
                        args.forge_target_record_id,
                        {
                            "source_record_id": args.forge_source_record_id,
                            "runbook_id": runbook_id,
                            "estimated_manual_minutes": args.forge_manual_minutes,
                        },
                    ).model_dump(mode="json"),
                    verbose=verbose,
                )
        else:
            forge_approval = {
                "error": "dependency_failed",
                "message": "Forge compilation did not return a runbook_id.",
            }
            forge_run = {
                "error": "dependency_failed",
                "message": "Forge approval was not available.",
            }

    forge_results = forge_run.get("results") if isinstance(forge_run.get("results"), list) else []
    forge_metrics = {
        "configured_model": forge_compile.get("configured_model"),
        "provider_reported_model": forge_compile.get("model"),
        "source_status": forge_compile.get("status"),
        "approval": forge_approval.get("decision"),
        "target_status": forge_run.get("status"),
        "step_count": len(forge_compile.get("steps") or []),
        "generation_duration_ms": forge_compile.get("generation_duration_ms"),
        "source_verification_duration_ms": forge_compile.get(
            "verification_duration_ms"
        ),
        "parser_valid_step_count": forge_compile.get("parser_valid_step_count"),
        "source_evidence_rows": forge_compile.get("total_evidence_rows"),
        "successful_step_count": sum(
            1
            for item in forge_results
            if isinstance(item, dict)
            and isinstance(item.get("spl_results"), dict)
            and not item["spl_results"].get("error")
            and int(item["spl_results"].get("row_count") or 0) > 0
        ),
        "manual_baseline_minutes": forge_run.get(
            "estimated_manual_minutes", args.forge_manual_minutes
        ),
        "automated_minutes": round(float(forge_run.get("duration_ms") or 0) / 60_000, 3),
        "estimated_minutes_saved": forge_run.get("estimated_minutes_saved"),
        "savings_percent": forge_run.get("savings_percent"),
        "target_evidence_rows": forge_run.get("total_evidence_rows"),
    }
    if forge_compile.get("error"):
        forge_metrics["error"] = forge_compile.get("error")

    output_files = [
        ("00_evidence_summary.md", None),
        ("01_classification_response.json", classify_res),
        ("02_route_response.json", route_res),
        ("03_agent_triage_response.json", agent_res),
        ("04_assistant_spl_response.json", spl_res),
        ("05_eval_report.json", eval_report),
        ("06_mcp_status.json", mcp_status),
        ("07_forge_source_record.json", forge_source),
        ("08_forge_compile.json", forge_compile),
        ("09_forge_approval.json", forge_approval),
        ("10_forge_target_run.json", forge_run),
        ("11_forge_metrics.json", forge_metrics),
    ]

    _vlog(verbose, "[write] output files")
    summary = _summary_md(eval_report)
    (out_dir / "00_evidence_summary.md").write_text(summary, encoding="utf-8")
    for filename, payload in output_files[1:]:
        _write_json(out_dir / filename, payload)
        _vlog(verbose, "[write] {0}".format(filename))

    manifest = {
        "generated_at_utc": run_id,
        "base_url": args.base_url,
        "files": [name for name, _ in output_files] + ["manifest.json"],
    }
    _write_json(out_dir / "manifest.json", manifest)
    _vlog(verbose, "[write] manifest.json")

    api_errors = _count_errors(
        classify_res,
        route_res,
        agent_res,
        spl_res,
        mcp_status,
        *(
            (forge_source, forge_compile, forge_approval, forge_run)
            if args.forge_source_record_id is not None
            else ()
        ),
    )

    print("Evidence pack generated: {0}".format(out_dir))
    print(
        "Summary: eval {0}/{1} ({2}%) | api_errors={3}".format(
            eval_report.get("total_score"),
            eval_report.get("max_score"),
            eval_report.get("score_percent"),
            api_errors,
        )
    )
    if api_errors:
        print("Warning: {0} API call(s) returned error payloads (see JSON files)".format(api_errors), file=sys.stderr)
    _vlog(verbose, "=== done ===")


if __name__ == "__main__":
    main()
