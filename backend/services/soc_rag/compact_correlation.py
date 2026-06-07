"""Compact RAG documents from graph correlation (findings + Neo4j alerts)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .models import RagAlertDocument

DOC_TYPE_FINDING = "correlation_finding"
DOC_TYPE_ALERT = "correlation_alert"
DOC_TYPE_PATH = "correlation_attack_path"


def _lines(parts: List[str]) -> str:
    return "\n".join(p for p in parts if p)


def compact_finding_document(
    *,
    finding_id: str,
    display_id: str,
    finding_type: str,
    title: str,
    summary: str,
    risk_score: int,
    ticket_status: str,
    owner: str,
    details: Optional[Dict[str, Any]] = None,
) -> RagAlertDocument:
    det = details if isinstance(details, dict) else {}
    contributing = det.get("contributing_alerts") or []
    entities = det.get("key_entities") or {}
    incident_id = str(det.get("incident_id") or "")
    exec_summary = str(det.get("executive_summary") or summary or "")
    steps = det.get("attack_analysis_steps") or []
    historical = det.get("historical_related_incidents") or []
    next_steps = det.get("recommended_next_steps") or []

    alert_lines: List[str] = []
    for a in contributing[:20]:
        if not isinstance(a, dict):
            continue
        alert_lines.append(
            "- {name} id={id} sid={sid} risk={risk} status={status} time={ts}".format(
                name=a.get("alert_name") or a.get("search_name") or "?",
                id=a.get("alert_row_id") or "?",
                sid=a.get("sid") or "-",
                risk=a.get("risk_score") or "?",
                status=a.get("threat_status") or a.get("status") or "?",
                ts=a.get("timestamp") or "?",
            )
        )

    entity_lines: List[str] = []
    for kind in ("identities", "assets", "iocs"):
        vals = entities.get(kind) if isinstance(entities, dict) else None
        if vals:
            entity_lines.append("{0}: {1}".format(kind, ", ".join(str(v) for v in vals[:12])))

    narrative_lines: List[str] = []
    for i, s in enumerate(steps[:12]):
        if not isinstance(s, dict):
            continue
        desc = str(s.get("description") or "").strip()
        phase = str(s.get("phase_label") or "Step").strip()
        if not desc and not phase:
            continue
        narrative_lines.append(
            "Step {n}: [{phase}] {desc}".format(n=i + 1, phase=phase, desc=desc[:500])
        )

    chunk = _lines(
        [
            "Graph correlation finding ({0})".format(finding_type),
            "Finding id={0} display_id={1} risk_score={2} ticket={3} owner={4}".format(
                finding_id,
                display_id,
                risk_score,
                ticket_status,
                owner,
            ),
            "Title: {0}".format(title),
            "Summary: {0}".format(summary),
            "Incident: {0}".format(incident_id or "(none)"),
            "Executive summary: {0}".format(exec_summary[:2000]),
            "Contributing alerts ({0}):".format(len(contributing)) if contributing else "",
            *alert_lines,
            "Key entities:" if entity_lines else "",
            *entity_lines,
            "Attack narrative (numbered steps):" if narrative_lines else "",
            *narrative_lines,
            "Historical related incidents: {0}".format(
                json.dumps(historical[:5], ensure_ascii=False)[:800]
            )
            if historical
            else "",
            "Recommended next steps: {0}".format("; ".join(str(s) for s in next_steps[:6]))
            if next_steps
            else "",
        ]
    )

    summary_line = "{0} (risk {1}, {2} alerts)".format(
        title[:80],
        risk_score,
        len(contributing),
    )
    return RagAlertDocument(
        doc_type=DOC_TYPE_FINDING,
        doc_id="corr-finding:{0}".format(finding_id),
        sid=incident_id or None,
        search_name=display_id or title[:120],
        essential={
            "finding_id": finding_id,
            "finding_type": finding_type,
            "risk_score": risk_score,
            "ticket_status": ticket_status,
            "alert_count": len(contributing),
        },
        summary_line=summary_line,
        chunk_text=chunk,
        metadata={
            "finding_id": finding_id,
            "display_id": display_id,
            "finding_type": finding_type,
            "incident_id": incident_id,
        },
    )


def compact_graph_alert_document(
    *,
    alert_row_id: str,
    props: Dict[str, Any],
    related_entities: Optional[List[str]] = None,
) -> RagAlertDocument:
    name = str(props.get("name") or props.get("search_name") or alert_row_id)
    sid = str(props.get("sid") or "").strip() or None
    search_name = str(props.get("search_name") or name)
    risk = int(props.get("risk_score") or 0)
    status = str(props.get("status") or "open")
    ts = str(props.get("timestamp") or "")
    entities = [str(e) for e in (related_entities or []) if e]

    chunk = _lines(
        [
            "Graph correlation alert node",
            "alert_row_id={0} name={1} sid={2} search_name={3}".format(
                alert_row_id,
                name,
                sid or "-",
                search_name,
            ),
            "risk_score={0} status={1} timestamp={2}".format(risk, status, ts or "-"),
            "Related entities: {0}".format(", ".join(entities[:24])) if entities else "Related entities: (none)",
        ]
    )
    return RagAlertDocument(
        doc_type=DOC_TYPE_ALERT,
        doc_id="corr-alert:{0}".format(alert_row_id),
        sid=sid,
        search_name=search_name,
        essential={
            "alert_row_id": alert_row_id,
            "risk_score": risk,
            "status": status,
            "_time": ts,
        },
        summary_line="Alert {0} (risk {1})".format(name[:60], risk),
        chunk_text=chunk,
        metadata={"alert_row_id": alert_row_id},
    )


def compact_attack_path_document(
    *,
    from_alert_id: str,
    to_alert_id: str,
    narrative: Optional[str] = None,
    time_delta_seconds: Optional[int] = None,
) -> RagAlertDocument:
    doc_id = "corr-path:{0}->{1}".format(from_alert_id, to_alert_id)
    chunk = _lines(
        [
            "Graph correlation attack path (CAUSED edge)",
            "from_alert={0} to_alert={1}".format(from_alert_id, to_alert_id),
            "time_delta_seconds={0}".format(time_delta_seconds) if time_delta_seconds is not None else "",
            "narrative: {0}".format((narrative or "Correlated sequence")[:1000]),
        ]
    )
    return RagAlertDocument(
        doc_type=DOC_TYPE_PATH,
        doc_id=doc_id,
        sid=None,
        search_name=from_alert_id,
        essential={
            "from_alert_row_id": from_alert_id,
            "to_alert_row_id": to_alert_id,
            "time_delta_seconds": time_delta_seconds,
        },
        summary_line="Attack path {0} → {1}".format(from_alert_id[:40], to_alert_id[:40]),
        chunk_text=chunk,
        metadata={"from_alert_row_id": from_alert_id, "to_alert_row_id": to_alert_id},
    )
