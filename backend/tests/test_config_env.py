"""Settings loading from .env — empty optional values must not break startup."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic_settings import SettingsConfigDict

from config import Settings, _BACKEND_ROOT, get_settings

_TEST_ENV = _BACKEND_ROOT / ".env.test_empty"


def test_settings_empty_litellm_chat_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITELLM_CHAT_DEFAULT_TEMPERATURE", "")
    s = Settings(_env_file=None)
    assert s.litellm_chat_default_temperature is None


def test_settings_whitespace_litellm_chat_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITELLM_CHAT_DEFAULT_TEMPERATURE", "   ")
    s = Settings(_env_file=None)
    assert s.litellm_chat_default_temperature is None


def test_settings_numeric_litellm_chat_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITELLM_CHAT_DEFAULT_TEMPERATURE", "0.3")
    s = Settings(_env_file=None)
    assert s.litellm_chat_default_temperature == pytest.approx(0.3)


@pytest.mark.skipif(not _TEST_ENV.is_file(), reason="requires backend/.env.test_empty")
def test_settings_loads_env_test_empty_file(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.chdir(_BACKEND_ROOT)
    # Isolate from developer backend/.env
    class _TestSettings(Settings):
        model_config = SettingsConfigDict(
            env_file=str(_TEST_ENV),
            env_file_encoding="utf-8",
            extra="ignore",
        )

    s = _TestSettings()
    assert s.litellm_chat_default_temperature is None
