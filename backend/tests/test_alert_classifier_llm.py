"""LLM-only alert classifier tests."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

from config import Settings
from services.alert.alert_classifier import classify_alert, classify_alert_unavailable
from services.alert.alert_classifier_llm import (
    build_alert_classification_payload,
    classify_alert_hybrid,
)


def _llm_response(track: str, pipeline: str, **extra: object) -> dict:
    body = {
        "track": track,
        "recommended_pipeline": pipeline,
        "confidence": 0.9,
        "reason": "test",
        "signals": ["test"],
        "needs_human_routing": False,
    }
    body.update(extra)
    return {"content": json.dumps(body)}


def test_classify_alert_fallback_is_manual_review() -> None:
    out = classify_alert({"cpu": 99}, "High CPU", [])
    assert out.track == "unknown"
    assert out.recommended_pipeline == "manual_review"
    assert out.needs_human_routing is True


def test_build_payload_includes_all_rows_and_mcp() -> None:
    rows = [{"host": "a", "cpu": 1}, {"host": "b", "cpu": 2}]
    payload = build_alert_classification_payload(
        normalized={"service": "api"},
        search_name="CPU spike",
        splunk_results=rows,
        sid="sid-1",
    )
    assert payload["sid"] == "sid-1"
    assert payload["splunk_result_count"] == 2
    assert len(payload["splunk_results"]) == 2


def test_classify_hybrid_uses_llm_with_full_payload() -> None:
    async def _run() -> None:
        settings = Settings(
            tsoc_classifier_llm=True,
            litellm_model="gpt-4o-mini",
            litellm_api_key="sk-test",
        )
        rows = [{"host": "DESKTOP-BRUCE", "CommandLine": "powershell.exe -enc ..."}]
        with patch(
            "services.alert.alert_classifier_llm.litellm_chat_completion",
            new_callable=AsyncMock,
        ) as m:
            m.return_value = _llm_response("security", "security", reason="Sysmon PowerShell")
            out = await classify_alert_hybrid(
                settings,
                {"user": "WAYNECORPINC\\bwayne"},
                "Sysmon: PowerShell Download Activity (t8372)",
                rows,
                sid="sid-ps-1",
            )
        assert out.classification_source == "llm"
        assert out.track == "security"
        user_msg = m.await_args.kwargs["messages"][-1]["content"]
        assert "sid-ps-1" in user_msg
        assert "DESKTOP-BRUCE" in user_msg
        assert "splunk_result_count" in user_msg

    asyncio.run(_run())


def test_classify_hybrid_falls_back_when_llm_disabled() -> None:
    async def _run() -> None:
        settings = Settings(tsoc_classifier_llm=False)
        out = await classify_alert_hybrid(settings, {}, "alert", [])
        assert out == classify_alert_unavailable()

    asyncio.run(_run())


def test_classify_hybrid_rejects_dual_from_llm() -> None:
    async def _run() -> None:
        settings = Settings(
            tsoc_classifier_llm=True,
            litellm_model="gpt-4o-mini",
            litellm_api_key="sk-test",
        )
        dual_json = (
            '{"track":"both","recommended_pipeline":"dual",'
            '"confidence":0.8,"reason":"mixed","signals":["mixed"],'
            '"secondary_track":"observability","needs_human_routing":false}'
        )
        with patch(
            "services.alert.alert_classifier_llm.litellm_chat_completion",
            new_callable=AsyncMock,
        ) as m:
            m.return_value = {"content": dual_json}
            out = await classify_alert_hybrid(settings, {"host": "x"}, "alert", [])
        assert out.track == "security"
        assert out.recommended_pipeline == "security"
        assert out.recommended_pipeline != "dual"

    asyncio.run(_run())


def test_classify_hybrid_falls_back_on_llm_error() -> None:
    async def _run() -> None:
        settings = Settings(
            tsoc_classifier_llm=True,
            litellm_model="gpt-4o-mini",
            litellm_api_key="sk-test",
        )
        with patch(
            "services.alert.alert_classifier_llm.litellm_chat_completion",
            new_callable=AsyncMock,
            side_effect=ValueError("bad json"),
        ):
            out = await classify_alert_hybrid(settings, {}, "alert", [])
        assert out.recommended_pipeline == "manual_review"
        assert "invalid output" in out.reason.lower()

    asyncio.run(_run())


def test_classify_hybrid_falls_back_on_provider_connection_error() -> None:
    async def _run() -> None:
        from services.llm.litellm_service import LiteLLMProviderError

        settings = Settings(
            tsoc_classifier_llm=True,
            litellm_model="nvidia_nim/openai/gpt-oss-120b",
            litellm_api_key="sk-test",
        )
        provider_err = LiteLLMProviderError(
            "LLM provider disconnected during the request. The upstream service may be overloaded "
            "or restarting; retry in a moment.",
            kind="connection",
        )
        with patch(
            "services.alert.alert_classifier_llm.litellm_chat_completion",
            new_callable=AsyncMock,
            side_effect=provider_err,
        ):
            out = await classify_alert_hybrid(settings, {}, "alert", [])
        assert out.recommended_pipeline == "manual_review"
        assert out.needs_human_routing is True
        assert "disconnected" in out.reason.lower()
        assert "manual routing" in out.reason.lower()

    asyncio.run(_run())
