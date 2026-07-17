"""Parse SAIA MCP tool responses into SPL and explanations."""

from __future__ import annotations

import json
import re
from typing import Any, List, Tuple

_SPL_GENERATING = re.compile(
    r"^(?:splunk-spl\s*)?(?:\||\s*(?:tstats|search|datamodel)\b|\s*index\s*=)",
    re.I,
)
_SPL_PIPE_CMD = re.compile(
    r"^\s*\|\s*[A-Za-z_][\w-]*\b",
    re.I,
)
_SPL_CONTINUATION = re.compile(
    r"^\s*(?:[\w.]+\s*=|where\s+(?:_time|[\w.])|AND\s|OR\s)",
    re.I,
)
_MARKDOWN_FENCE = re.compile(
    r"```(?:json|splunk-spl|spl)?\s*([\s\S]*?)```",
    re.IGNORECASE,
)


def _split_markdown_saia_response(text: str) -> Tuple[str, str]:
    """When spl_only=false, SAIA returns markdown with reasoning then ```splunk-spl block."""
    raw = (text or "").strip()
    if not raw:
        return "", ""
    m = re.search(r"```(?:json|splunk-spl|spl)?\s*", raw, re.IGNORECASE)
    if not m:
        spl = extract_spl_from_saia_text(raw)
        if spl:
            return spl, ""
        return "", raw
    expl = raw[: m.start()].strip()
    spl = extract_spl_from_saia_text(raw[m.start() :])
    return spl, expl


def _normalize_spl_line(line: str) -> str:
    line = re.sub(r"^splunk-spl\s*", "", (line or "").strip(), flags=re.I).strip()
    if not line or line.lower() == "splunk-spl":
        return ""
    if line.startswith("|") or line.lower().startswith("search "):
        return line
    if re.match(r"^(?:tstats|datamodel)\b", line, re.I):
        return "| " + line
    return line


def _best_spl_from_fragment_list(items: List[Any]) -> str:
    """Pick the longest extractable SPL from SAIA spl_only list fragments."""
    best = ""
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        spl = extract_spl_from_saia_text(text)
        if spl and len(spl) > len(best):
            best = spl
    return best


def collapse_spl_lines(lines: List[str]) -> str:
    parts = [ln.strip() for ln in lines if ln.strip()]
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def extract_spl_from_saia_text(text: str) -> str:
    """
    SAIA often returns multi-line SPL prefixed with ``splunk-spl``.
    Keep the full pipeline (datamodel criteria, where, rename, table), not only the first line.
    """
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return ""

    for m in reversed(list(_MARKDOWN_FENCE.finditer(text))):
        block = m.group(1).strip()
        if "|" in block or block.lower().startswith("search "):
            inner = extract_spl_from_saia_text(block)
            if inner:
                return inner

    collected: List[str] = []
    started = False
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            if started:
                break
            continue
        if not started:
            line = _normalize_spl_line(line)
            if not line:
                continue
            if _SPL_GENERATING.match(line) or line.lower().startswith("search "):
                started = True
                collected.append(line)
            continue
        line = _normalize_spl_line(line) or line
        if _SPL_PIPE_CMD.match(line) or line.lower().startswith("search "):
            collected.append(line)
            continue
        if _SPL_CONTINUATION.match(line):
            collected.append(line)
            continue
        if started:
            break

    if collected:
        return collapse_spl_lines(collected)

    normalized = _normalize_spl_line(
        re.sub(r"^splunk-spl\s*", "", text, flags=re.I).strip()
    )
    if normalized:
        return collapse_spl_lines([normalized])
    if "|" in text or re.search(r"\b(?:tstats|search|datamodel)\b", text, re.I):
        return collapse_spl_lines([re.sub(r"^splunk-spl\s*", "", text, flags=re.I).strip()])
    return ""


def looks_like_spl_text(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if "|" in t or re.search(r"\b(?:tstats|search|datamodel)\b", t, re.I):
        return True
    if "splunk-spl" in t.lower() and ("|" in t or "tstats" in t.lower()):
        return True
    return False


def parse_saia_spl_result(raw: Any) -> Tuple[str, str]:
    """Extract SPL string and short explanation from MCP tool output."""
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("{"):
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                if looks_like_spl_text(text):
                    return extract_spl_from_saia_text(text) or text, ""
                return text, ""
        elif looks_like_spl_text(text):
            spl = extract_spl_from_saia_text(text)
            return spl or text, ""
        else:
            return text, ""
    if isinstance(raw, dict):
        for key in ("spl", "query", "search", "generated_spl", "optimized_spl"):
            if raw.get(key):
                expl = str(raw.get("explanation") or raw.get("description") or "")
                val = str(raw[key]).strip()
                if looks_like_spl_text(val):
                    return extract_spl_from_saia_text(val) or val, expl
                return val, expl
        results = raw.get("results")
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                resp = first.get("response")
                if isinstance(resp, list):
                    spl = _best_spl_from_fragment_list(resp)
                    if spl:
                        return spl, ""
                if isinstance(resp, str) and resp.strip():
                    spl, expl = _split_markdown_saia_response(resp)
                    if spl:
                        return spl, expl
                    return parse_saia_spl_result(resp)
        if "content" in raw:
            return parse_saia_spl_result(raw["content"])
    if isinstance(raw, list):
        for item in reversed(raw):
            if isinstance(item, dict) and item.get("type") == "text":
                return parse_saia_spl_result(item.get("text"))
            if isinstance(item, str) and looks_like_spl_text(item):
                spl = extract_spl_from_saia_text(item)
                if spl:
                    return spl, ""
    return str(raw or ""), ""


def parse_explain_text(raw: Any) -> str:
    """Extract analyst-facing explanation from saia_explain_spl."""
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("{"):
            try:
                data = json.loads(text)
                return parse_explain_text(data)
            except json.JSONDecodeError:
                return text
        _, expl = _split_markdown_saia_response(text)
        return (expl or text).strip()
    if isinstance(raw, dict):
        for key in ("explanation", "description", "text", "answer", "summary"):
            if raw.get(key):
                val = raw[key]
                if isinstance(val, str) and val.strip():
                    return parse_explain_text(val)
        results = raw.get("results")
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                resp = first.get("response")
                if isinstance(resp, str) and resp.strip():
                    _, expl = _split_markdown_saia_response(resp)
                    return (expl or resp).strip()
                if isinstance(resp, list):
                    joined = "\n".join(str(x).strip() for x in resp if str(x).strip())
                    if joined:
                        return joined
        if "content" in raw:
            return parse_explain_text(raw["content"])
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and item.get("type") == "text":
                return parse_explain_text(item.get("text"))
    return str(raw or "").strip()
