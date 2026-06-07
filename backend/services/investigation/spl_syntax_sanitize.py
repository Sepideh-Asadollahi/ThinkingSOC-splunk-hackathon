"""Generic SPL syntax cleanup for LLM/MCP output (no domain-specific field mappings).

Design and pipeline diagram: ``docs/13-cim-investigation-spl-mcp.md``
(section *SPL syntax sanitize + parser-driven refine*).

Semantic fixes (wrong index, field names) use Splunk ``parse_spl`` + LiteLLM refine
with live MCP catalog — not hardcoded mappings in this module.
"""

from __future__ import annotations

import re

# Unquoted ``field=Foo:Bar`` is parsed as field ``Foo`` with value ``Bar`` — quote any colon value.
_SPL_COLON_FIELD = re.compile(
    r'\b(\w+)=([^"\s|]+:[^\s|"]+)',
    re.IGNORECASE,
)
_SEARCH_FIELD_CLAUSE = re.compile(
    r'\b(\w+)\s*=\s*(?:"[^"]*"|[^\s|"]+)',
    re.IGNORECASE,
)
_VALUES_IN_STATS = re.compile(
    r"values\s*\(\s*([^)]+)\s*\)(?:\s+as\s+(\w+))?",
    re.IGNORECASE,
)
_EARLIEST_IN_SPL = re.compile(r"\s*earliest=[^\s|]+", re.IGNORECASE)
_LATEST_IN_SPL = re.compile(r"\s*latest=[^\s|]+", re.IGNORECASE)
# LLM often omits ``search`` or uses ``| index=foo`` — Splunk then treats ``index`` as a command name.
_IMPLICIT_SEARCH_START = re.compile(
    r"^(?:\|\s*)?(index|host|sourcetype|source|EventCode|EventID|user|src|dest|src_ip|dest_ip)\s*=",
    re.IGNORECASE,
)
_FIELD_EQ_TOKEN = re.compile(r'\b(\w+)=(?:"[^"]*"|[^\s,|"]+)')
_AGG_COMMAND_PREFIX = re.compile(
    r"^(stats|chart|timechart|top|rare|table|fields)\b",
    re.IGNORECASE,
)


def strip_time_range_from_spl(spl: str) -> str:
    """Remove earliest=/latest= from SPL; execution applies All Time bounds."""
    s = (spl or "").strip()
    if not s:
        return s
    s = _EARLIEST_IN_SPL.sub("", s)
    s = _LATEST_IN_SPL.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def strip_spl_backticks(spl: str) -> str:
    """Remove stray markdown backticks from LLM/MCP SPL output."""
    return (spl or "").replace("`", "")


def quote_spl_colon_field_values(spl: str) -> str:
    """Quote any ``field=value:with:colons`` (Splunk treats ``:`` as a field modifier)."""

    def _repl(m: re.Match[str]) -> str:
        field, val = m.group(1), m.group(2)
        if val.startswith('"') or '"' in val:
            return m.group(0)
        return '{0}="{1}"'.format(field, val.replace('"', '\\"'))

    return _SPL_COLON_FIELD.sub(_repl, spl or "")


def dedupe_search_field_clauses(spl: str) -> str:
    """Keep the first ``field=`` clause per field in the search portion (before ``|``)."""
    s = (spl or "").strip()
    if not s:
        return s
    pipe_idx = s.find("|")
    head = s[:pipe_idx].strip() if pipe_idx >= 0 else s
    tail = s[pipe_idx:] if pipe_idx >= 0 else ""

    matches = list(_SEARCH_FIELD_CLAUSE.finditer(head))
    if len(matches) <= 1:
        return s

    seen: set[str] = set()
    remove_ranges: list[tuple[int, int]] = []
    for m in matches:
        field = m.group(1).lower()
        if field == "search":
            continue
        if field in seen:
            remove_ranges.append((m.start(), m.end()))
        else:
            seen.add(field)

    new_head = head
    for start, end in reversed(remove_ranges):
        new_head = new_head[:start] + new_head[end:]
    new_head = re.sub(r"\s+", " ", new_head).strip()
    if tail:
        return "{0} {1}".format(new_head, tail.strip()).strip()
    return new_head


def strip_redundant_boolean_and(spl: str) -> str:
    """Remove stray ``and``/``AND`` left after clause deduplication."""
    return re.sub(r"\s+\band\b\s+", " ", spl or "", flags=re.IGNORECASE)


def _safe_spl_alias(value: str) -> str:
    cleaned = re.sub(r"[^\w]", "_", (value or "").strip()) or "value"
    if cleaned[0].isdigit():
        return "v_{0}".format(cleaned)
    return cleaned


def ensure_search_generating_command(spl: str) -> str:
    """Prepend ``search`` when the SPL starts with bare ``field=value`` filters."""
    s = (spl or "").strip()
    if not s:
        return s
    if re.match(r"^search\b", s, re.IGNORECASE):
        return s
    if _IMPLICIT_SEARCH_START.match(s):
        if s.startswith("|"):
            s = s.lstrip("|").strip()
        return "search " + s
    return s


def fix_field_equals_in_pipe_clauses(spl: str) -> str:
    """
    Fix LLM filter syntax inside pipe commands.

    ``stats count by index=firewall`` and ``table index=firewall`` are invalid —
    aggregation commands expect field *names*, not ``field=value`` pairs.
    """
    s = (spl or "").strip()
    if "|" not in s:
        return s
    parts = [p.strip() for p in s.split("|") if p.strip()]
    if not parts:
        return s

    head = ensure_search_generating_command(parts[0])
    out: list[str] = [head]
    for seg in parts[1:]:
        if not _AGG_COMMAND_PREFIX.match(seg):
            out.append(seg)
            continue
        seg = re.sub(
            r"\bas\s+(\w+)=(\S+)",
            lambda m: "as {0}".format(_safe_spl_alias(m.group(2))),
            seg,
            flags=re.IGNORECASE,
        )
        seg = re.sub(
            r"\bas\s+(\w+)=\"([^\"]*)\"",
            lambda m: "as {0}".format(_safe_spl_alias(m.group(2))),
            seg,
            flags=re.IGNORECASE,
        )

        def _fix_by_clause(m: re.Match[str]) -> str:
            body = _FIELD_EQ_TOKEN.sub(lambda t: t.group(1), m.group(1))
            return "by {0}".format(body.strip())

        seg = re.sub(r"\bby\b\s+([^|]+?)(?=\s*\||$)", _fix_by_clause, seg, flags=re.IGNORECASE)

        cmd = seg.split(None, 1)[0].lower()
        if cmd in ("table", "top", "rare", "fields"):
            seg = _FIELD_EQ_TOKEN.sub(lambda t: t.group(1), seg)
        out.append(seg)
    return " | ".join(out)


def fix_spl_quoted_string_escapes(spl: str) -> str:
    """
    Normalize backslashes inside SPL double-quoted literals.

    Splunk rejects a lone ``\\`` before the closing quote. LLM output often uses
    Windows paths with bad escaping; forward slashes are valid in search literals.
    """
    if not spl or '"' not in spl:
        return spl or ""

    out: list[str] = []
    i = 0
    n = len(spl)
    while i < n:
        if spl[i] != '"':
            out.append(spl[i])
            i += 1
            continue
        out.append('"')
        i += 1
        decoded: list[str] = []
        while i < n:
            ch = spl[i]
            if ch == "\\":
                if i + 1 >= n:
                    i += 1
                    break
                nxt = spl[i + 1]
                if nxt == '"':
                    i += 1
                    break
                if nxt == "\\":
                    decoded.append("\\")
                    i += 2
                else:
                    decoded.append("\\")
                    decoded.append(nxt)
                    i += 2
                continue
            if ch == '"':
                break
            decoded.append(ch)
            i += 1
        text = "".join(decoded).rstrip("\\")
        if "\\" in text:
            text = text.replace("\\", "/")
        text = text.replace("\\", "\\\\").replace('"', '\\"')
        out.append(text)
        out.append('"')
        if i < n and spl[i] == '"':
            i += 1
    return "".join(out)


def discourage_values_aggregation(spl: str) -> str:
    """Replace ``stats values()`` with ``dc()`` for readable aggregate rows."""

    def _repl(m: re.Match[str]) -> str:
        field = (m.group(1) or "").strip()
        alias = (m.group(2) or "").strip()
        safe = re.sub(r"[^\w]", "_", field) or "field"
        if alias:
            return "dc({0}) as {1}".format(field, alias)
        return "dc({0}) as unique_{1}".format(field, safe)

    return _VALUES_IN_STATS.sub(_repl, spl or "")


def sanitize_spl_syntax(spl: str) -> str:
    """Apply generic syntax-only normalizations (no index/field name hardcoding)."""
    s = re.sub(r"\s+", " ", (spl or "").strip()).strip()
    s = strip_time_range_from_spl(s)
    s = strip_spl_backticks(s)
    if s.startswith("| search"):
        s = s[1:].strip()
    s = ensure_search_generating_command(s)
    s = quote_spl_colon_field_values(s)
    s = dedupe_search_field_clauses(s)
    s = strip_redundant_boolean_and(s)
    s = fix_field_equals_in_pipe_clauses(s)
    s = discourage_values_aggregation(s)
    s = fix_spl_quoted_string_escapes(s)
    return s
