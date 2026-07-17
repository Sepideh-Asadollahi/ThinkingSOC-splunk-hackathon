"""LiteLLM API and service layer tests (network calls mocked)."""

from __future__ import annotations

from collections import deque
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings, get_settings
from main import app
from services.llm.litellm_service import (
    LiteLLMProviderError,
    _map_litellm_exception,
    _wait_for_litellm_rpm_slot,
    litellm_chat_completion,
    provider_error_http_status,
)


@pytest.fixture
def client_llm_configured(test_settings: Settings):
    """Explicit API key so status reports configured."""

    def _override() -> Settings:
        return test_settings.model_copy(
            update={
                "litellm_model": "gpt-4o-mini",
                "litellm_api_key": "sk-test",
                "litellm_api_base": None,
                "litellm_timeout_seconds": 30.0,
            }
        )

    app.dependency_overrides[get_settings] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_llm_status(client: TestClient) -> None:
    r = client.get("/api/v1/llm/status")
    assert r.status_code == 200
    data = r.json()
    assert "litellm_model" in data
    assert data["litellm_rpm"] == 30
    assert data["litellm_max_retries"] == 3
    assert data["litellm_api_key_configured"] is False


def test_llm_chat_requires_bearer_when_token_set(client_with_token: TestClient) -> None:
    r = client_with_token.post(
        "/api/v1/llm/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 401


def test_llm_chat_success_mocked(client_llm_configured: TestClient) -> None:
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(content="hello"),
            finish_reason="stop",
        )
    ]
    mock_resp.model = "gpt-4o-mini"
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 1
    mock_usage.completion_tokens = 2
    mock_usage.total_tokens = 3
    mock_resp.usage = mock_usage

    async def _acompletion(**kwargs):
        return mock_resp

    with patch("litellm.acompletion", new_callable=AsyncMock) as m:
        m.side_effect = _acompletion
        r = client_llm_configured.post(
            "/api/v1/llm/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["content"] == "hello"
    assert body["model"] == "gpt-4o-mini"
    assert body["usage"]["total_tokens"] == 3


def test_map_litellm_connection_error() -> None:
    import litellm

    exc = litellm.exceptions.InternalServerError(
        message="Nvidia_nimException - Connection error.",
        llm_provider="nvidia_nim",
        model="meta/llama-3.1-70b-instruct",
    )
    mapped = _map_litellm_exception(exc)
    assert isinstance(mapped, LiteLLMProviderError)
    assert mapped.kind == "connection"
    assert "disconnected" in str(mapped).lower() or "unreachable" in str(mapped).lower()
    assert provider_error_http_status(mapped) == 502


def test_map_litellm_busy_provider_error() -> None:
    import litellm

    exc = litellm.exceptions.ServiceUnavailableError(
        message="Nvidia_nimException - ResourceExhausted: All workers are busy",
        llm_provider="nvidia_nim",
        model="deepseek-ai/deepseek-v4-flash",
    )
    mapped = _map_litellm_exception(exc)
    assert mapped.kind == "provider_busy"
    assert mapped.retryable is True
    assert provider_error_http_status(mapped) == 503
    assert "ResourceExhausted" not in str(mapped)


def test_llm_chat_provider_connection_error_mocked(client_llm_configured: TestClient) -> None:
    import litellm

    async def _acompletion(**kwargs):
        raise litellm.exceptions.InternalServerError(
            message="Nvidia_nimException - Connection error.",
            llm_provider="nvidia_nim",
            model="gpt-4o-mini",
        )

    with patch("litellm.acompletion", new_callable=AsyncMock) as m:
        m.side_effect = _acompletion
        r = client_llm_configured.post(
            "/api/v1/llm/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )
    assert r.status_code == 502
    detail = r.json()["detail"]
    assert "LLM provider" in detail
    assert "Connection error" not in detail


def test_litellm_chat_completion_accepts_system_and_user_messages():
    import asyncio

    settings = Settings(
        splunk_mgmt_url="https://x",
        litellm_model="gpt-4o-mini",
        litellm_api_key="k",
    )
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="ok"), finish_reason="stop")]
    mock_resp.model = "gpt-4o-mini"
    mock_resp.usage = None

    async def _acompletion(**kwargs):
        return mock_resp

    async def _run():
        return await litellm_chat_completion(
            settings,
            [{"role": "system", "content": "sys"}, {"role": "user", "content": "ping"}],
        )

    with patch("litellm.acompletion", new_callable=AsyncMock) as m:
        m.side_effect = _acompletion
        out = asyncio.run(_run())
    assert out["content"] == "ok"
    call_kw = m.call_args.kwargs
    assert call_kw["model"] == "gpt-4o-mini"
    assert len(call_kw["messages"]) == 2


def test_litellm_rpm_limiter_waits_for_sliding_window() -> None:
    import asyncio

    async def _run() -> None:
        with (
            patch(
                "services.llm.litellm_service._rpm_timestamps",
                new=deque(),
            ),
            patch(
                "services.llm.litellm_service.time.monotonic",
                side_effect=[0.0, 0.0, 0.0, 60.1],
            ),
            patch(
                "services.llm.litellm_service.asyncio.sleep",
                new_callable=AsyncMock,
            ) as sleep,
        ):
            await _wait_for_litellm_rpm_slot(2)
            await _wait_for_litellm_rpm_slot(2)
            await _wait_for_litellm_rpm_slot(2)

        sleep.assert_awaited_once_with(60.0)

    asyncio.run(_run())


def test_litellm_retries_busy_provider_then_succeeds() -> None:
    import asyncio
    import litellm

    settings = Settings(
        splunk_mgmt_url="https://x",
        litellm_model="nvidia_nim/deepseek-ai/deepseek-v4-flash",
        litellm_api_key="k",
        litellm_max_retries=3,
        litellm_retry_base_seconds=5,
        litellm_retry_max_seconds=60,
    )
    busy = litellm.exceptions.ServiceUnavailableError(
        message="ResourceExhausted: All workers are busy",
        llm_provider="nvidia_nim",
        model="deepseek-ai/deepseek-v4-flash",
    )
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content="ok"), finish_reason="stop")]
    response.model = "deepseek-ai/deepseek-v4-flash"
    response.usage = None

    async def _run():
        return await litellm_chat_completion(
            settings,
            [{"role": "user", "content": "ping"}],
        )

    with (
        patch(
            "services.llm.litellm_service._wait_for_litellm_rpm_slot",
            new_callable=AsyncMock,
        ) as rpm_slot,
        patch(
            "services.llm.litellm_service.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep,
        patch(
            "litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=[busy, busy, response],
        ) as completion,
    ):
        out = asyncio.run(_run())

    assert out["content"] == "ok"
    assert completion.await_count == 3
    assert rpm_slot.await_count == 3
    assert sleep.await_args_list == [call(5.0), call(10.0)]
    assert completion.await_args_list[0].kwargs["max_retries"] == 0


def test_litellm_stops_after_three_retries() -> None:
    import asyncio
    import litellm

    settings = Settings(
        splunk_mgmt_url="https://x",
        litellm_model="nvidia_nim/deepseek-ai/deepseek-v4-flash",
        litellm_api_key="k",
        litellm_max_retries=3,
        litellm_retry_base_seconds=5,
        litellm_retry_max_seconds=60,
    )

    def _busy() -> Exception:
        return litellm.exceptions.ServiceUnavailableError(
            message="ResourceExhausted: All workers are busy",
            llm_provider="nvidia_nim",
            model="deepseek-ai/deepseek-v4-flash",
        )

    async def _run():
        return await litellm_chat_completion(
            settings,
            [{"role": "user", "content": "ping"}],
        )

    with (
        patch(
            "services.llm.litellm_service._wait_for_litellm_rpm_slot",
            new_callable=AsyncMock,
        ),
        patch(
            "services.llm.litellm_service.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep,
        patch(
            "litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=[_busy(), _busy(), _busy(), _busy()],
        ) as completion,
    ):
        with pytest.raises(LiteLLMProviderError) as exc_info:
            asyncio.run(_run())

    assert exc_info.value.kind == "provider_busy"
    assert exc_info.value.attempts == 4
    assert completion.await_count == 4
    assert sleep.await_args_list == [call(5.0), call(10.0), call(20.0)]
