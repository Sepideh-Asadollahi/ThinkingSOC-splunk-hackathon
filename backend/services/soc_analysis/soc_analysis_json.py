"""Parse JSON from LLM text (strip optional ``` fences, extract embedded objects)."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

_JSON_BLOCK = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_SPL_LINE_HINT = re.compile(r"\b(?:search\s+)?index\s*=", re.IGNORECASE)


def _balanced_json_objects(text: str) -> List[str]:
    """Return substrings that look like balanced ``{...}`` objects, in document order."""
    out: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        start = text.find("{", i)
        if start < 0:
            break
        depth = 0
        in_string = False
        escape = False
        for j in range(start, n):
            ch = text[j]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    out.append(text[start : j + 1])
                    i = j + 1
                    break
        else:
            i = start + 1
    return out


def _try_load_json(candidate: str) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _strip_wrapped_quotes(line: str) -> str:
    s = (line or "").strip().rstrip(",").strip()
    while s.startswith('"') or s.startswith("'"):
        s = s[1:].strip()
    while s.endswith('"') or s.endswith("'"):
        s = s[:-1].strip().rstrip(",").strip()
    return s


def _is_spl_line(s: str) -> bool:
    return bool(
        _SPL_LINE_HINT.search(s)
        or ("|" in s and ("index=" in s.lower() or "sourcetype=" in s.lower()))
    )


def _extract_spl_lines(text: str) -> List[str]:
    """Pull SPL-looking lines from raw model text (no JSON wrapper)."""
    out: List[str] = []
    seen: set[str] = set()
    for line in (text or "").replace("\r\n", "\n").split("\n"):
        s = _strip_wrapped_quotes(line)
        if not s or s in ("[", "]", "{"):
            continue
        if not _is_spl_line(s):
            continue
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def salvage_hunter_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Recover Hunter output when the model returns bare SPL strings instead of JSON.

    Handles newline-separated SPL, comma-separated quoted strings, or a JSON string array.
    """
    raw = (text or "").strip()
    if not raw:
        return None

    if raw.startswith("["):
        try:
            arr = json.loads(raw)
            if isinstance(arr, list):
                spl = [str(x).strip() for x in arr if str(x).strip()]
                if spl and all(_SPL_LINE_HINT.search(s) or "|" in s for s in spl[:3]):
                    return {
                        "narrative": "Hunt expansion (recovered from JSON array of SPL strings).",
                        "splunk_search_suggestions": spl[:12],
                        "notes": ["recovered_hunter_json_array"],
                    }
        except json.JSONDecodeError:
            pass

    spl_lines = _extract_spl_lines(raw)
    if len(spl_lines) < 2 and ('","' in raw or '",\n' in raw or '", "' in raw):
        seen = {s.lower() for s in spl_lines}
        for part in re.split(r'"\s*,\s*"', raw):
            s = _strip_wrapped_quotes(part)
            if not _is_spl_line(s):
                continue
            key = s.lower()
            if key not in seen:
                seen.add(key)
                spl_lines.append(s)
    if not spl_lines:
        return None

    prose: List[str] = []
    for line in raw.replace("\r\n", "\n").split("\n"):
        s = line.strip()
        if not s or _SPL_LINE_HINT.search(s) or s in ("[", "]", "{"):
            continue
        if "|" not in s and "index=" not in s.lower():
            prose.append(s)
    narrative = " ".join(prose)[:2000].strip()
    if not narrative:
        narrative = "Hunt expansion (recovered from non-JSON SPL output)."

    return {
        "narrative": narrative,
        "splunk_search_suggestions": spl_lines[:12],
        "notes": ["recovered_non_json_hunter_output"],
    }


def salvage_investigation_questions_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Recover investigation_questions when JSON is embedded in reasoning text."""
    raw = (text or "").strip()
    if not raw or "investigation_questions" not in raw:
        return None

    for fragment in reversed(_balanced_json_objects(raw)):
        parsed = _try_load_json(fragment)
        if parsed is None:
            continue
        iq = parsed.get("investigation_questions")
        if isinstance(iq, list) and iq:
            return {
                "investigation_questions": [str(x).strip() for x in iq if str(x).strip()],
                "notes": ["recovered_investigation_questions_from_text"],
            }
    return None


def parse_llm_json_response(text: str) -> Dict[str, Any]:
    """
    Parse a JSON object from model output.

    Handles fenced ```json blocks, prose + trailing JSON, and multiple objects
    (prefers the last valid dict, e.g. final answer after chain-of-thought).
    """
    raw = (text or "").strip()
    if not raw:
        raise json.JSONDecodeError("empty LLM response", raw, 0)

    candidates: List[str] = []
    for m in _JSON_BLOCK.finditer(raw):
        block = m.group(1).strip()
        if block:
            candidates.append(block)

    if not candidates:
        candidates.append(raw)

    for blob in candidates:
        parsed = _try_load_json(blob)
        if parsed is not None:
            return parsed

        for fragment in reversed(_balanced_json_objects(blob)):
            parsed = _try_load_json(fragment)
            if parsed is not None:
                return parsed

    salvaged = salvage_hunter_json_from_text(raw)
    if salvaged is not None:
        return salvaged

    return json.loads(raw)
