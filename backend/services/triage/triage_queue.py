"""Shared Analysis page queue — same logic as GET /api/v1/triage/queue."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional

from config import Settings
from models.triage import TriageOutcome
from services.splunk_json_store import search_stored_events
from services.triage.triage_priority import triage_from_stored_payload

TrackFilter = Literal["security", "observability", "all"]

_INDEXED_RE = re.compile(r"(?i)\b(?:indexed|splunk_alert|rag\s+index|vector\s+index)\b")
_INGEST_RE = re.compile(r"(?i)\b(?:ingested|raw\s+ingest|splunk_ingest|ingest\s+storage)\b")
_ANALYSIS_UI_RE = re.compile(
    r"(?i)\b(?:analysis\s+page|/analysis|triage\s+queue|review\s+queue)\b",
)
_SECURITY_TRACK_RE = re.compile(r"(?i)\b(?:security\s+track|security\s+alerts?)\b")
_OBSERVABILITY_RE = re.compile(r"(?i)\b(?:observability|ops\s+track)\b")
_ALERTS_RE = re.compile(r"(?i)\balerts?\b")
_SOC_RE = re.compile(r"(?i)\b(?:\bsoc\b|thinking\s*soc)\b")


def queue_item_from_row(row: Dict[str, Any], triage: TriageOutcome) -> Dict[str, Any]:
    pl = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    return {
        "id": row.get("id"),
        "stored_at": row.get("created_at") or pl.get("stored_at"),
        "tsoc_record_type": row.get("tsoc_record_type"),
        "sid": row.get("sid") or pl.get("sid"),
        "search_name": row.get("search_name") or pl.get("search_name"),
        "row_index": row.get("row_index") if row.get("row_index") is not None else pl.get("row_index"),
        "source_track": triage.source_track,
        "triage": triage.model_dump(mode="json"),
        "triage_score": triage.triage_score,
        "investigation_priority": triage.investigation_priority,
        "review_verdict": triage.review_verdict,
        "needs_human_review": triage.needs_human_review,
    }


def record_types_for_track(track: TrackFilter) -> List[str]:
    if track == "security":
        return ["soc_analysis"]
    if track == "observability":
        return ["observability_analysis"]
    return ["soc_analysis", "observability_analysis"]


async def build_triage_queue_items(
    settings: Settings,
    *,
    track: TrackFilter = "all",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Build the Analysis page queue (identical to list_triage_queue).

    Only rows with a valid triage outcome are included (test/invalid payloads excluded).
    Sorted by triage_score descending.

    For ``track=all``, up to ``limit`` rows are loaded per record type (e.g. soc + observability),
    then merged — cap is ``limit * number_of_types`` so items visible on Security/Observability
    tabs are not dropped after a global top-N cut.
    """
    types = record_types_for_track(track)
    per_type_limit = max(limit, 50)
    items: List[Dict[str, Any]] = []
    for rec_type in types:
        rows = await search_stored_events(
            settings,
            record_type=rec_type,
            limit=per_type_limit,
        )
        for row in rows:
            pl = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            merged = dict(pl)
            merged.setdefault("tsoc_record_type", row.get("tsoc_record_type"))
            triage = triage_from_stored_payload(merged)
            if triage is None:
                continue
            if track != "all" and triage.source_track != track:
                continue
            items.append(queue_item_from_row(row, triage))
    items.sort(key=lambda x: int(x.get("triage_score") or 0), reverse=True)
    cap = limit * len(types) if track == "all" else limit
    return items[:cap]


def track_from_question(question: str) -> TrackFilter:
    q = question or ""
    if _OBSERVABILITY_RE.search(q) and not _SECURITY_TRACK_RE.search(q):
        return "observability"
    if _SECURITY_TRACK_RE.search(q):
        return "security"
    return "all"


def is_analysis_queue_question(question: str) -> bool:
    """Vague 'alerts in SOC' / Analysis page — not indexed RAG or raw ingest."""
    q = (question or "").strip()
    if not q:
        return False
    if _INDEXED_RE.search(q) or _INGEST_RE.search(q):
        return False
    if _ANALYSIS_UI_RE.search(q):
        return True
    if _ALERTS_RE.search(q):
        return True
    if _SOC_RE.search(q) and re.search(r"(?i)\b(?:available|how\s+many|list)\b", q):
        return True
    return False


def format_triage_queue_answer(
    items: List[Dict[str, Any]],
    *,
    track: TrackFilter,
) -> str:
    """Human-readable list aligned with /analysis table columns."""
    if not items:
        return (
            "The Analysis page queue is empty for track **{0}** "
            "(same as GET /api/v1/triage/queue)."
        ).format(track)

    lines = [
        "There are **{0}** item(s) on the Analysis page "
        "(track=**{1}**, same as /analysis):".format(len(items), track),
    ]
    for i, row in enumerate(items, 1):
        name = row.get("search_name")
        name_s = str(name) if name not in (None, "") else "—"
        sid = row.get("sid")
        sid_s = str(sid) if sid not in (None, "") else "—"
        score = row.get("triage_score")
        priority = row.get("investigation_priority") or "—"
        verdict = row.get("review_verdict") or "—"
        rtype = row.get("tsoc_record_type") or "—"
        source_track = row.get("source_track") or "—"
        lines.append(
            "{0}. **{1}** | score={2} | priority={3} | review={4} | "
            "type={5} | track={6} | sid={7}".format(
                i,
                name_s,
                score if score is not None else "—",
                priority,
                verdict,
                rtype,
                source_track,
                sid_s,
            )
        )
    return "\n".join(lines)
