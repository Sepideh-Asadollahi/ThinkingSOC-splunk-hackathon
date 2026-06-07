"""Graph nodes: canonical context, risk, and threat-intel (no LLM)."""

from __future__ import annotations

from typing import Any, Callable, Dict

from config import Settings
from models.enrichment import EnrichmentResult
from services.soc_analysis.soc_analysis_canonical import build_canonical_static_context
from services.soc_analysis.soc_analysis_risk import build_risk_context
from services.threat_intel.threat_intel_compact import compact_threat_intel_for_analysis
from services.threat_intel.virustotal import enrich_virustotal

from .state import SocAnalysisGraphState
from .step_logging import run_graph_step


def make_prepare_node(_settings: Settings) -> Callable[..., Any]:
    async def node_prepare(state: SocAnalysisGraphState) -> Dict[str, Any]:
        async def work() -> Dict[str, Any]:
            row_index = int(state.get("row_index") or 0)
            canon = build_canonical_static_context(
                normalized=state["normalized"],
                search_name=state.get("search_name"),
                sid=state.get("sid"),
                splunk_results_preview=state.get("splunk_results_preview") or [],
                enrichment=state["enrichment"],
                risk_context="",
                inventory_user=state.get("inventory_user"),
                inventory_asset=state.get("inventory_asset"),
                similar_alert_context=state.get("similar_alert_context"),
                row_index=row_index,
            )
            return {"canonical_prefix": canon}

        return await run_graph_step("prepare", state, work)

    return node_prepare


def make_risk_engine_node(_settings: Settings) -> Callable[..., Any]:
    async def node_risk_engine(state: SocAnalysisGraphState) -> Dict[str, Any]:
        async def work() -> Dict[str, Any]:
            ident = EnrichmentResult(**state["enrichment"])
            risk = build_risk_context(
                ident,
                state.get("inventory_user"),
                state.get("inventory_asset"),
            )
            row_index = int(state.get("row_index") or 0)
            canon = build_canonical_static_context(
                normalized=state["normalized"],
                search_name=state.get("search_name"),
                sid=state.get("sid"),
                splunk_results_preview=state.get("splunk_results_preview") or [],
                enrichment=state["enrichment"],
                risk_context=risk,
                inventory_user=state.get("inventory_user"),
                inventory_asset=state.get("inventory_asset"),
                similar_alert_context=state.get("similar_alert_context"),
                row_index=row_index,
            )
            return {"risk_context": risk, "canonical_prefix": canon}

        return await run_graph_step("risk_engine", state, work)

    return node_risk_engine


def make_virustotal_node(settings: Settings) -> Callable[..., Any]:
    async def node_virustotal(state: SocAnalysisGraphState) -> Dict[str, Any]:
        async def work() -> Dict[str, Any]:
            vt = await enrich_virustotal(
                settings,
                normalized=state["normalized"],
                splunk_results_preview=state.get("splunk_results_preview") or [],
            )
            row_index = int(state.get("row_index") or 0)
            compact_ti = compact_threat_intel_for_analysis({"virustotal": vt})
            canon = build_canonical_static_context(
                normalized=state["normalized"],
                search_name=state.get("search_name"),
                sid=state.get("sid"),
                splunk_results_preview=state.get("splunk_results_preview") or [],
                enrichment=state["enrichment"],
                risk_context=state.get("risk_context") or "",
                inventory_user=state.get("inventory_user"),
                inventory_asset=state.get("inventory_asset"),
                threat_intel=compact_ti,
                similar_alert_context=state.get("similar_alert_context"),
                row_index=row_index,
            )
            return {"threat_intel": compact_ti, "canonical_prefix": canon}

        return await run_graph_step("virustotal", state, work)

    return node_virustotal
