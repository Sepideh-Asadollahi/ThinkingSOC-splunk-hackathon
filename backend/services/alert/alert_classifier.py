"""Fallback classification when the LLM router is unavailable."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.agentic_ops import AlertClassificationResult


def classify_alert_unavailable() -> AlertClassificationResult:
    """Return manual review when LiteLLM classification cannot run."""
    return AlertClassificationResult(
        track="unknown",
        recommended_pipeline="manual_review",
        confidence=0.0,
        reason="LLM classifier unavailable; manual routing required.",
        signals=[],
        needs_human_routing=True,
        classification_source="rules",
    )


def classify_alert(
    normalized: Dict[str, Any],
    search_name: str | None,
    splunk_results: List[Dict[str, Any]],
    extra_signals: List[str] | None = None,
) -> AlertClassificationResult:
    """Legacy entry point — keyword routing removed; defers to unavailable fallback."""
    _ = (normalized, search_name, splunk_results, extra_signals)
    return classify_alert_unavailable()
