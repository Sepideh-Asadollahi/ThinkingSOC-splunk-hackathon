"""Rule-based investigation questions when the LLM path is off."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from services.investigation.investigation_question_context import (
    _ALERT_FIELD_PRIORITY,
    merge_alert_field_sample,
    primary_alert_fields,
)


def _pick(
    sample: Dict[str, Any],
    *keys: str,
    max_len: int = 120,
) -> Optional[str]:
    for key in keys:
        val = sample.get(key)
        if val is None:
            continue
        s = str(val).strip()
        if s and s not in ("-", "null", "None"):
            if len(s) > max_len:
                return s[: max_len - 3] + "..."
            return s
    return None


def _field_present(sample: Dict[str, Any], key: str) -> bool:
    val = sample.get(key)
    if val is None:
        return False
    s = str(val).strip()
    return bool(s and s not in ("-", "null", "None"))


def _question_for_missing_field(
    target_key: str,
    anchor_key: str,
    anchor_val: str,
) -> str:
    """Generic single-answer question from alert field names and values only."""
    return "What is {0} for {1}={2}?".format(target_key, anchor_key, anchor_val)


def _attack_pivot_questions(sample: Dict[str, Any], fields: List[Tuple[str, str]]) -> List[str]:
    """Sysmon/process-style pivots when Image or process fields are present."""
    host = _pick(sample, "host", "dest", "Computer")
    image = _pick(sample, "Image", "ProcessName", "process", "process_name")
    if not host and not image:
        return []

    host_token = "host={0}".format(host) if host else ""
    image_glob = ""
    if image:
        base = image.replace("\\", "/").rsplit("/", 1)[-1]
        image_glob = 'Image="*{0}*"'.format(base.replace('"', ""))

    pivots: List[str] = []
    if image and not _field_present(sample, "ParentImage"):
        parts = [p for p in (host_token, image_glob) if p]
        pivots.append(
            "What is ParentImage for {0} on process create?".format(" ".join(parts))
        )
    if image and not _field_present(sample, "CommandLine"):
        parts = [p for p in (host_token, image_glob) if p]
        pivots.append(
            "What is CommandLine for {0} on process create?".format(" ".join(parts))
        )
    if image and not _field_present(sample, "Hashes"):
        parts = [p for p in (host_token, 'TargetFilename="*{0}*"'.format(
            image.replace("\\", "/").rsplit("/", 1)[-1].replace('"', "")
        )) if p]
        pivots.append("What is Hashes for file create events matching {0}?".format(" ".join(parts)))
    if image and not _field_present(sample, "DestinationIp"):
        parts = [p for p in (host_token, image_glob) if p]
        pivots.append(
            "What DestinationIp count exists for {0} on network events?".format(" ".join(parts))
        )
    return pivots


def fallback_investigation_questions(
    normalized: Dict[str, Any],
    splunk_results: List[Dict[str, Any]],
    *,
    max_items: int = 3,
) -> List[str]:
    """
    When LLM is unavailable: attack-relevant pivots from alert fields only.

    Prefer missing technique corroboration (parent, cmdline, hash, egress) over
    generic field lookups.
    """
    sample = merge_alert_field_sample(normalized, splunk_results)
    fields = primary_alert_fields(sample, max_fields=10)
    limit = max(1, int(max_items))
    out: List[str] = []

    for q in _attack_pivot_questions(sample, fields):
        if q not in out:
            out.append(q)
        if len(out) >= limit:
            return out[:limit]

    if not fields:
        idx = _pick(sample, "index")
        if idx:
            return ["What process Image count exists for index={0}?".format(idx)][:limit]
        return ["What is the suspicious process Image on this alert?"][:limit]

    anchors: List[Tuple[str, str]] = list(fields[:3])
    asked_targets: set[str] = set()

    for anchor_key, anchor_val in anchors:
        if len(out) >= limit:
            break
        for target_key in _ALERT_FIELD_PRIORITY:
            if target_key in asked_targets or target_key == anchor_key:
                continue
            if _field_present(sample, target_key):
                continue
            q = _question_for_missing_field(target_key, anchor_key, anchor_val)
            if q not in out:
                out.append(q)
                asked_targets.add(target_key)
            if len(out) >= limit:
                break

    if len(out) < limit:
        for j, (fk, fv) in enumerate(fields):
            if len(out) >= limit:
                break
            for tk, _tv in fields[j + 1 :]:
                if fk == tk or _field_present(sample, tk):
                    continue
                q = "What is {0} for {1}={2}?".format(tk, fk, fv)
                if q not in out:
                    out.append(q)
                if len(out) >= limit:
                    break

    if not out and fields:
        k, v = fields[0]
        out.append("What related process events share {0}={1}?".format(k, v))

    return out[:limit]
