#!/usr/bin/env python3
"""Developer CLI for quick endpoint checks (classification/agent/assistant)."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict

from devtools import TsocApiError, TsocAuthError, TsocNotFoundError, TsocSdkClient, TsocTimeoutError


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="ThinkingSOC backend developer tools CLI")
    parser.add_argument("--base-url", default="http://127.0.0.1:9876")
    parser.add_argument("--token", default=None, help="Bearer token. Defaults to TSOC_INGEST_TOKEN if unset.")
    parser.add_argument("--timeout", type=float, default=120.0, help="HTTP timeout in seconds.")
    parser.add_argument("--retries", type=int, default=2, help="Retry count for 5xx/timeout errors.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_cls = sub.add_parser("classify")
    p_cls.add_argument("--body", required=True, help="Path to JSON body file")

    p_route = sub.add_parser("route")
    p_route.add_argument("--body", required=True, help="Path to JSON body file")

    p_agent = sub.add_parser("agent")
    p_agent.add_argument("--body", required=True, help="Path to JSON body file")

    p_spl = sub.add_parser("spl")
    p_spl.add_argument("--body", required=True, help="Path to JSON body file")

    sub.add_parser("mcp-status", help="GET /api/v1/mcp/status (Splunk MCP Server)")

    p_mcp_gen = sub.add_parser("mcp-generate", help="POST /api/v1/mcp/spl-generate (SAIA NL→SPL)")
    p_mcp_gen.add_argument("--body", required=True, help="Path to JSON body file")

    p_mcp_tool = sub.add_parser("mcp-tool", help="POST /api/v1/mcp/tools/call (raw MCP tool)")
    p_mcp_tool.add_argument("--body", required=True, help="Path to JSON body file")

    p_bysid = sub.add_parser("run-by-sid", help="POST /api/v1/analysis/run-by-sid (batch by Splunk SID)")
    p_bysid.add_argument("--body", required=True, help="Path to JSON body file")

    sub.add_parser("dashboard", help="GET /api/v1/dashboard/overview (SOC dashboard)")

    p_obs = sub.add_parser("obs-run", help="POST /api/v1/observability/run (Diagnoser+Responder+OpsJudge)")
    p_obs.add_argument("--body", required=True, help="Path to JSON body file")

    p_obs_sid = sub.add_parser("obs-by-sid", help="POST /api/v1/observability/run-by-sid (batch by SID)")
    p_obs_sid.add_argument("--body", required=True, help="Path to JSON body file")

    p_chat = sub.add_parser("soc-chat", help="POST /api/v1/soc/chat (RAG investigation chat)")
    p_chat.add_argument("--body", required=True, help="Path to JSON body file")

    sub.add_parser("chat-status", help="GET /api/v1/soc/chat/status (RAG backend status)")

    p_timeline = sub.add_parser("timeline", help="GET /api/v1/investigation/records/{id}/timeline")
    p_timeline.add_argument("--record-id", required=True, type=int, help="PostgreSQL record ID")

    p_triage = sub.add_parser("triage", help="GET /api/v1/triage/queue (priority-sorted analyst queue)")
    p_triage.add_argument("--track", default=None, choices=["all", "security", "observability"], help="Filter by track")
    p_triage.add_argument("--limit", type=int, default=None, help="Max results")

    sub.add_parser("health", help="GET /api/v1/health (liveness check)")

    args = parser.parse_args()
    token = args.token or os.environ.get("TSOC_INGEST_TOKEN")
    client = TsocSdkClient(
        base_url=args.base_url,
        ingest_token=token,
        timeout_seconds=args.timeout,
        max_retries=args.retries,
    )

    try:
        if args.command == "mcp-status":
            print(json.dumps(client.mcp_status(), ensure_ascii=False, indent=2))
            return
        if args.command == "dashboard":
            print(json.dumps(client.dashboard_overview().model_dump(mode="json"), ensure_ascii=False, indent=2))
            return
        if args.command == "chat-status":
            print(json.dumps(client.soc_chat_status(), ensure_ascii=False, indent=2))
            return
        if args.command == "health":
            print(json.dumps(client.health(), ensure_ascii=False, indent=2))
            return
        if args.command == "timeline":
            print(json.dumps(client.investigation_timeline(args.record_id), ensure_ascii=False, indent=2))
            return
        if args.command == "triage":
            print(json.dumps(client.triage_queue(track=args.track, limit=args.limit), ensure_ascii=False, indent=2))
            return
        body = _load_json(args.body)
        if args.command == "classify":
            out = client.classify_alert(body).model_dump(mode="json")
        elif args.command == "route":
            out = client.route_analysis(body).model_dump(mode="json")
        elif args.command == "agent":
            out = client.run_agent_triage(body).model_dump(mode="json")
        elif args.command == "mcp-generate":
            out = client.mcp_generate_spl(body).model_dump(mode="json")
        elif args.command == "mcp-tool":
            out = client.mcp_call_tool(body).model_dump(mode="json")
        elif args.command == "run-by-sid":
            out = client.run_analysis_by_sid(body).model_dump(mode="json")
        elif args.command == "obs-run":
            out = client.run_observability(body).model_dump(mode="json")
        elif args.command == "obs-by-sid":
            out = client.run_observability_by_sid(body).model_dump(mode="json")
        elif args.command == "soc-chat":
            out = client.soc_chat(body).model_dump(mode="json")
        else:
            out = client.suggest_spl(body).model_dump(mode="json")
    except TsocAuthError as e:
        raise SystemExit("Authentication failed: {0}".format(e)) from e
    except TsocNotFoundError as e:
        raise SystemExit("Endpoint not found: {0}".format(e)) from e
    except TsocTimeoutError as e:
        raise SystemExit("Request timeout: {0}".format(e)) from e
    except TsocApiError as e:
        raise SystemExit(
            "API error status={0} body={1}".format(e.status_code, (e.response_text or "")[:500])
        ) from e

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

