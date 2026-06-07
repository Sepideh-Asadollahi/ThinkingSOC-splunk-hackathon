"""Read-only SQL validation for SOC Chat Text-to-SQL."""

from __future__ import annotations

import re
from typing import List

from ..sql_schema import ALLOWED_SQL_TABLES

_FORBIDDEN_SQL_RE = re.compile(
    r"(?i)\b("
    r"insert|update|delete|drop|truncate|alter|create|grant|revoke|copy|"
    r"execute|call|merge|replace|attach|detach|pragma"
    r")\b",
)

_FROM_JOIN_TABLE_RE = re.compile(
    r"(?i)\b(?:from|join)\s+([a-z_][a-z0-9_]*)",
)


def _strip_sql_comments(sql: str) -> str:
    s = re.sub(r"/\*[\s\S]*?\*/", " ", sql)
    s = re.sub(r"--[^\n]*", " ", s)
    return s.strip()


def validate_readonly_sql(
    sql: str,
    *,
    max_rows: int = 500,
    allowed_tables: frozenset[str] = ALLOWED_SQL_TABLES,
) -> str:
    """Validate and normalize a read-only SELECT. Raises ValueError on unsafe SQL."""
    raw = (sql or "").strip()
    if not raw:
        raise ValueError("empty SQL")

    if ";" in raw:
        raise ValueError("multiple statements not allowed")

    cleaned = _strip_sql_comments(raw)
    upper = cleaned.upper()
    if not upper.startswith("SELECT"):
        raise ValueError("only SELECT queries are allowed")

    if _FORBIDDEN_SQL_RE.search(cleaned):
        raise ValueError("forbidden SQL keyword")

    referenced: List[str] = []
    for m in _FROM_JOIN_TABLE_RE.finditer(cleaned):
        tbl = m.group(1).lower()
        referenced.append(tbl)
        if tbl not in allowed_tables:
            raise ValueError("table not allowed: {0}".format(tbl))

    if not referenced:
        raise ValueError("no table reference found")

    out = cleaned.rstrip()
    if not re.search(r"(?i)\blimit\b", out):
        out = "{0} LIMIT {1}".format(out, int(max_rows))
    return out
