"""Compact observability analysis for SOC chat retrieval."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from models.observability import ObservabilityAnalysisResult

from .compact_alert import _build_chunk_text, _build_summary_line, extract_essential_fields, make_doc_id
from .models import RagAlertDocument


def compact_observability_from_payload(payload: Dict[str, Any]) -> Optional[RagAlertDocument]:
    sid = payload.get("sid")
    search_name = payload.get("search_name")
    row_index = int(payload.get("row_index") or 0)
    raw = payload.get("raw_alert") if isinstance(payload.get("raw_alert"), dict) else {}
    normalized = raw.get("normalized") if isinstance(raw.get("normalized"), dict) else {}
    if not normalized and isinstance(payload.get("normalized"), dict):
        normalized = payload["normalized"]
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    if not analysis:
        return None
    try:
        result = ObservabilityAnalysisResult.model_validate(analysis)
    except Exception:
        return None

    essential = extract_essential_fields(normalized or {})
    ops = result.ops_judge
    essential["verdict"] = str(getattr(ops, "verdict", "") or "")
    essential["priority"] = str(getattr(ops, "priority", "") or "")
    essential["track"] = "observability"

    hypo = ""
    if result.diagnoser and result.diagnoser.root_cause_hypotheses:
        hypo = result.diagnoser.root_cause_hypotheses[0].hypothesis
    actions = ", ".join((result.responder.recommended_actions or [])[:5]) if result.responder else ""
    extra = [
        "Track: observability",
        "Summary: {0}".format((result.summary or "")[:400]),
        "Root cause hypothesis: {0}".format(hypo[:500]),
        "Recommended actions: {0}".format(actions[:400]),
        "Ops verdict: {0} priority={1}".format(
            getattr(ops, "verdict", ""),
            getattr(ops, "priority", ""),
        ),
        "Ops next: {0}".format((getattr(ops, "recommended_next_step", "") or "")[:300]),
    ]
    if result.entity_resolution:
        extra.append(
            "Entity: {0}".format(json.dumps(result.entity_resolution.model_dump(mode="json"), default=str)[:400])
        )
    if result.impact_context:
        extra.append(
            "Impact: {0}".format(json.dumps(result.impact_context.model_dump(mode="json"), default=str)[:400])
        )
    if result.triage:
        extra.append("Triage score: {0}".format(result.triage.triage_score))

    summary_line = _build_summary_line(search_name, essential)
    if result.summary:
        summary_line = "{0} | {1}".format(summary_line, (result.summary or "")[:180])

    chunk_text = _build_chunk_text(
        doc_type="observability_analysis",
        sid=sid if isinstance(sid, str) else None,
        search_name=search_name if isinstance(search_name, str) else None,
        essential=essential,
        extra_lines=extra,
    )
    doc_id = make_doc_id(sid, row_index, "observability_analysis")
    return RagAlertDocument(
        doc_type="observability_analysis",
        doc_id=doc_id,
        sid=sid if isinstance(sid, str) else None,
        search_name=search_name if isinstance(search_name, str) else None,
        row_index=row_index,
        essential=essential,
        summary_line=summary_line,
        chunk_text=chunk_text,
        metadata={
            "doc_type": "observability_analysis",
            "sid": sid,
            "search_name": search_name,
            "row_index": row_index,
            "track": "observability",
            **essential,
        },
    )
