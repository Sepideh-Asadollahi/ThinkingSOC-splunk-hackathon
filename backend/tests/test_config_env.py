"""Settings loading from .env — empty optional values must not break startup."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic_settings import SettingsConfigDict

from config import (
    Settings,
    _BACKEND_ROOT,
    _apply_persisted_setting_overrides,
    get_settings,
)

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


def test_litellm_rpm_defaults_to_30(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LITELLM_RPM", raising=False)
    monkeypatch.delenv("LITELLM_MAX_RETRIES", raising=False)
    monkeypatch.delenv("LITELLM_RETRY_BASE_SECONDS", raising=False)
    monkeypatch.delenv("LITELLM_RETRY_MAX_SECONDS", raising=False)
    s = Settings(_env_file=None)
    assert s.litellm_rpm == 30
    assert s.litellm_max_retries == 3
    assert s.litellm_retry_base_seconds == 5.0
    assert s.litellm_retry_max_seconds == 60.0


def test_explicit_env_value_wins_over_persisted_integration_override() -> None:
    base = Settings.model_construct(
        _fields_set={"litellm_api_key"},
        litellm_api_key="env-key",
    )

    merged = _apply_persisted_setting_overrides(
        base,
        {
            "litellm_api_key": "stored-key",
            "litellm_chat_default_temperature": 0.4,
        },
    )

    assert merged.litellm_api_key == "env-key"
    assert merged.litellm_chat_default_temperature == pytest.approx(0.4)


def test_persisted_override_applies_when_env_field_is_unset() -> None:
    base = Settings.model_construct(_fields_set=set())
    merged = _apply_persisted_setting_overrides(
        base,
        {"litellm_chat_default_temperature": 0.25},
    )
    assert merged.litellm_chat_default_temperature == pytest.approx(0.25)


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
