"""Evidence field keys derived from normalized alert + Splunk result rows."""

from __future__ import annotations

from typing import Any, Dict, List


def build_evidence_refs(normalized: Dict[str, Any], splunk_results: List[Dict[str, Any]]) -> List[str]:
    """Field names present in normalized + first result row (Splunk-backed evidence only)."""
    keys: List[str] = []
    for k in sorted(normalized.keys()):
        sk = str(k)
        if not sk or sk.startswith("__mv_"):
            continue
        if sk not in keys:
            keys.append(sk)
    if splunk_results:
        for k in sorted(splunk_results[0].keys()):
            sk = str(k)
            if sk.startswith("__mv_"):
                continue
            if sk not in keys:
                keys.append(sk)
    return keys[:80]
