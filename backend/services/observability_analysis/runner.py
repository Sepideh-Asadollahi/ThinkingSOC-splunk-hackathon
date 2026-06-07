"""Main observability analysis entrypoint."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config import Settings
from models.observability import ObservabilityAnalysisResult, ObservabilityRunRequest
from services.alert.enrichment_resolver import enrich_from_inventory
from services.soc_analysis.analysis_audit import (
    build_analysis_input,
    build_raw_alert,
    resolve_row_index,
)
from services.splunk_json_store import persist_observability_analysis_to_splunk

from .diagnoser import build_diagnoser
from .entity import build_entity_resolution
from .impact import build_impact_context
from .judge import build_ops_judge
from .llm import build_diagnoser_llm, build_ops_judge_llm, build_responder_llm
from services.triage.triage_priority import compute_triage_from_observability, merge_triage_into_analysis_output

from .responder import build_responder


def _build_evidence_refs(normalized: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for key in ("host", "service", "cpu", "memory", "disk", "latency_ms", "error_rate", "status_code", "severity"):
        val = normalized.get(key)
        if val is None or str(val).strip() == "":
            continue
        out.append("normalized.{0}={1}".format(key, val))
    return out


async def run_observability_analysis(
    settings: Settings,
    body: ObservabilityRunRequest,
    *,
    users: List[Dict[str, Any]],
    assets: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    analysis_row_index: Optional[int] = None,
) -> ObservabilityAnalysisResult:
    row_index = resolve_row_index(
        analysis_row_index if analysis_row_index is not None else body.row_index,
        body.splunk_results,
    )
    enrichment = body.enrichment
    if enrichment is None:
        enrichment = enrich_from_inventory(body.normalized, users, assets, relationships)

    entity, asset_row = build_entity_resolution(body.normalized, enrichment, assets)
    impact = build_impact_context(body.normalized, entity, asset_row)
    diagnoser = build_diagnoser(body.normalized)
    responder = build_responder(impact, diagnoser)
    ops_judge = build_ops_judge(impact, diagnoser, responder)

    llm_context_base = {
        "search_name": body.search_name,
        "sid": body.sid,
        "normalized": body.normalized,
        "splunk_results_preview": (body.splunk_results or [])[:5],
        "entity_resolution": entity.model_dump(mode="json"),
        "impact_context": impact.model_dump(mode="json"),
        "evidence_refs": _build_evidence_refs(body.normalized),
    }
    try:
        diagnoser = await build_diagnoser_llm(settings, llm_context_base)
        responder = await build_responder_llm(
            settings,
            {
                **llm_context_base,
                "diagnoser": diagnoser.model_dump(mode="json"),
            },
        )
        ops_judge = await build_ops_judge_llm(
            settings,
            {
                **llm_context_base,
                "diagnoser": diagnoser.model_dump(mode="json"),
                "responder": responder.model_dump(mode="json"),
            },
        )
    except Exception:
        # Fallback stays deterministic when LiteLLM is unavailable.
        diagnoser = build_diagnoser(body.normalized)
        responder = build_responder(impact, diagnoser)
        ops_judge = build_ops_judge(impact, diagnoser, responder)
    evidence_refs = _build_evidence_refs(body.normalized)

    summary = "Operational alert analyzed with impact level {0}: {1}".format(
        impact.impact_level,
        ops_judge.verdict,
    )
    result = ObservabilityAnalysisResult(
        summary=summary,
        entity_resolution=entity,
        impact_context=impact,
        diagnoser=diagnoser,
        responder=responder,
        ops_judge=ops_judge,
        evidence_refs=evidence_refs,
    )
    triage = compute_triage_from_observability(result)
    result = result.model_copy(update={"triage": triage})
    analysis_output = merge_triage_into_analysis_output(
        {
            "verdict": result.ops_judge.verdict,
            "priority": result.ops_judge.priority,
            "recommended_next_step": result.ops_judge.recommended_next_step,
            "confidence": result.ops_judge.confidence,
            "rationale": result.ops_judge.rationale,
            "summary": result.summary,
        },
        triage,
    )
    await persist_observability_analysis_to_splunk(
        settings,
        body,
        result,
        row_index=row_index,
        raw_alert=build_raw_alert(
            sid=body.sid,
            search_name=body.search_name,
            normalized=body.normalized,
            splunk_results=body.splunk_results,
            row_index=row_index,
        ),
        analysis_input=build_analysis_input(
            search_name=body.search_name,
            normalized=body.normalized,
            splunk_results=body.splunk_results,
            row_index=row_index,
        ),
        analysis_output=analysis_output,
    )
    from services.soc_rag.index_writer import upsert_observability_document

    await upsert_observability_document(
        settings,
        sid=body.sid,
        search_name=body.search_name,
        normalized=body.normalized,
        result=result,
        row_index=row_index,
    )
    return result
