"""Alert field context and post-processing for investigation questions."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Fields from the triggering search / alert row (priority order).
_ALERT_FIELD_PRIORITY = (
    "index",
    "host",
    "dest",
    "Computer",
    "user",
    "User",
    "src_user",
    "src",
    "dest_ip",
    "src_ip",
    "Image",
    "ProcessName",
    "process",
    "process_name",
    "process_path",
    "ParentImage",
    "parent_process",
    "parent_process_name",
    "CommandLine",
    "Command",
    "file_hash",
    "hash",
    "sourcetype",
    "source",
    "signature",
    "search_name",
)

_ORIG_SEARCH_FIELD_RE = re.compile(
    r'([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s|]+))'
)

_MAX_QUESTION_LEN = 220

_COMPOUND_SPLITTERS = (
    "; ",
    " and what ",
    " and also ",
    " as well as ",
    " additionally ",
    " furthermore ",
)

_TIME_PHRASE_PATTERNS = [
    re.compile(r"\bearliest\s*=\s*[^\s,)]+", re.I),
    re.compile(r"\blatest\s*=\s*[^\s,)]+", re.I),
    re.compile(r"\b(?:in|over|during|within)\s+the\s+(?:last|past)\s+\d+\s*(?:s|sec|secs|seconds?|m|min|mins|minutes?|h|hr|hrs|hours?|d|days?)\b", re.I),
    re.compile(r"\b(?:last|past)\s+\d+\s*(?:s|sec|secs|seconds?|m|min|mins|minutes?|h|hr|hrs|hours?|d|days?)\b", re.I),
    re.compile(r"[±+-]\s*\d+\s*(?:s|sec|secs|seconds?|m|min|mins|minutes?|h|hr|hrs|hours?)\b", re.I),
    re.compile(
        r"\b(?:same\s+minute|surrounding\s+window|time\s+window|time\s+range|time\s+bounds?|"
        r"same\s+time\s+window|around\s+the\s+alert\s+time)\b",
        re.I,
    ),
    re.compile(r"\b@(?:h|d|w|mon|y)\b", re.I),
]


def merge_alert_field_sample(
    normalized: Dict[str, Any],
    splunk_results: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Merge normalized alert with first Splunk result row (main search event)."""
    sample: Dict[str, Any] = dict(normalized or {})
    rows = splunk_results or []
    if rows and isinstance(rows[0], dict):
        for k, v in rows[0].items():
            sk = str(k)
            if sk.startswith("__mv_"):
                continue
            if v is None or (isinstance(v, str) and not v.strip()):
                continue
            sample.setdefault(sk, v)
    orig = str(sample.get("orig_search") or "").strip()
    if orig:
        for key, val in _fields_from_orig_search(orig).items():
            sample.setdefault(key, val)
    return sample


def _fields_from_orig_search(orig_search: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for m in _ORIG_SEARCH_FIELD_RE.finditer(orig_search):
        key = m.group(1)
        val = (m.group(2) or m.group(3) or m.group(4) or "").strip()
        if key and val and key.lower() not in ("search", "where"):
            out[key] = val
    return out


def _truncate_val(val: Any, *, max_len: int = 120) -> str:
    s = str(val).strip()
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


def primary_alert_fields(
    sample: Dict[str, Any],
    *,
    search_name: str = "",
    max_fields: int = 12,
) -> List[Tuple[str, str]]:
    """Key field=value pairs from the main search for questions and SPL prompts."""
    out: List[Tuple[str, str]] = []
    seen: set[str] = set()

    if search_name:
        sn = _truncate_val(search_name, max_len=200)
        if sn:
            out.append(("search_name", sn))
            seen.add("search_name")

    for key in _ALERT_FIELD_PRIORITY:
        if key in seen:
            continue
        val = sample.get(key)
        if val is None:
            continue
        sval = _truncate_val(val)
        if not sval or sval in ("-", "null", "None"):
            continue
        out.append((key, sval))
        seen.add(key)
        if len(out) >= max_fields:
            return out

    for key in sorted(sample.keys()):
        if len(out) >= max_fields:
            break
        sk = str(key)
        if sk in seen or sk.startswith("_") or sk.startswith("__mv_"):
            continue
        if sk in ("orig_search", "sid", "event_id", "preview"):
            continue
        val = sample.get(key)
        if val is None or isinstance(val, (dict, list)):
            continue
        sval = _truncate_val(val)
        if not sval:
            continue
        out.append((sk, sval))
        seen.add(sk)

    return out


def format_alert_fields_block(
    fields: List[Tuple[str, str]],
    *,
    search_name: str = "",
) -> str:
    if not fields and not search_name:
        return "(no structured alert fields available)"
    lines: List[str] = []
    if search_name and not any(k == "search_name" for k, _ in fields):
        lines.append("- search_name: {0}".format(_truncate_val(search_name, max_len=200)))
    for key, val in fields:
        lines.append("- {0}: {1}".format(key, val))
    return "\n".join(lines) if lines else "(no structured alert fields available)"


def _field_map(fields: List[Tuple[str, str]]) -> Dict[str, str]:
    return {k: v for k, v in fields}


def _pick_field(
    fmap: Dict[str, str],
    *keys: str,
) -> Optional[Tuple[str, str]]:
    for key in keys:
        val = fmap.get(key)
        if val:
            return key, val
    return None


def condense_investigation_question(question: str, *, max_len: int = _MAX_QUESTION_LEN) -> str:
    """Keep one short sentence; trim verbosity."""
    q = (question or "").strip()
    if not q:
        return q
    lower = q.lower()
    for sep in _COMPOUND_SPLITTERS:
        idx = lower.find(sep)
        if idx > 0:
            q = q[:idx].strip()
            lower = q.lower()
    q = re.sub(r"\s{2,}", " ", q)
    if len(q) > max_len:
        cut = q[:max_len].rsplit(" ", 1)[0]
        q = cut if cut else q[:max_len]
    if q and not q.endswith("?"):
        q = q.rstrip(".") + "?"
    return q


def strip_time_phrases_from_question(question: str) -> str:
    """Remove explicit time-window wording from investigation question text."""
    q = (question or "").strip()
    if not q:
        return q
    for pat in _TIME_PHRASE_PATTERNS:
        q = pat.sub("", q)
    q = re.sub(r"\s{2,}", " ", q)
    q = re.sub(r"\s+([,.;])", r"\1", q)
    q = re.sub(r"\(\s*\)", "", q)
    return q.strip().rstrip(" ,;-")


def question_references_alert_field(
    question: str,
    fields: List[Tuple[str, str]],
) -> bool:
    q_lower = (question or "").lower()
    if not q_lower:
        return False
    for key, val in fields:
        if key.lower() in q_lower:
            return True
        v = (val or "").strip()
        if len(v) >= 3 and v.lower() in q_lower:
            return True
        # basename for paths (e.g. osk.exe from full Image path)
        if "\\" in v or "/" in v:
            base = v.replace("\\", "/").rsplit("/", 1)[-1]
            if len(base) >= 3 and base.lower() in q_lower:
                return True
    return False


def _target_field_from_question_hint(
    question: str,
    fmap: Dict[str, str],
) -> Optional[str]:
    """If the question names a Splunk field, return that field key when present in fmap."""
    q_lower = (question or "").lower()
    for key in _ALERT_FIELD_PRIORITY:
        if key.lower() in q_lower and key in fmap:
            return key
    for key in sorted(fmap.keys()):
        if key.lower() in q_lower:
            return key
    return None


def _rewrite_single_answer_with_alert(
    question: str,
    fmap: Dict[str, str],
) -> Optional[str]:
    """Anchor vague LLM wording using field names/values from this alert only."""
    q_lower = (question or "").lower()
    if not fmap:
        return None

    target = _target_field_from_question_hint(question, fmap)
    anchor = _pick_field(
        fmap,
        "host",
        "dest",
        "Computer",
        "Image",
        "ProcessName",
        "process",
        "user",
        "User",
        "src_user",
        "src_ip",
        "src",
    )
    if target and anchor:
        ak, av = anchor
        on_host = ""
        host_t = _pick_field(fmap, "host", "dest", "Computer")
        if host_t and host_t[0] != ak and target not in (host_t[0],):
            on_host = " on {0}={1}".format(host_t[0], host_t[1])
        return "What is {0} for {1}={2}{3}?".format(target, ak, av, on_host)

    if anchor:
        ak, av = anchor
        return "What is the value of {0}={1} in related events?".format(ak, av)
    return None


def enrich_question_with_alert_fields(
    question: str,
    fields: List[Tuple[str, str]],
) -> str:
    """Ensure concise single-answer question cites alert field=value pairs."""
    q = condense_investigation_question(strip_time_phrases_from_question(question))
    if not q:
        return q
    if not fields:
        return q
    if question_references_alert_field(q, fields):
        return q
    rewritten = _rewrite_single_answer_with_alert(q, _field_map(fields))
    if rewritten:
        return condense_investigation_question(rewritten)
    anchor_parts: List[str] = []
    for key in ("host", "dest", "Image", "ProcessName", "process", "user"):
        for k, v in fields:
            if k == key and "{0}=".format(k) not in q:
                anchor_parts.append("{0}={1}".format(k, v))
                break
        if len(anchor_parts) >= 2:
            break
    if anchor_parts:
        return condense_investigation_question(
            "{0} ({1})?".format(q.rstrip("?"), ", ".join(anchor_parts))
        )
    k, v = fields[0]
    return condense_investigation_question("{0} for {1}={2}?".format(q.rstrip("?"), k, v))


def postprocess_investigation_question_strings(
    raw: Any,
    *,
    normalized: Optional[Dict[str, Any]] = None,
    splunk_results: Optional[List[Dict[str, Any]]] = None,
    search_name: str = "",
    max_items: int = 3,
) -> List[str]:
    """Sanitize LLM questions: no time windows; require main-search field references."""
    from services.soc_analysis.soc_verdict import sanitize_investigation_questions

    base = sanitize_investigation_questions(raw, max_items=max_items)
    if not base:
        return []

    sample = merge_alert_field_sample(normalized or {}, splunk_results)
    fields = primary_alert_fields(sample, search_name=search_name)
    out: List[str] = []
    for q in base:
        enriched = enrich_question_with_alert_fields(q, fields)
        if enriched and enriched not in out:
            out.append(enriched)
        if len(out) >= max_items:
            break
    return out
