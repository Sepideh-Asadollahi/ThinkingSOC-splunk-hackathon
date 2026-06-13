"""Shared SDK workflow helpers (doctor, full investigation summaries)."""

from __future__ import annotations

from typing import Any, Dict, Optional


def build_doctor_report(
    *,
    health: Dict[str, Any],
    mcp_status: Dict[str, Any],
    llm_status: Dict[str, Any],
    soc_chat_status: Dict[str, Any],
    graph_health: Optional[Dict[str, Any]] = None,
    inventory_status: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Summarize connectivity checks for demo/CI readiness."""
    backend_ok = str(health.get("status") or "").lower() == "ok"
    mcp_connected = bool(mcp_status.get("connected"))
    mcp_configured = bool(mcp_status.get("configured", mcp_connected))
    saia_available = bool(mcp_status.get("saia_available"))
    llm_ok = bool(llm_status.get("litellm_model")) or bool(llm_status.get("litellm_api_key_configured"))
    chat_enabled = bool(soc_chat_status.get("enabled"))

    graph_ok = False
    if graph_health is not None:
        graph_ok = str(graph_health.get("status") or "").lower() == "ok"
    inventory_ok = False
    if inventory_status is not None:
        inventory_ok = bool(inventory_status.get("postgres_configured"))

    checks = {
        "backend": {"ok": backend_ok, "status": health.get("status")},
        "mcp": {
            "ok": mcp_configured and mcp_connected,
            "configured": mcp_configured,
            "connected": mcp_connected,
            "saia_available": saia_available,
        },
        "llm": {
            "ok": llm_ok,
            "model": llm_status.get("litellm_model"),
            "api_key_configured": llm_status.get("litellm_api_key_configured"),
        },
        "soc_chat": {
            "ok": chat_enabled,
            "enabled": chat_enabled,
            "document_count": soc_chat_status.get("document_count"),
        },
        "graph": {
            "ok": graph_ok,
            "neo4j": (graph_health or {}).get("neo4j"),
            "postgres": (graph_health or {}).get("postgres"),
        },
        "inventory": {
            "ok": inventory_ok,
            "postgres_configured": (inventory_status or {}).get("postgres_configured"),
            "source": (inventory_status or {}).get("source"),
        },
    }
    ready_for_demo = backend_ok and checks["mcp"]["ok"] and llm_ok
    raw: Dict[str, Any] = {
        "health": health,
        "mcp_status": mcp_status,
        "llm_status": llm_status,
        "soc_chat_status": soc_chat_status,
    }
    if graph_health is not None:
        raw["graph_health"] = graph_health
    if inventory_status is not None:
        raw["inventory_status"] = inventory_status
    return {
        "ok": backend_ok,
        "ready_for_demo": ready_for_demo,
        "checks": checks,
        "raw": raw,
    }


def build_full_investigation_result(
    *,
    classification: Any,
    triage: Any,
    spl: Any,
    mcp_status: Dict[str, Any],
) -> Dict[str, Any]:
    """Package chained investigation steps into one dict."""
    def _dump(obj: Any) -> Any:
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        return obj

    return {
        "classification": _dump(classification),
        "triage": _dump(triage),
        "spl": _dump(spl),
        "mcp_status": mcp_status,
    }
