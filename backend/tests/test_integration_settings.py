from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config import Settings, clear_settings_cache, get_settings
from main import app
from services.platform import integration_settings as store


@pytest.fixture
def settings_store_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "data" / "integration_settings.json"
    monkeypatch.setattr(store, "_BACKEND_ROOT", tmp_path)
    monkeypatch.setattr(store, "_STORE_PATH", path)
    monkeypatch.setattr(store, "_LEGACY_STORE_PATH", tmp_path / "services" / "data" / "integration_settings.json")
    yield path
    clear_settings_cache()


def test_store_path_under_backend_root() -> None:
    assert store._BACKEND_ROOT.name == "backend"
    assert store._STORE_PATH == store._BACKEND_ROOT / "data" / "integration_settings.json"


def test_migrates_legacy_store_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backend_root = tmp_path / "backend"
    canonical = backend_root / "data" / "integration_settings.json"
    legacy = backend_root / "services" / "data" / "integration_settings.json"
    legacy.parent.mkdir(parents=True)
    canonical.parent.mkdir(parents=True)
    legacy.write_text(
        json.dumps(
            {
                "overrides": {"litellm_analysis_temperature": 0.7},
                "custom": [],
                "hidden_builtin": [],
            }
        ),
        encoding="utf-8",
    )
    canonical.write_text(
        json.dumps(
            {
                "overrides": {"litellm_api_key": "secret-key"},
                "custom": [],
                "hidden_builtin": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(store, "_BACKEND_ROOT", backend_root)
    monkeypatch.setattr(store, "_STORE_PATH", canonical)
    monkeypatch.setattr(store, "_LEGACY_STORE_PATH", legacy)

    store._migrate_legacy_store_if_needed()

    data = json.loads(canonical.read_text(encoding="utf-8"))
    assert data["overrides"]["litellm_analysis_temperature"] == 0.7
    assert data["overrides"]["litellm_api_key"] == "secret-key"
    assert not legacy.is_file()


@pytest.fixture
def client_integration(test_settings: Settings, settings_store_path: Path) -> TestClient:
    def _override() -> Settings:
        return test_settings

    app.dependency_overrides[get_settings] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_builtin_settings(client_integration: TestClient) -> None:
    r = client_integration.get("/api/v1/integrations/settings")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 10
    ids = {row["id"] for row in rows}
    assert "splunk_mgmt_url" in ids
    assert "litellm_model" in ids
    runbook_rows = [row for row in rows if row["category"] == "runbook"]
    assert {row["id"] for row in runbook_rows} == {
        "tsoc_runbook_enabled",
        "tsoc_runbook_autopilot_enabled",
        "tsoc_runbook_max_steps",
            "tsoc_runbook_default_manual_minutes",
            "tsoc_runbook_artifact_scan_limit",
            "tsoc_runbook_analyst_hourly_cost_usd",
            "tsoc_runbook_input_cost_per_1m_tokens",
            "tsoc_runbook_output_cost_per_1m_tokens",
        }


def test_runbook_builtin_rejects_out_of_range_value(
    client_integration: TestClient,
) -> None:
    response = client_integration.patch(
        "/api/v1/integrations/settings/tsoc_runbook_max_steps",
        json={"value": "4"},
    )
    assert response.status_code == 400
    assert "less than or equal to 3" in response.json()["detail"]


def test_update_builtin_persists_override(
    client_integration: TestClient, settings_store_path: Path
) -> None:
    r = client_integration.patch(
        "/api/v1/integrations/settings/splunk_mgmt_url",
        json={"value": "https://splunk.example:8089"},
    )
    assert r.status_code == 200
    assert r.json()["value"] == "https://splunk.example:8089"

    data = json.loads(settings_store_path.read_text(encoding="utf-8"))
    assert data["overrides"]["splunk_mgmt_url"] == "https://splunk.example:8089"


def test_update_builtin_ignores_metadata_fields(
    client_integration: TestClient, settings_store_path: Path
) -> None:
    """UI may send category/key/description; built-in PATCH applies value only."""
    r = client_integration.patch(
        "/api/v1/integrations/settings/litellm_analysis_temperature",
        json={
            "category": "litellm",
            "key": "LITELLM_ANALYSIS_TEMPERATURE",
            "value": "0.7",
            "description": "Temperature for Defender/Hunter/Judge.",
            "is_secret": False,
        },
    )
    assert r.status_code == 200
    assert r.json()["value"] == "0.7"


def test_create_custom_setting(client_integration: TestClient) -> None:
    r = client_integration.post(
        "/api/v1/integrations/settings",
        json={
            "id": "demo_webhook_url",
            "category": "custom",
            "key": "DEMO_WEBHOOK_URL",
            "value": "https://hooks.example/tsoc",
            "description": "Optional demo webhook",
        },
    )
    assert r.status_code == 201
    assert r.json()["id"] == "demo_webhook_url"

    listed = client_integration.get("/api/v1/integrations/settings").json()
    assert any(row["id"] == "demo_webhook_url" for row in listed)


def test_delete_custom_setting(client_integration: TestClient) -> None:
    client_integration.post(
        "/api/v1/integrations/settings",
        json={"id": "temp_flag", "key": "TEMP_FLAG", "value": "1"},
    )
    r = client_integration.delete("/api/v1/integrations/settings/temp_flag")
    assert r.status_code == 204
    listed = client_integration.get("/api/v1/integrations/settings").json()
    assert not any(row["id"] == "temp_flag" for row in listed)


def test_delete_builtin_forbidden(client_integration: TestClient) -> None:
    r = client_integration.delete("/api/v1/integrations/settings/litellm_model")
    assert r.status_code == 403
    listed = client_integration.get("/api/v1/integrations/settings").json()
    assert any(row["id"] == "litellm_model" for row in listed)
