"""Compact threat-intel payloads for SOC analysis (LLM context + API response)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.threat_intel.virustotal_schema import (
    stats_imply_malicious,
    stats_imply_suspicious,
)

_IOC_BUCKETS = (
    ("file_hash", "files"),
    ("ip", "ips"),
    ("domain", "domains"),
    ("url", "urls"),
)


def _analyst_verdict_from_vt_stats(stats: Dict[str, int]) -> str:
    """Derived label for analysts; VT itself uses per-engine `category` in last_analysis_results."""
    if stats_imply_malicious(stats):
        return "malicious"
    if stats_imply_suspicious(stats):
        return "suspicious"
    if stats.get("harmless", 0) > 0:
        return "harmless"
    return "undetected"


def _compact_vt_ioc_display_entry(ioc: str, ioc_type: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    """Full VT summary per checked IOC for analyst UI (all hits, not only significant)."""
    err = entry.get("error")
    if err and err != "not_found":
        return {"ioc": ioc, "ioc_type": ioc_type, "verdict": "error", "error": str(err)}
    if err == "not_found":
        return {"ioc": ioc, "ioc_type": ioc_type, "verdict": "not_found", "error": "not_found"}

    summary = entry.get("summary")
    if not isinstance(summary, dict):
        return {"ioc": ioc, "ioc_type": ioc_type, "verdict": "unknown"}

    stats = summary.get("last_analysis_stats")
    if not isinstance(stats, dict):
        stats = {}

    votes = summary.get("total_votes")
    if not isinstance(votes, dict):
        votes = {}

    out: Dict[str, Any] = {
        "ioc": ioc,
        "ioc_type": ioc_type,
        "vt_id": summary.get("id"),
        "vt_type": summary.get("type"),
        "verdict": _analyst_verdict_from_vt_stats(stats),
        "last_analysis_stats": stats,
        "reputation": summary.get("reputation"),
        "total_votes": votes,
        "last_analysis_date": summary.get("last_analysis_date"),
        "link": summary.get("link"),
    }
    tags = summary.get("tags")
    if isinstance(tags, list) and tags:
        out["tags"] = [str(t) for t in tags]
    categories = summary.get("categories")
    if isinstance(categories, dict) and categories:
        out["categories"] = categories
    for key in ("md5", "sha1", "sha256", "meaningful_name", "type_description"):
        if summary.get(key) is not None:
            out[key] = summary.get(key)
    return out


def _compact_vt_ioc_entry(ioc: str, ioc_type: str, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    err = entry.get("error")
    if err and err != "not_found":
        return None
    if err == "not_found":
        return {"ioc": ioc, "ioc_type": ioc_type, "verdict": "not_found"}

    summary = entry.get("summary")
    if not isinstance(summary, dict):
        return None

    stats = summary.get("last_analysis_stats")
    if not isinstance(stats, dict):
        stats = {}

    votes = summary.get("total_votes")
    if not isinstance(votes, dict):
        votes = {}

    out: Dict[str, Any] = {
        "ioc": ioc,
        "ioc_type": ioc_type,
        "vt_id": summary.get("id"),
        "vt_type": summary.get("type"),
        "verdict": _analyst_verdict_from_vt_stats(stats),
        "last_analysis_stats": stats,
        "reputation": summary.get("reputation"),
        "total_votes": votes,
    }
    tags = summary.get("tags")
    if isinstance(tags, list) and tags:
        out["tags"] = [str(t) for t in tags[:5]]
    categories = summary.get("categories")
    if isinstance(categories, dict) and categories:
        out["categories"] = categories
    return out


def _is_significant_finding(finding: Dict[str, Any]) -> bool:
    verdict = str(finding.get("verdict") or "")
    if verdict in ("malicious", "suspicious"):
        return True
    stats = finding.get("last_analysis_stats")
    if isinstance(stats, dict):
        if stats_imply_malicious(stats) or stats_imply_suspicious(stats):
            return True
    votes = finding.get("total_votes")
    if isinstance(votes, dict) and int(votes.get("malicious") or 0) > 0:
        return True
    rep = finding.get("reputation")
    try:
        if rep is not None and int(rep) < 0:
            return True
    except (TypeError, ValueError):
        pass
    return False


def _count_checked_iocs(vt: Dict[str, Any]) -> int:
    requested = vt.get("requested")
    if isinstance(requested, dict):
        return sum(
            len(requested.get(k) or [])
            for k in ("file_hashes", "ips", "domains", "urls")
        )
    total = 0
    for _, bucket_key in _IOC_BUCKETS:
        bucket = vt.get(bucket_key)
        if isinstance(bucket, dict):
            total += len(bucket)
    return total


def _build_note(findings: List[Dict[str, Any]], checked: int) -> str:
    if not findings:
        if checked <= 0:
            return "No IOCs were submitted for threat-intelligence lookup."
        return (
            "Checked {0} IOC(s) via VirusTotal; no malicious or suspicious detections "
            "in last_analysis_stats."
        ).format(checked)
    malicious = sum(1 for f in findings if f.get("verdict") == "malicious")
    suspicious = sum(1 for f in findings if f.get("verdict") == "suspicious")
    parts = []
    if malicious:
        parts.append("{0} malicious".format(malicious))
    if suspicious:
        parts.append("{0} suspicious".format(suspicious))
    label = ", ".join(parts) if parts else "{0} notable".format(len(findings))
    return "VirusTotal: {0} IOC hit(s) ({1}) included in analysis context.".format(len(findings), label)


def compact_threat_intel_for_analysis(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Keep only analyst-actionable TI fields for LLM prompts and API consumers.

    Findings preserve VirusTotal attribute names (``last_analysis_stats``, ``reputation``,
    ``total_votes``, ``tags``, ``categories``) per API v3 docs.
    """
    if not raw or not isinstance(raw, dict):
        return None

    if raw.get("findings") is not None and raw.get("status") is not None:
        if raw.get("iocs") is None and raw.get("findings"):
            return {**raw, "iocs": list(raw.get("findings") or [])}
        return raw

    vt = raw.get("virustotal")
    if not isinstance(vt, dict):
        return None

    if not vt.get("enabled"):
        reason = str(vt.get("reason") or "disabled")
        return {
            "status": "unavailable",
            "source": "virustotal",
            "reason": reason,
            "findings": [],
            "note": "Threat intelligence enrichment was not applied.",
        }

    findings: List[Dict[str, Any]] = []
    iocs: List[Dict[str, Any]] = []
    for ioc_type, bucket_key in _IOC_BUCKETS:
        bucket = vt.get(bucket_key)
        if not isinstance(bucket, dict):
            continue
        for ioc, entry in bucket.items():
            if not isinstance(entry, dict):
                continue
            ioc_key = str(ioc)
            display = _compact_vt_ioc_display_entry(ioc_key, ioc_type, entry)
            iocs.append(display)
            row = _compact_vt_ioc_entry(ioc_key, ioc_type, entry)
            if row and _is_significant_finding(row):
                findings.append(row)

    checked = _count_checked_iocs(vt)
    status = "ok" if findings else "no_significant_hits"
    return {
        "status": status,
        "source": "virustotal",
        "checked_ioc_count": checked,
        "findings": findings,
        "iocs": iocs,
        "note": _build_note(findings, checked),
    }
