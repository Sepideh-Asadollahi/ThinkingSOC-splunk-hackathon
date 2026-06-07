"""LLM-only alert routing (full alert payload + metadata)."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import Settings
from models.agentic_ops import AlertClassificationResult
from models.mcp import McpAlertContext
from services.alert.alert_classifier import classify_alert_unavailable
from services.llm.litellm_service import (
    LiteLLMNotConfiguredError,
    LiteLLMProviderError,
    litellm_chat_completion,
)

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "prompt_alert_classifier_system.md"

_TRACK_TO_PIPELINE = {
    "security": "security",
    "observability": "observability",
    "unknown": "manual_review",
}


def _normalize_exclusive_track(
    track: str,
    pipeline: str,
    secondary: Optional[str],
    reason: str,
) -> tuple[str, str, Optional[str], str]:
    """Enforce exactly one of security or observability (never dual/both)."""
    if track == "unknown" or pipeline == "manual_review":
        return "unknown", "manual_review", None, reason

    if track in ("both",) or pipeline == "dual":
        logger.warning("classifier_llm: dual/both rejected; coercing to single track")
        if secondary == "observability":
            chosen = "security"
        elif secondary == "security":
            chosen = "observability"
        else:
            chosen = "security"
        note = " Dual track rejected; routed exclusively to {0}.".format(chosen)
        return chosen, chosen, None, reason + note

    if track not in ("security", "observability"):
        raise ValueError("invalid track: {0}".format(track))

    expected = _TRACK_TO_PIPELINE[track]
    if pipeline != expected:
        pipeline = expected
    return track, pipeline, secondary, reason


def ensure_exclusive_classification(result: AlertClassificationResult) -> AlertClassificationResult:
    """Safety guard: never return dual/both from any classification path."""
    track, pipeline, secondary, reason = _normalize_exclusive_track(
        result.track,
        result.recommended_pipeline,
        result.secondary_track,
        result.reason,
    )
    if (
        track == result.track
        and pipeline == result.recommended_pipeline
        and secondary == result.secondary_track
        and reason == result.reason
    ):
        return result
    return result.model_copy(
        update={
            "track": track,
            "recommended_pipeline": pipeline,
            "secondary_track": secondary,
            "reason": reason,
        }
    )


@lru_cache(maxsize=1)
def load_alert_classifier_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8").strip()


def _llm_available(settings: Settings) -> bool:
    if not settings.tsoc_classifier_llm:
        return False
    if not (settings.litellm_model or "").strip():
        return False
    if not settings.litellm_api_key and not settings.litellm_api_base:
        return False
    return True


def _parse_llm_json(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
    return json.loads(raw.strip())


def _classification_from_llm(llm_data: Dict[str, Any]) -> AlertClassificationResult:
    track = llm_data.get("track")
    pipeline = llm_data.get("recommended_pipeline")
    if track is None and pipeline in _TRACK_TO_PIPELINE.values():
        for t, p in _TRACK_TO_PIPELINE.items():
            if p == pipeline:
                track = t
                break
    if track not in ("security", "observability", "both", "unknown"):
        raise ValueError("invalid track: {0}".format(track))
    if pipeline not in ("security", "observability", "dual", "manual_review"):
        pipeline = _TRACK_TO_PIPELINE.get(str(track), "manual_review")

    conf = llm_data.get("confidence", 0.7)
    try:
        conf_f = float(conf)
    except (TypeError, ValueError):
        conf_f = 0.7
    conf_f = max(0.0, min(1.0, conf_f))

    signals = llm_data.get("signals")
    if not isinstance(signals, list):
        signals = []
    else:
        signals = [str(s) for s in signals if str(s).strip()]

    reason = str(llm_data.get("reason") or "LLM classification.")
    needs_human = bool(llm_data.get("needs_human_routing", track == "unknown"))
    secondary = llm_data.get("secondary_track")
    if secondary not in ("security", "observability", None):
        secondary = None

    track, pipeline, secondary, reason = _normalize_exclusive_track(
        str(track),
        str(pipeline),
        secondary,
        reason,
    )

    return AlertClassificationResult(
        track=track,
        recommended_pipeline=pipeline,
        confidence=round(conf_f, 2),
        reason=reason,
        signals=signals,
        secondary_track=secondary,
        needs_human_routing=needs_human,
        classification_source="llm",
    )


def build_alert_classification_payload(
    *,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    splunk_results: List[Dict[str, Any]],
    sid: Optional[str] = None,
    mcp_context: Optional[McpAlertContext] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble the full alert document sent to the classifier LLM."""
    payload: Dict[str, Any] = {
        "search_name": search_name,
        "sid": sid,
        "normalized": normalized,
        "splunk_results": splunk_results,
        "splunk_result_count": len(splunk_results),
    }
    if mcp_context is not None:
        payload["splunk_mcp"] = mcp_context.model_dump(mode="json")
    if extra_metadata:
        payload["extra_metadata"] = extra_metadata
    return payload


def build_classifier_user_message(payload: Dict[str, Any]) -> str:
    return "Classify this Splunk alert using the full payload below:\n{0}".format(
        json.dumps(payload, ensure_ascii=False, default=str)
    )


async def _classify_with_llm(
    settings: Settings,
    payload: Dict[str, Any],
) -> AlertClassificationResult:
    out = await litellm_chat_completion(
        settings,
        messages=[
            {"role": "system", "content": load_alert_classifier_system_prompt()},
            {"role": "user", "content": build_classifier_user_message(payload)},
        ],
        temperature=0.1,
        max_tokens=512,
    )
    llm_data = _parse_llm_json(str(out.get("content") or ""))
    return _classification_from_llm(llm_data)


async def classify_alert_hybrid(
    settings: Settings,
    normalized: Dict[str, Any],
    search_name: Optional[str],
    splunk_results: List[Dict[str, Any]],
    extra_signals: List[str] | None = None,
    *,
    sid: Optional[str] = None,
    mcp_context: Optional[McpAlertContext] = None,
) -> AlertClassificationResult:
    """
    Classify alert via LLM using the complete normalized fields, all Splunk result
    rows, and optional MCP metadata. Falls back to manual_review when LLM is off
    or fails.
    """
    extra_metadata: Dict[str, Any] = {}
    if extra_signals:
        extra_metadata["legacy_extra_signals"] = extra_signals

    payload = build_alert_classification_payload(
        normalized=normalized,
        search_name=search_name,
        splunk_results=splunk_results,
        sid=sid,
        mcp_context=mcp_context,
        extra_metadata=extra_metadata or None,
    )

    if not _llm_available(settings):
        return classify_alert_unavailable()

    try:
        return ensure_exclusive_classification(await _classify_with_llm(settings, payload))
    except LiteLLMNotConfiguredError as e:
        logger.warning("classifier_llm not configured, fallback to manual_review: %s", e)
        return classify_alert_unavailable(reason=str(e))
    except LiteLLMProviderError as e:
        logger.warning(
            "classifier_llm provider error (%s) fallback to manual_review: %s",
            e.kind,
            e,
        )
        return classify_alert_unavailable(
            reason="{0} Manual routing required.".format(e),
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("classifier_llm invalid LLM output, fallback to manual_review: %s", e)
        return classify_alert_unavailable(
            reason="LLM classifier returned invalid output; manual routing required.",
        )
    except Exception as e:
        logger.warning("classifier_llm unexpected error fallback to manual_review: %s", e)
        return classify_alert_unavailable(
            reason="LLM classifier failed unexpectedly; manual routing required.",
        )
