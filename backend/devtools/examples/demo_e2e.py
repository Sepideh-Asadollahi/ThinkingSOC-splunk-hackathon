#!/usr/bin/env python3
"""End-to-end SDK demo: alert → classify → triage → investigate → chat.

Demonstrates the full ThinkingSOC Lite pipeline using the Developer SDK,
including Splunk MCP integration, exclusive single-track analysis, investigation
timeline, and RAG-powered SOC chat.

Usage:
    cd backend
    python devtools/examples/demo_e2e.py [--base-url http://127.0.0.1:9876]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from devtools import TsocSdkClient


def _pp(label: str, obj: object) -> None:
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump(mode="json")
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(json.dumps(obj, ensure_ascii=False, indent=2)[:2000])


def main() -> None:
    parser = argparse.ArgumentParser(description="ThinkingSOC Lite end-to-end SDK demo")
    parser.add_argument("--base-url", default="http://127.0.0.1:9876")
    parser.add_argument("--token", default=None)
    args = parser.parse_args()

    client = TsocSdkClient(
        base_url=args.base_url,
        ingest_token=args.token or os.environ.get("TSOC_INGEST_TOKEN"),
    )

    # ── Step 0: Health & connectivity ──
    print("\n[Step 0] Health & connectivity checks")
    _pp("Doctor (full connectivity)", client.doctor())
    _pp("LLM status", client.llm_status())

    alert = {
        "normalized": {
            "host": "web-prod-01",
            "user": "jdoe",
            "src": "1.2.3.4",
            "dest": "10.0.0.10",
            "action": "failure",
        },
        "search_name": "Suspicious auth failed login alert",
    }
    users = [{"user_id": "jdoe", "risk_score": "3", "department": "IT"}]
    assets = [{"asset_id": "srv-web-01", "hostname": "web-prod-01", "criticality": "high"}]

    # ── Step 1: Classify the alert ──
    print("\n[Step 1] Classify alert")
    cls = client.classify_alert(alert)
    _pp("Classification", cls)
    print(f"\n  → Track: {cls.track}  Confidence: {cls.confidence}")

    # ── Step 2: Full agent triage (or chained investigate) ──
    print("\n[Step 2] Full investigation chain (classify → triage → SPL → MCP)")
    investigation = client.run_full_investigation({
        **alert,
        "operator_goal": "confirm lateral movement path",
        "users": users,
        "assets": assets,
    })
    _pp("Full investigation", investigation)
    triage_summary = (investigation.get("triage") or {}).get("agent_summary") or ""
    print(f"\n  → Summary: {triage_summary[:200]}")
    print(f"  → MCP connected: {(investigation.get('mcp_status') or {}).get('connected')}")

    # ── Step 3: SPL suggestion (standalone) ──
    print("\n[Step 3] SPL suggestion for investigation")
    spl = client.suggest_spl({
        **alert,
        "objective": "collect root cause timeline",
    })
    _pp("SPL suggestion", spl)
    print(f"\n  → Source: {spl.source}")
    if spl.root_cause_spl:
        print(f"  → SPL: {spl.root_cause_spl.spl[:200]}")

    # ── Step 4: MCP SPL generation & SAIA ask ──
    print("\n[Step 4] Splunk MCP SAIA — natural language → SPL")
    try:
        mcp_spl = client.mcp_generate_spl({
            "query": "Show failed login attempts for user jdoe in the last 24 hours",
            "index": "main",
        })
        _pp("MCP SPL generation", mcp_spl)
        saia = client.mcp_saia_ask(
            "What indexes contain authentication events?",
            additional_context="Alert user=jdoe host=web-prod-01",
        )
        _pp("MCP SAIA ask", saia.model_dump(mode="json"))
    except Exception as e:
        print(f"  → MCP unavailable: {e}")

    # ── Step 5: Dashboard overview ──
    print("\n[Step 5] Dashboard overview")
    dash = client.dashboard_overview()
    _pp("Dashboard", dash)
    print(f"\n  → Health: {dash.kpis.health_score}%  Total records: {dash.kpis.total_records}")

    # ── Step 6: Triage queue ──
    print("\n[Step 6] Triage queue (priority-sorted)")
    queue = client.triage_queue(track="security", limit=5)
    _pp("Triage queue", queue)
    print(f"\n  → {queue.get('count', 0)} items in security queue")

    # ── Step 7: SOC Chat ──
    print("\n[Step 7] SOC Chat — ask about recent alerts")
    try:
        chat = client.soc_chat({
            "messages": [
                {"role": "user", "content": "What are the most critical security findings in the last 24 hours?"},
            ],
        })
        _pp("SOC chat answer", chat)
        print(f"\n  → Backend: {chat.retrieval_backend}  Citations: {len(chat.citations)}")
        print(f"  → Answer: {(chat.answer or '')[:300]}")
    except Exception as e:
        print(f"  → SOC chat unavailable: {e}")

    print(f"\n{'='*60}")
    print("  Demo complete — all SDK methods exercised")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
