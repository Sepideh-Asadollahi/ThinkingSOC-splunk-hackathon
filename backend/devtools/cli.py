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


def _print_json(obj: Any) -> None:
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump(mode="json")
    elif isinstance(obj, list) and obj and hasattr(obj[0], "model_dump"):
        obj = [item.model_dump(mode="json") for item in obj]
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="ThinkingSOC Lite backend developer tools CLI")
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

    p_ingest = sub.add_parser("ingest", help="POST /api/v1/alerts/splunk-ingest (Splunk webhook)")
    p_ingest.add_argument("--body", required=True, help="Path to JSON body file")

    sub.add_parser("mcp-status", help="GET /api/v1/mcp/status (Splunk MCP Server)")

    p_mcp_gen = sub.add_parser("mcp-generate", help="POST /api/v1/mcp/spl-generate (SAIA NL→SPL)")
    p_mcp_gen.add_argument("--body", required=True, help="Path to JSON body file")

    p_mcp_tool = sub.add_parser("mcp-tool", help="POST /api/v1/mcp/tools/call (raw MCP tool)")
    p_mcp_tool.add_argument("--body", required=True, help="Path to JSON body file")

    p_mcp_query = sub.add_parser("mcp-query", help="Run SPL via splunk_run_query MCP tool")
    p_mcp_query.add_argument("--spl", required=True, help="SPL search string")

    p_mcp_ask = sub.add_parser("mcp-ask", help="Ask Splunk SAIA via saia_ask_splunk_question")
    p_mcp_ask.add_argument("--question", required=True, help="Natural language question")
    p_mcp_ask.add_argument("--context", default=None, help="Optional additional context")

    p_run = sub.add_parser("run-analysis", help="POST /api/v1/analysis/run (SOC security pipeline)")
    p_run.add_argument("--body", required=True, help="Path to JSON body file")

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

    sub.add_parser("llm-status", help="GET /api/v1/llm/status (LiteLLM configuration)")

    sub.add_parser("doctor", help="Connectivity check: health + MCP + LLM + SOC chat")

    p_investigate = sub.add_parser("investigate", help="Full chain: classify → triage → SPL → MCP status")
    p_investigate.add_argument("--body", required=True, help="Path to JSON body file (agent triage shape)")

    p_timeline = sub.add_parser("timeline", help="GET /api/v1/investigation/records/{id}/timeline")
    p_timeline.add_argument("--record-id", required=True, type=int, help="PostgreSQL record ID")

    p_actions = sub.add_parser("analyst-actions", help="GET analyst action log for a record")
    p_actions.add_argument("--record-id", required=True, type=int, help="PostgreSQL record ID")

    p_action_add = sub.add_parser("analyst-action-add", help="POST analyst action (acknowledge/escalate)")
    p_action_add.add_argument("--record-id", required=True, type=int, help="PostgreSQL record ID")
    p_action_add.add_argument("--body", required=True, help="Path to JSON body file")

    p_search = sub.add_parser("search-events", help="GET /api/v1/storage/events")
    p_search.add_argument("--sid", default=None)
    p_search.add_argument("--record-type", default=None)
    p_search.add_argument("--limit", type=int, default=None)

    p_get = sub.add_parser("get-event", help="GET /api/v1/storage/events/{id}")
    p_get.add_argument("--record-id", required=True, type=int, help="PostgreSQL record ID")

    p_triage = sub.add_parser("triage", help="GET /api/v1/triage/queue (priority-sorted analyst queue)")
    p_triage.add_argument("--track", default=None, choices=["all", "security", "observability"], help="Filter by track")
    p_triage.add_argument("--limit", type=int, default=None, help="Max results")

    sub.add_parser("health", help="GET /api/v1/health (liveness check)")

    p_gap = sub.add_parser("gap-suggest", help="POST /api/v1/admin-org/gap-suggest")
    p_gap.add_argument("--body", required=True)

    sub.add_parser("inventory-status")
    sub.add_parser("inventory-users")
    p_inv_user = sub.add_parser("inventory-user-get")
    p_inv_user.add_argument("--user-id", required=True)
    p_inv_user_c = sub.add_parser("inventory-user-create")
    p_inv_user_c.add_argument("--body", required=True)
    p_inv_user_u = sub.add_parser("inventory-user-update")
    p_inv_user_u.add_argument("--user-id", required=True)
    p_inv_user_u.add_argument("--body", required=True)
    p_inv_user_d = sub.add_parser("inventory-user-delete")
    p_inv_user_d.add_argument("--user-id", required=True)

    sub.add_parser("inventory-assets")
    p_inv_asset = sub.add_parser("inventory-asset-get")
    p_inv_asset.add_argument("--asset-id", required=True)
    p_inv_asset_c = sub.add_parser("inventory-asset-create")
    p_inv_asset_c.add_argument("--body", required=True)
    p_inv_asset_u = sub.add_parser("inventory-asset-update")
    p_inv_asset_u.add_argument("--asset-id", required=True)
    p_inv_asset_u.add_argument("--body", required=True)
    p_inv_asset_d = sub.add_parser("inventory-asset-delete")
    p_inv_asset_d.add_argument("--asset-id", required=True)

    sub.add_parser("inventory-relationships")
    p_inv_rel = sub.add_parser("inventory-relationship-get")
    p_inv_rel.add_argument("--relationship-id", required=True)
    p_inv_rel_c = sub.add_parser("inventory-relationship-create")
    p_inv_rel_c.add_argument("--body", required=True)
    p_inv_rel_u = sub.add_parser("inventory-relationship-update")
    p_inv_rel_u.add_argument("--relationship-id", required=True)
    p_inv_rel_u.add_argument("--body", required=True)
    p_inv_rel_d = sub.add_parser("inventory-relationship-delete")
    p_inv_rel_d.add_argument("--relationship-id", required=True)

    p_inv_enrich = sub.add_parser("inventory-enrich")
    p_inv_enrich.add_argument("--body", required=True)

    sub.add_parser("integrations-list")
    p_int_get = sub.add_parser("integration-get")
    p_int_get.add_argument("--setting-id", required=True)
    p_int_c = sub.add_parser("integration-create")
    p_int_c.add_argument("--body", required=True)
    p_int_u = sub.add_parser("integration-update")
    p_int_u.add_argument("--setting-id", required=True)
    p_int_u.add_argument("--body", required=True)
    p_int_d = sub.add_parser("integration-delete")
    p_int_d.add_argument("--setting-id", required=True)

    sub.add_parser("graph-health")
    p_graph_find = sub.add_parser("graph-findings")
    p_graph_find.add_argument("--limit", type=int, default=None)
    p_graph_find.add_argument("--offset", type=int, default=None)
    p_graph_get = sub.add_parser("graph-finding")
    p_graph_get.add_argument("--finding-id", required=True)
    p_graph_data = sub.add_parser("graph-finding-data")
    p_graph_data.add_argument("--finding-id", required=True)
    p_graph_topo = sub.add_parser("graph-topology")
    p_graph_topo.add_argument("--identifier", required=True)
    p_graph_tree = sub.add_parser("graph-attack-tree")
    p_graph_tree.add_argument("--identifier", required=True)
    p_graph_disc = sub.add_parser("graph-discover")
    p_graph_disc.add_argument("--body", default=None, help="Optional JSON body file")
    p_graph_op = sub.add_parser("graph-operation")
    p_graph_op.add_argument("--operation-id", required=True)

    sub.add_parser("chat-conversations")
    p_chat_create = sub.add_parser("chat-conversation-create")
    p_chat_create.add_argument("--title", default=None)
    p_chat_get = sub.add_parser("chat-conversation-get")
    p_chat_get.add_argument("--conversation-id", required=True)
    p_chat_del = sub.add_parser("chat-conversation-delete")
    p_chat_del.add_argument("--conversation-id", required=True)

    args = parser.parse_args()
    token = args.token or os.environ.get("TSOC_INGEST_TOKEN")
    client = TsocSdkClient(
        base_url=args.base_url,
        ingest_token=token,
        timeout_seconds=args.timeout,
        max_retries=args.retries,
    )

    try:
        cmd = args.command
        if cmd == "mcp-status":
            _print_json(client.mcp_status())
            return
        if cmd == "dashboard":
            _print_json(client.dashboard_overview())
            return
        if cmd == "chat-status":
            _print_json(client.soc_chat_status())
            return
        if cmd == "llm-status":
            _print_json(client.llm_status())
            return
        if cmd == "doctor":
            _print_json(client.doctor())
            return
        if cmd == "health":
            _print_json(client.health())
            return
        if cmd == "timeline":
            _print_json(client.investigation_timeline(args.record_id))
            return
        if cmd == "analyst-actions":
            _print_json(client.analyst_actions(args.record_id))
            return
        if cmd == "search-events":
            _print_json(client.search_events(sid=args.sid, record_type=args.record_type, limit=args.limit))
            return
        if cmd == "get-event":
            _print_json(client.get_event(args.record_id))
            return
        if cmd == "triage":
            _print_json(client.triage_queue(track=args.track, limit=args.limit))
            return
        if cmd == "mcp-query":
            _print_json(client.mcp_run_query(args.spl).model_dump(mode="json"))
            return
        if cmd == "mcp-ask":
            _print_json(client.mcp_saia_ask(args.question, additional_context=args.context).model_dump(mode="json"))
            return
        if cmd == "analyst-action-add":
            _print_json(client.add_analyst_action(args.record_id, _load_json(args.body)))
            return
        if cmd == "investigate":
            _print_json(client.run_full_investigation(_load_json(args.body)))
            return
        if cmd == "inventory-status":
            _print_json(client.inventory_status())
            return
        if cmd == "inventory-users":
            _print_json(client.list_inventory_users())
            return
        if cmd == "inventory-user-get":
            _print_json(client.get_inventory_user(args.user_id))
            return
        if cmd == "inventory-user-delete":
            client.delete_inventory_user(args.user_id)
            _print_json({"ok": True, "user_id": args.user_id})
            return
        if cmd == "inventory-assets":
            _print_json(client.list_inventory_assets())
            return
        if cmd == "inventory-asset-get":
            _print_json(client.get_inventory_asset(args.asset_id))
            return
        if cmd == "inventory-asset-delete":
            client.delete_inventory_asset(args.asset_id)
            _print_json({"ok": True, "asset_id": args.asset_id})
            return
        if cmd == "inventory-relationships":
            _print_json(client.list_inventory_relationships())
            return
        if cmd == "inventory-relationship-get":
            _print_json(client.get_inventory_relationship(args.relationship_id))
            return
        if cmd == "inventory-relationship-delete":
            client.delete_inventory_relationship(args.relationship_id)
            _print_json({"ok": True, "relationship_id": args.relationship_id})
            return
        if cmd == "integrations-list":
            _print_json(client.list_integrations())
            return
        if cmd == "integration-get":
            _print_json(client.get_integration(args.setting_id))
            return
        if cmd == "integration-delete":
            client.delete_integration(args.setting_id)
            _print_json({"ok": True, "setting_id": args.setting_id})
            return
        if cmd == "graph-health":
            _print_json(client.graph_health())
            return
        if cmd == "graph-findings":
            _print_json(client.graph_findings(limit=args.limit, offset=args.offset))
            return
        if cmd == "graph-finding":
            _print_json(client.graph_get_finding(args.finding_id))
            return
        if cmd == "graph-finding-data":
            _print_json(client.graph_finding_graph_data(args.finding_id))
            return
        if cmd == "graph-topology":
            _print_json(client.graph_topology(args.identifier))
            return
        if cmd == "graph-attack-tree":
            _print_json(client.graph_attack_tree(args.identifier))
            return
        if cmd == "graph-discover":
            body = _load_json(args.body) if args.body else {}
            _print_json(client.graph_discover_attack_paths(body))
            return
        if cmd == "graph-operation":
            _print_json(client.graph_operation_status(args.operation_id))
            return
        if cmd == "chat-conversations":
            _print_json(client.list_soc_chat_conversations())
            return
        if cmd == "chat-conversation-create":
            _print_json(client.create_soc_chat_conversation({"title": args.title} if args.title else {}))
            return
        if cmd == "chat-conversation-get":
            _print_json(client.get_soc_chat_conversation(args.conversation_id))
            return
        if cmd == "chat-conversation-delete":
            _print_json(client.delete_soc_chat_conversation(args.conversation_id))
            return

        body = _load_json(args.body)
        if cmd == "classify":
            out = client.classify_alert(body)
        elif cmd == "route":
            out = client.route_analysis(body)
        elif cmd == "agent":
            out = client.run_agent_triage(body)
        elif cmd == "ingest":
            _print_json(client.ingest_alert(body))
            return
        elif cmd == "mcp-generate":
            out = client.mcp_generate_spl(body)
        elif cmd == "mcp-tool":
            out = client.mcp_call_tool(body)
        elif cmd == "run-analysis":
            out = client.run_analysis(body)
        elif cmd == "run-by-sid":
            out = client.run_analysis_by_sid(body)
        elif cmd == "obs-run":
            out = client.run_observability(body)
        elif cmd == "obs-by-sid":
            out = client.run_observability_by_sid(body)
        elif cmd == "soc-chat":
            out = client.soc_chat(body)
        elif cmd == "gap-suggest":
            out = client.gap_suggest(body)
        elif cmd == "inventory-user-create":
            out = client.create_inventory_user(body)
        elif cmd == "inventory-user-update":
            out = client.update_inventory_user(args.user_id, body)
        elif cmd == "inventory-asset-create":
            out = client.create_inventory_asset(body)
        elif cmd == "inventory-asset-update":
            out = client.update_inventory_asset(args.asset_id, body)
        elif cmd == "inventory-relationship-create":
            out = client.create_inventory_relationship(body)
        elif cmd == "inventory-relationship-update":
            out = client.update_inventory_relationship(args.relationship_id, body)
        elif cmd == "inventory-enrich":
            out = client.enrich_inventory(body)
        elif cmd == "integration-create":
            out = client.create_integration(body)
        elif cmd == "integration-update":
            out = client.update_integration(args.setting_id, body)
        else:
            out = client.suggest_spl(body)
        _print_json(out)
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


if __name__ == "__main__":
    main()
