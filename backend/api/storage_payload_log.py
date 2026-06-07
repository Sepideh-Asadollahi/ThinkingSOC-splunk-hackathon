"""Small payload summaries for storage API logs (avoid dumping full JSON)."""

from __future__ import annotations

from typing import Any, Dict, Optional


def storage_payload_summary(payload: Any) -> Dict[str, Any]:
    """Token-efficient shape hints for troubleshooting investigation loads."""
    if not isinstance(payload, dict):
        return {"payload_type": type(payload).__name__}

    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    iq = analysis.get("investigation_questions") if isinstance(analysis, dict) else None
    iq_count = len(iq) if isinstance(iq, list) else 0
    spl_rows = 0
    if isinstance(iq, list):
        for item in iq:
            if not isinstance(item, dict):
                continue
            sr = item.get("spl_results")
            if isinstance(sr, dict) and isinstance(sr.get("rows"), list):
                spl_rows += len(sr["rows"])

    return {
        "payload_keys": sorted(payload.keys()),
        "has_analysis": isinstance(payload.get("analysis"), dict),
        "has_security_result": isinstance(payload.get("security_result"), dict),
        "has_analysis_output": isinstance(payload.get("analysis_output"), dict),
        "investigation_questions": iq_count,
        "spl_result_rows_total": spl_rows,
        "has_judge": isinstance(analysis.get("judge"), dict) if isinstance(analysis, dict) else False,
        "has_hunter": isinstance(analysis.get("hunter"), dict) if isinstance(analysis, dict) else False,
        "has_triage": payload.get("triage") is not None
        or (isinstance(analysis, dict) and analysis.get("triage") is not None),
    }


def approx_json_bytes(value: Any) -> Optional[int]:
    try:
        import json

        return len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"))
    except Exception:
        return None


def investigation_questions_detail(payload: Any) -> list[Dict[str, Any]]:
    """Per-question SPL row counts — pinpoints huge spl_results blobs in logs."""
    if not isinstance(payload, dict):
        return []
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    iq = analysis.get("investigation_questions") if isinstance(analysis, dict) else None
    if not isinstance(iq, list):
        return []

    out: list[Dict[str, Any]] = []
    for idx, item in enumerate(iq):
        if not isinstance(item, dict):
            out.append({"index": idx, "shape": type(item).__name__})
            continue
        sr = item.get("spl_results")
        rows = sr.get("rows") if isinstance(sr, dict) else None
        row_count = len(rows) if isinstance(rows, list) else 0
        raw_len = 0
        if isinstance(rows, list) and rows:
            first = rows[0] if isinstance(rows[0], dict) else {}
            raw = first.get("_raw")
            if isinstance(raw, str):
                raw_len = len(raw)
        out.append(
            {
                "index": idx,
                "question_len": len(str(item.get("question") or "")),
                "spl_len": len(str(item.get("spl") or "")),
                "spl_result_rows": row_count,
                "spl_results_truncated": sr.get("truncated") if isinstance(sr, dict) else None,
                "first_row_raw_chars": raw_len,
                "has_saia": item.get("spl_saia_analysis") is not None,
                "has_results_analysis": item.get("spl_results_analysis") is not None,
            }
        )
    return out
