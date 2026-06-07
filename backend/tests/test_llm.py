"""LiteLLM API and service layer tests (network calls mocked)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings, get_settings
from main import app
from services.llm.litellm_service import (
    LiteLLMProviderError,
    _map_litellm_exception,
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

    from services.llm.litellm_service import litellm_chat_completion

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
