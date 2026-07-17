"""Investigation timeline and analyst human-in-the-loop actions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import Settings
from services.splunk_json_store import (
    get_stored_event_by_id,
    search_stored_events,
    splunk_store_configured,
    submit_hec_event,
)

ANALYST_ACTION_RECORD_TYPE = "investigation_analyst_action"
VERIFIED_RUNBOOK_DRAFT_RECORD_TYPE = "verified_runbook_draft"
VERIFIED_RUNBOOK_APPROVAL_RECORD_TYPE = "verified_runbook_approval"
VERIFIED_RUNBOOK_RUN_RECORD_TYPE = "verified_runbook_run"

# Pipeline stages shown in Event timeline (one Splunk alert = sid + row_index).
TIMELINE_PIPELINE_RECORD_TYPES = frozenset(
    {
        "splunk_ingest",
        "agentic_ops_analysis",
        "soc_analysis",
        "observability_analysis",
        "admin_org_gap_suggest",
        ANALYST_ACTION_RECORD_TYPE,
        VERIFIED_RUNBOOK_DRAFT_RECORD_TYPE,
        VERIFIED_RUNBOOK_APPROVAL_RECORD_TYPE,
        VERIFIED_RUNBOOK_RUN_RECORD_TYPE,
    }
)

# Internal shards / audits — same sid but not separate pipeline steps for the analyst.
_TIMELINE_EXCLUDED_RECORD_TYPES = frozenset(
    {
        "soc_analysis_audit",
        "enrichment_resolve",
        "llm_chat_audit",
    }
)

# Re-runnable pipeline outputs — timeline shows at most one per alert view.
_DEDUPE_ONE_PER_ALERT_TYPES = frozenset(
    {
        "agentic_ops_analysis",
        "admin_org_gap_suggest",
        "soc_analysis",
        "observability_analysis",
    }
)

_ANALYSIS_RECORD_TYPES = frozenset({"soc_analysis", "observability_analysis"})

# Lower = earlier in typical pipeline order when timestamps tie.
_RECORD_SORT_RANK: Dict[str, int] = {
    "splunk_ingest": 10,
    "agentic_ops_analysis": 20,
    "enrichment_resolve": 30,
    "soc_analysis": 40,
    "observability_analysis": 40,
    "admin_org_gap_suggest": 50,
    "investigation_analyst_action": 60,
    "verified_runbook_draft": 70,
    "verified_runbook_approval": 80,
    "verified_runbook_run": 90,
    "soc_analysis_audit": 70,
}


def _step_meta(record_type: str) -> tuple[str, str]:
    mapping = {
        "splunk_ingest": ("Splunk ingest", "Alert received via webhook and normalized"),
        "agentic_ops_analysis": ("Classification", "Agentic ops router selected the pipeline"),
        "enrichment_resolve": ("Enrichment", "Inventory user/asset resolution"),
        "soc_analysis": ("SOC analysis", "Defender, Hunter, and Judge pipeline completed"),
        "observability_analysis": ("Observability analysis", "Ops diagnoser/responder pipeline completed"),
        "admin_org_gap_suggest": ("Admin org gap", "Organizational knowledge gap suggested"),
        "investigation_analyst_action": ("Analyst decision", "Human acknowledge or escalate recorded"),
        "verified_runbook_draft": ("Runbook compiled", "Reusable intents generated and verified on the source"),
        "verified_runbook_approval": ("Runbook decision", "Human approval or rejection recorded"),
        "verified_runbook_run": ("Runbook reused", "Approved procedure executed on a compatible alert"),
        "soc_analysis_audit": ("Analysis audit", "Pipeline audit metadata stored"),
    }
    return mapping.get(record_type, (record_type.replace("_", " ").title(), "Stored record"))


def _resolve_row_index(row: Dict[str, Any]) -> Optional[int]:
    ri = row.get("row_index")
    if ri is not None:
        return int(ri)
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    if payload.get("row_index") is not None:
        return int(payload["row_index"])
    return None


def _same_alert_row(anchor: Dict[str, Any], row: Dict[str, Any]) -> bool:
    """True when ``row`` belongs to the same Splunk result row as ``anchor``.

    Multi-row jobs store each row under a suffixed sid (``{base}-1``, ``{base}-2``),
    so a sid match is the strongest signal. Fall back to ``row_index`` for legacy
    records that share the base sid.
    """
    anchor_sid = str(anchor.get("sid") or "").strip()
    row_sid = str(row.get("sid") or "").strip()
    if anchor_sid and row_sid and anchor_sid != row_sid:
        # Different suffixed sids under the same job → different rows.
        return False
    # Same sid (or one missing): legacy records share the base sid, so disambiguate
    # by row_index when both are known.
    anchor_ri = _resolve_row_index(anchor)
    row_ri = _resolve_row_index(row)
    if anchor_ri is not None and row_ri is not None:
        return anchor_ri == row_ri
    return True


def _is_timeline_pipeline_record(record_type: str) -> bool:
    if not record_type:
        return False
    if record_type in _TIMELINE_EXCLUDED_RECORD_TYPES:
        return False
    if record_type.startswith("soc_investigation_"):
        return False
    return record_type in TIMELINE_PIPELINE_RECORD_TYPES


def _filter_timeline_rows(
    rows: List[Dict[str, Any]],
    anchor: Dict[str, Any],
    record_id: int,
) -> List[Dict[str, Any]]:
    """Keep pipeline steps for this alert row only (not all storage under sid)."""
    filtered: List[Dict[str, Any]] = []
    for row in rows:
        rtype = str(row.get("tsoc_record_type") or "")
        if not _is_timeline_pipeline_record(rtype):
            continue
        # The ingest summary is job-level (base sid, shared by every row) — always keep it.
        if rtype != "splunk_ingest" and not _same_alert_row(anchor, row):
            continue
        if rtype == ANALYST_ACTION_RECORD_TYPE:
            pl = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            if pl.get("investigation_record_id") not in (record_id, str(record_id)):
                continue
        if rtype in (VERIFIED_RUNBOOK_DRAFT_RECORD_TYPE, VERIFIED_RUNBOOK_APPROVAL_RECORD_TYPE):
            pl = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            if pl.get("source_record_id") not in (record_id, str(record_id)):
                continue
        if rtype == VERIFIED_RUNBOOK_RUN_RECORD_TYPE:
            pl = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            if pl.get("target_record_id") not in (record_id, str(record_id)):
                continue
        filtered.append(row)
    return _dedupe_timeline_records(filtered, anchor)


def _row_dt(row: Dict[str, Any]) -> datetime:
    return _parse_dt(row.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)


def _pick_focus_analysis_record(
    rows: List[Dict[str, Any]],
    anchor: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """SOC/Obs record the analyst opened, or the latest analysis on this alert row."""
    anchor_type = str(anchor.get("tsoc_record_type") or "")
    if anchor_type in _ANALYSIS_RECORD_TYPES:
        return anchor
    analyses = [r for r in rows if str(r.get("tsoc_record_type") or "") in _ANALYSIS_RECORD_TYPES]
    if not analyses:
        return None
    return max(analyses, key=lambda r: (_row_dt(r), r.get("id") or 0))


def _pick_keep_id_for_type(
    rows: List[Dict[str, Any]],
    *,
    record_type: str,
    anchor: Dict[str, Any],
    focus: Optional[Dict[str, Any]],
) -> Optional[int]:
    typed = [r for r in rows if str(r.get("tsoc_record_type") or "") == record_type]
    if not typed:
        return None

    anchor_type = str(anchor.get("tsoc_record_type") or "")
    anchor_id = anchor.get("id")
    if anchor_type == record_type and anchor_id is not None:
        return int(anchor_id)

    focus_dt = _row_dt(focus) if focus else None

    if record_type in _ANALYSIS_RECORD_TYPES:
        if focus is not None and focus.get("id") is not None:
            return int(focus["id"])
        return int(max(typed, key=lambda r: (_row_dt(r), r.get("id") or 0)).get("id"))

    if record_type == "agentic_ops_analysis":
        if focus_dt is not None:
            before = [r for r in typed if _row_dt(r) <= focus_dt]
            pool = before or typed
        else:
            pool = typed
        return int(max(pool, key=lambda r: (_row_dt(r), r.get("id") or 0)).get("id"))

    if record_type == "admin_org_gap_suggest":
        if focus_dt is not None:
            after = [r for r in typed if _row_dt(r) >= focus_dt]
            if after:
                return int(min(after, key=lambda r: (_row_dt(r), r.get("id") or 0)).get("id"))
        return int(max(typed, key=lambda r: (_row_dt(r), r.get("id") or 0)).get("id"))

    return int(max(typed, key=lambda r: (_row_dt(r), r.get("id") or 0)).get("id"))


def _dedupe_timeline_records(
    rows: List[Dict[str, Any]],
    anchor: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """One ingest + one of each re-runnable pipeline stage for the opened investigation."""
    if not rows:
        return rows

    focus = _pick_focus_analysis_record(rows, anchor)
    keep_ids: set[int] = set()

    ingests = [r for r in rows if str(r.get("tsoc_record_type") or "") == "splunk_ingest"]
    if ingests:
        keep_ids.add(int(min(ingests, key=lambda r: (_row_dt(r), r.get("id") or 0)).get("id")))

    for row in rows:
        rtype = str(row.get("tsoc_record_type") or "")
        if rtype in (ANALYST_ACTION_RECORD_TYPE, "splunk_ingest"):
            rid = row.get("id")
            if rid is not None and rtype == ANALYST_ACTION_RECORD_TYPE:
                keep_ids.add(int(rid))
            continue
        if rtype not in _DEDUPE_ONE_PER_ALERT_TYPES:
            rid = row.get("id")
            if rid is not None:
                keep_ids.add(int(rid))

    keep_analysis_id = _pick_keep_id_for_type(
        rows, record_type="soc_analysis", anchor=anchor, focus=focus
    )
    keep_obs_id = _pick_keep_id_for_type(
        rows, record_type="observability_analysis", anchor=anchor, focus=focus
    )
    if keep_analysis_id is not None and keep_obs_id is not None:
        focus_type = str(focus.get("tsoc_record_type") or "") if focus else ""
        if focus_type == "observability_analysis":
            keep_analysis_id = None
        elif focus_type == "soc_analysis":
            keep_obs_id = None
        else:
            obs_row = next((r for r in rows if r.get("id") == keep_obs_id), None)
            ana_row = next((r for r in rows if r.get("id") == keep_analysis_id), None)
            if obs_row and ana_row and _row_dt(obs_row) > _row_dt(ana_row):
                keep_analysis_id = None
            else:
                keep_obs_id = None

    for keep_id in (keep_analysis_id, keep_obs_id):
        if keep_id is not None:
            keep_ids.add(keep_id)

    for rtype in ("agentic_ops_analysis", "admin_org_gap_suggest"):
        keep_id = _pick_keep_id_for_type(rows, record_type=rtype, anchor=anchor, focus=focus)
        if keep_id is not None:
            keep_ids.add(keep_id)

    return [r for r in rows if r.get("id") in keep_ids]


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _timeline_detail(row: Dict[str, Any]) -> Optional[str]:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    rtype = str(row.get("tsoc_record_type") or "")

    if rtype == "splunk_ingest":
        norm = payload.get("normalized") if isinstance(payload.get("normalized"), dict) else {}
        host = norm.get("host") or norm.get("dest")
        user = norm.get("user")
        parts = [p for p in [host, user] if p]
        return "Fields: {0}".format(", ".join(str(x) for x in parts)) if parts else None

    if rtype == "agentic_ops_analysis":
        classification = payload.get("classification") if isinstance(payload.get("classification"), dict) else {}
        track = classification.get("track")
        pipeline = classification.get("recommended_pipeline")
        if track or pipeline:
            detail = "Track {0}, pipeline {1}".format(track or "—", pipeline or "—")
            if track in ("both",) or pipeline in ("dual", "both"):
                detail += " (legacy dual routing — re-run analysis for exclusive track)"
            return detail
        return None

    if rtype in ("soc_analysis", "observability_analysis"):
        analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else payload
        judge = analysis.get("judge") if isinstance(analysis.get("judge"), dict) else {}
        verdict = judge.get("verdict")
        triage = payload.get("triage") if isinstance(payload.get("triage"), dict) else analysis.get("triage")
        if isinstance(triage, dict):
            inv_p = triage.get("investigation_priority")
            score = triage.get("triage_score")
            extra = " · Triage {0} (score {1})".format(inv_p, score) if inv_p else ""
        else:
            extra = ""
        if verdict:
            return "Verdict {0}{1}".format(verdict, extra)
        return extra.strip(" ·") or None

    if rtype == ANALYST_ACTION_RECORD_TYPE:
        action = payload.get("action")
        note = payload.get("note")
        parts = [str(action)] if action else []
        if note:
            parts.append(str(note)[:120])
        return " — ".join(parts) if parts else None

    if rtype == VERIFIED_RUNBOOK_DRAFT_RECORD_TYPE:
        status = payload.get("status") or "DRAFT"
        title = payload.get("title")
        count = len(payload.get("steps") or [])
        return f"{status} · {count} step(s)" + (f" · {title}" if title else "")

    if rtype == VERIFIED_RUNBOOK_APPROVAL_RECORD_TYPE:
        decision = payload.get("decision") or "recorded"
        analyst = payload.get("analyst") or "analyst"
        return f"{decision} by {analyst}"

    if rtype == VERIFIED_RUNBOOK_RUN_RECORD_TYPE:
        status = payload.get("status") or "FAILED"
        saved = payload.get("estimated_minutes_saved")
        return f"{status}" + (f" · estimated {saved} minutes saved" if saved is not None else "")

    if rtype == "enrichment_resolve":
        conf = payload.get("confidence")
        user = payload.get("resolved_user_id")
        asset = payload.get("resolved_asset_id")
        if conf or user or asset:
            return "Confidence {0}, user {1}, asset {2}".format(conf or "—", user or "—", asset or "—")
        return None

    return None


def _row_to_timeline_step(row: Dict[str, Any], *, highlight_record_id: Optional[int] = None) -> Dict[str, Any]:
    rtype = str(row.get("tsoc_record_type") or "unknown")
    title, description = _step_meta(rtype)
    created = row.get("created_at")
    detail = _timeline_detail(row)
    rid = row.get("id")
    return {
        "record_id": rid,
        "record_type": rtype,
        "title": title,
        "description": description,
        "detail": detail,
        "created_at": created,
        "is_current_record": highlight_record_id is not None and rid == highlight_record_id,
        "is_analyst_action": rtype == ANALYST_ACTION_RECORD_TYPE,
    }


async def build_investigation_timeline(
    settings: Settings,
    record_id: int,
    *,
    limit: int = 80,
) -> Dict[str, Any]:
    """Chronological pipeline steps for the alert linked to this storage record."""
    anchor = await get_stored_event_by_id(settings, record_id)
    if anchor is None:
        return {"record_id": record_id, "found": False, "steps": []}

    from services.soc_analysis.analysis_audit import splunk_job_sid

    sid = anchor.get("sid")
    anchor_ri = _resolve_row_index(anchor)
    rows: List[Dict[str, Any]] = []
    if sid and splunk_store_configured(settings):
        # Multi-row jobs store rows under suffixed sids ({base}-1, {base}-2) while the
        # ingest summary keeps the base sid — fetch the whole job, then filter to this row.
        rows = await search_stored_events(
            settings,
            job_sid=splunk_job_sid(str(sid)) or str(sid),
            limit=limit,
            order="asc",
        )
        rows = _filter_timeline_rows(rows, anchor, record_id)
        # Run records belong to the target sid by design. Also project runs that
        # originated from this source investigation into its timeline so the full
        # compile → approve → reuse story remains visible on the source record.
        if str(anchor.get("tsoc_record_type") or "") == "soc_analysis":
            run_rows = await search_stored_events(
                settings,
                record_type=VERIFIED_RUNBOOK_RUN_RECORD_TYPE,
                limit=limit,
                order="asc",
            )
            existing_ids = {row.get("id") for row in rows}
            for run_row in run_rows:
                payload = (
                    run_row.get("payload")
                    if isinstance(run_row.get("payload"), dict)
                    else {}
                )
                if payload.get("source_record_id") not in (
                    record_id,
                    str(record_id),
                ):
                    continue
                if run_row.get("id") not in existing_ids:
                    rows.append(run_row)
                    existing_ids.add(run_row.get("id"))
        if anchor.get("id") and not any(r.get("id") == anchor.get("id") for r in rows):
            if _is_timeline_pipeline_record(str(anchor.get("tsoc_record_type") or "")):
                rows.append(anchor)
    else:
        rows = [anchor] if _is_timeline_pipeline_record(str(anchor.get("tsoc_record_type") or "")) else []

    steps = [_row_to_timeline_step(r, highlight_record_id=record_id) for r in rows]

    def sort_key(step: Dict[str, Any]) -> tuple:
        dt = _parse_dt(step.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)
        rank = _RECORD_SORT_RANK.get(str(step.get("record_type")), 99)
        if step.get("is_analyst_action"):
            return (2, dt, rank, step.get("record_id") or 0)
        return (1, rank, dt, step.get("record_id") or 0)

    steps.sort(key=sort_key)

    if not steps:
        steps = [_row_to_timeline_step(anchor, highlight_record_id=record_id)]

    return {
        "record_id": record_id,
        "found": True,
        "sid": sid,
        "search_name": anchor.get("search_name"),
        "row_index": anchor_ri,
        "postgres_configured": splunk_store_configured(settings),
        "steps": steps,
    }


def _pick_recommended_step_from_payload(payload: Dict[str, Any]) -> str:
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else payload
    if not isinstance(analysis, dict):
        return ""
    judge = analysis.get("judge") if isinstance(analysis.get("judge"), dict) else {}
    step = judge.get("recommended_next_step") or judge.get("next_step")
    if isinstance(step, str) and step.strip():
        return step.strip()
    triage = payload.get("triage") if isinstance(payload.get("triage"), dict) else analysis.get("triage")
    if isinstance(triage, dict):
        report = triage.get("report") if isinstance(triage.get("report"), dict) else {}
        action = report.get("recommended_action")
        if isinstance(action, str) and action.strip():
            return action.strip()
    return ""


async def list_analyst_actions_for_record(
    settings: Settings,
    record_id: int,
    *,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    anchor = await get_stored_event_by_id(settings, record_id)
    if anchor is None:
        return []
    sid = anchor.get("sid")
    if not sid or not splunk_store_configured(settings):
        return []

    rows = await search_stored_events(
        settings,
        sid=str(sid),
        record_type=ANALYST_ACTION_RECORD_TYPE,
        limit=limit,
        order="desc",
    )
    out: List[Dict[str, Any]] = []
    for row in rows:
        pl = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if pl.get("investigation_record_id") not in (record_id, str(record_id)):
            continue
        out.append(
            {
                "id": row.get("id"),
                "created_at": row.get("created_at"),
                "action": pl.get("action"),
                "note": pl.get("note"),
                "recommended_step": pl.get("recommended_step_at_action"),
                "investigation_record_id": pl.get("investigation_record_id"),
            }
        )
    return out


async def record_analyst_action(
    settings: Settings,
    record_id: int,
    *,
    action: str,
    note: Optional[str] = None,
    analyst: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist acknowledge or escalate for an investigation record."""
    normalized = str(action or "").strip().lower()
    if normalized not in ("acknowledge", "escalate"):
        raise ValueError("action must be 'acknowledge' or 'escalate'")

    anchor = await get_stored_event_by_id(settings, record_id)
    if anchor is None:
        raise LookupError("Record not found")

    payload_anchor = anchor.get("payload") if isinstance(anchor.get("payload"), dict) else {}
    recommended = _pick_recommended_step_from_payload(payload_anchor)
    now = datetime.now(timezone.utc).isoformat()

    event = {
        "tsoc_record_type": ANALYST_ACTION_RECORD_TYPE,
        "sid": anchor.get("sid"),
        "search_name": anchor.get("search_name"),
        "row_index": anchor.get("row_index"),
        "investigation_record_id": record_id,
        "action": normalized,
        "note": (note or "").strip() or None,
        "analyst": (analyst or "").strip() or "analyst",
        "recommended_step_at_action": recommended or None,
        "recorded_at": now,
    }

    if not splunk_store_configured(settings):
        return {"ok": False, "postgres_configured": False, "event": event}

    ok = await submit_hec_event(settings, event)
    return {
        "ok": ok,
        "postgres_configured": True,
        "event": event,
        "created_at": now,
    }
