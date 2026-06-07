"""Normalize judge verdicts for downstream logic (e.g. FP vs needs work)."""

from __future__ import annotations

from typing import Any, List


def _norm_verdict(verdict: str) -> str:
    v = (verdict or "").strip().lower().replace(" ", "_").replace("-", "_")
    while "__" in v:
        v = v.replace("__", "_")
    return v


_FALSE_POSITIVE_LIKE = frozenset(
    {
        "false_positive",
        "fp",
        "likely_benign",
        "benign",
        "true_negative",
        "expected_behavior",
        "informational",
        "no_threat",
        "noise",
        "benign_true_positive",
    }
)


def verdict_implies_false_positive(verdict: str) -> bool:
    """
    Return True when the ticket should be treated as false positive / benign closure.

    Anything else (e.g. needs_investigation, true_positive, insufficient_data) is
    eligible for deeper investigation follow-up questions.
    """
    return _norm_verdict(verdict) in _FALSE_POSITIVE_LIKE


def sanitize_investigation_questions(raw: Any, *, max_items: int = 3) -> List[str]:
    """Turn LLM output into a clean list of non-empty strings."""
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    for x in raw:
        s = str(x).strip()
        if s and s not in out:
            out.append(s)
        if len(out) >= max_items:
            break
    return out


def investigation_questions_for_verdict(verdict: str, questions: Any) -> List[str]:
    """SOC follow-up questions only when the verdict is not FP/benign-like."""
    if verdict_implies_false_positive(verdict):
        return []
    return sanitize_investigation_questions(questions)
