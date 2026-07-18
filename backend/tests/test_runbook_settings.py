"""Focused configuration tests for the dedicated ThinkingSOC Lite settings surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from config import Settings
from models.integration_settings import IntegrationSettingUpdate
from services.platform import integration_settings as store


@pytest.fixture
def settings_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "integration_settings.json"
    monkeypatch.setattr(store, "_STORE_PATH", path)
    monkeypatch.setattr(store, "_LEGACY_STORE_PATH", tmp_path / "missing-legacy.json")
    return path


@pytest.fixture
def settings() -> Settings:
    return Settings(
        splunk_username="",
        splunk_password="",
        tsoc_postgres_dsn=None,
        litellm_api_key=None,
        litellm_api_base=None,
    )


def test_runbook_settings_are_builtin_and_grouped(
    settings: Settings, settings_store: Path
) -> None:
    rows = [row for row in store.list_integration_settings(settings) if row.category == "runbook"]
    assert {row.id for row in rows} == {
        "tsoc_runbook_enabled",
        "tsoc_runbook_autopilot_enabled",
        "tsoc_runbook_max_steps",
        "tsoc_runbook_default_manual_minutes",
        "tsoc_runbook_artifact_scan_limit",
        "tsoc_runbook_analyst_hourly_cost_usd",
        "tsoc_runbook_input_cost_per_1m_tokens",
        "tsoc_runbook_output_cost_per_1m_tokens",
    }
    assert all(row.builtin for row in rows)


def test_runbook_setting_rejects_invalid_value_without_persisting(
    settings: Settings, settings_store: Path
) -> None:
    with pytest.raises(ValueError, match="less than or equal to 3"):
        store.update_integration_setting(
            settings,
            "tsoc_runbook_max_steps",
            IntegrationSettingUpdate(value="4"),
        )
    assert not settings_store.exists()


def test_runbook_setting_persists_valid_override(
    settings: Settings, settings_store: Path
) -> None:
    row, changed = store.update_integration_setting(
        settings,
        "tsoc_runbook_default_manual_minutes",
        IntegrationSettingUpdate(value="30"),
    )
    assert changed is True
    assert row.value == "30"
    persisted = json.loads(settings_store.read_text(encoding="utf-8"))
    assert persisted["overrides"]["tsoc_runbook_default_manual_minutes"] == 30
    assert store.load_setting_overrides()["tsoc_runbook_default_manual_minutes"] == 30
