"""
LangGraph pipeline: prepare → risk_engine → virustotal → Defender → Hunter → Judge → …

``prepare`` only assembles inventory + identity + alert into a sorted JSON canonical prefix with
empty risk (raw). ``risk_engine`` computes ``risk_context`` and rebuilds the canonical prefix so
downstream LLMs share the same enriched System Context.
"""

from __future__ import annotations

import logging
import time

from langgraph.graph import END, StateGraph

from config import Settings

from .constants import GRAPH_NODE_ORDER
from .nodes_canonical import make_prepare_node, make_risk_engine_node, make_virustotal_node
from .nodes_llm import make_llm_nodes_bundle
from .nodes_root_cause import make_root_cause_spl_node
from .state import SocAnalysisGraphState

logger = logging.getLogger(__name__)


def build_soc_analysis_graph(settings: Settings) -> StateGraph:
    """Return a StateGraph — call ``.compile()`` to get an executable graph."""
    llm = make_llm_nodes_bundle(settings)
    mt = llm["mt"]

    workflow: StateGraph = StateGraph(SocAnalysisGraphState)
    workflow.add_node("prepare", make_prepare_node(settings))
    workflow.add_node("risk_engine", make_risk_engine_node(settings))
    workflow.add_node("virustotal", make_virustotal_node(settings))
    workflow.add_node("defender", llm["defender"])
    workflow.add_node("hunter", llm["hunter"])
    workflow.add_node("judge", llm["judge"])
    workflow.add_node("framework_mapping", llm["framework_mapping"])
    workflow.add_node("investigation_questions", llm["investigation_questions"])
    workflow.add_node("root_cause_spl", make_root_cause_spl_node(settings, mt))

    workflow.set_entry_point("prepare")
    workflow.add_edge("prepare", "risk_engine")
    workflow.add_edge("risk_engine", "virustotal")
    workflow.add_edge("virustotal", "defender")
    workflow.add_edge("defender", "hunter")
    workflow.add_edge("hunter", "judge")
    workflow.add_edge("judge", "framework_mapping")
    workflow.add_edge("framework_mapping", "investigation_questions")
    workflow.add_edge("investigation_questions", "root_cause_spl")
    workflow.add_edge("root_cause_spl", END)

    return workflow


async def run_soc_analysis_langgraph(
    settings: Settings,
    initial: SocAnalysisGraphState,
) -> SocAnalysisGraphState:
    sid = initial.get("sid")
    search_name = initial.get("search_name")
    logger.info(
        "soc_langgraph start sid=%s search_name=%s expected_steps=%s",
        sid,
        search_name,
        GRAPH_NODE_ORDER,
    )
    t0 = time.perf_counter()
    g = build_soc_analysis_graph(settings).compile()
    out: SocAnalysisGraphState = await g.ainvoke(initial)
    logger.info(
        "soc_langgraph done sid=%s duration_ms=%.1f",
        sid,
        (time.perf_counter() - t0) * 1000.0,
    )
    return out
