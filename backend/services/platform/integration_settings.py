"""Persist and list integration settings for the Splunk connection UI."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from config import Settings
from models.integration_settings import (
    IntegrationSettingCreate,
    IntegrationSettingRecord,
    IntegrationSettingUpdate,
    SettingCategory,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_STORE_PATH = _BACKEND_ROOT / "data" / "integration_settings.json"
_LEGACY_STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "integration_settings.json"
_SECRET_MASK = "••••••••"
_CUSTOM_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

_BUILTIN: List[Dict[str, Any]] = [
    # Splunk REST
    {
        "id": "splunk_mgmt_url",
        "category": "splunk_rest",
        "key": "SPLUNK_MGMT_URL",
        "field": "splunk_mgmt_url",
        "description": "Splunk management port REST base URL.",
    },
    {
        "id": "splunk_username",
        "category": "splunk_rest",
        "key": "SPLUNK_USERNAME",
        "field": "splunk_username",
        "description": "Splunk REST username.",
    },
    {
        "id": "splunk_password",
        "category": "splunk_rest",
        "key": "SPLUNK_PASSWORD",
        "field": "splunk_password",
        "is_secret": True,
        "description": "Splunk REST password.",
    },
    {
        "id": "splunk_verify_ssl",
        "category": "splunk_rest",
        "key": "SPLUNK_VERIFY_SSL",
        "field": "splunk_verify_ssl",
        "value_type": "bool",
        "description": "Verify TLS certificates for Splunk REST.",
    },
    {
        "id": "tsoc_splunk_app",
        "category": "splunk_rest",
        "key": "TSOC_SPLUNK_APP",
        "field": "tsoc_splunk_app",
        "description": "Splunk app namespace for REST oneshot (servicesNS).",
    },
    {
        "id": "tsoc_splunk_owner",
        "category": "splunk_rest",
        "key": "TSOC_SPLUNK_OWNER",
        "field": "tsoc_splunk_owner",
        "description": "Splunk owner for servicesNS REST.",
    },
    # PostgreSQL / inventory
    {
        "id": "tsoc_postgres_dsn",
        "category": "postgres",
        "key": "TSOC_POSTGRES_DSN",
        "field": "tsoc_postgres_dsn",
        "is_secret": True,
        "description": "PostgreSQL DSN for inventory and TSOC record storage.",
    },
    # LiteLLM
    {
        "id": "litellm_model",
        "category": "litellm",
        "key": "LITELLM_MODEL",
        "field": "litellm_model",
        "description": "LiteLLM model id.",
    },
    {
        "id": "litellm_api_key",
        "category": "litellm",
        "key": "LITELLM_API_KEY",
        "field": "litellm_api_key",
        "is_secret": True,
        "description": "LiteLLM API key (optional if provider env vars are set).",
    },
    {
        "id": "litellm_api_base",
        "category": "litellm",
        "key": "LITELLM_API_BASE",
        "field": "litellm_api_base",
        "description": "Optional LiteLLM API base URL.",
    },
    {
        "id": "litellm_timeout_seconds",
        "category": "litellm",
        "key": "LITELLM_TIMEOUT_SECONDS",
        "field": "litellm_timeout_seconds",
        "value_type": "float",
        "description": "LiteLLM HTTP timeout (seconds).",
    },
    {
        "id": "litellm_rpm",
        "category": "litellm",
        "key": "LITELLM_RPM",
        "field": "litellm_rpm",
        "value_type": "int",
        "description": "Process-wide maximum LLM requests per minute.",
    },
    {
        "id": "litellm_max_retries",
        "category": "litellm",
        "key": "LITELLM_MAX_RETRIES",
        "field": "litellm_max_retries",
        "value_type": "int",
        "description": "Transient provider retries after the initial LLM attempt (0..10).",
    },
    {
        "id": "litellm_retry_base_seconds",
        "category": "litellm",
        "key": "LITELLM_RETRY_BASE_SECONDS",
        "field": "litellm_retry_base_seconds",
        "value_type": "float",
        "description": "Initial delay for exponential LLM retry backoff.",
    },
    {
        "id": "litellm_retry_max_seconds",
        "category": "litellm",
        "key": "LITELLM_RETRY_MAX_SECONDS",
        "field": "litellm_retry_max_seconds",
        "value_type": "float",
        "description": "Maximum delay between transient LLM retries.",
    },
    {
        "id": "litellm_analysis_max_tokens",
        "category": "litellm",
        "key": "LITELLM_ANALYSIS_MAX_TOKENS",
        "field": "litellm_analysis_max_tokens",
        "value_type": "int",
        "description": "Max tokens for structured SOC analysis calls.",
    },
    {
        "id": "litellm_analysis_temperature",
        "category": "litellm",
        "key": "LITELLM_ANALYSIS_TEMPERATURE",
        "field": "litellm_analysis_temperature",
        "value_type": "float",
        "description": "Temperature for Defender/Hunter/Judge.",
    },
    {
        "id": "litellm_chat_default_temperature",
        "category": "litellm",
        "key": "LITELLM_CHAT_DEFAULT_TEMPERATURE",
        "field": "litellm_chat_default_temperature",
        "value_type": "float",
        "description": "Default temperature for POST /llm/chat.",
    },
    # Splunk MCP
    {
        "id": "tsoc_mcp_enabled",
        "category": "splunk_mcp",
        "key": "TSOC_MCP_ENABLED",
        "field": "tsoc_mcp_enabled",
        "value_type": "bool",
        "description": "Enable Splunk MCP Server integration.",
    },
    {
        "id": "splunk_mcp_url",
        "category": "splunk_mcp",
        "key": "SPLUNK_MCP_URL",
        "field": "splunk_mcp_url",
        "description": "MCP endpoint URL (defaults to SPLUNK_MGMT_URL/services/mcp).",
    },
    {
        "id": "splunk_mcp_token",
        "category": "splunk_mcp",
        "key": "SPLUNK_MCP_TOKEN",
        "field": "splunk_mcp_token",
        "is_secret": True,
        "description": "Splunk MCP bearer token.",
    },
    {
        "id": "splunk_mcp_verify_ssl",
        "category": "splunk_mcp",
        "key": "SPLUNK_MCP_VERIFY_SSL",
        "field": "splunk_mcp_verify_ssl",
        "value_type": "bool",
        "description": "Verify TLS for MCP HTTP calls.",
    },
    {
        "id": "splunk_mcp_timeout_seconds",
        "category": "splunk_mcp",
        "key": "SPLUNK_MCP_TIMEOUT_SECONDS",
        "field": "splunk_mcp_timeout_seconds",
        "value_type": "float",
        "description": "MCP HTTP timeout (seconds).",
    },
    {
        "id": "tsoc_mcp_correlation_enabled",
        "category": "splunk_mcp",
        "key": "TSOC_MCP_CORRELATION_ENABLED",
        "field": "tsoc_mcp_correlation_enabled",
        "value_type": "bool",
        "description": "Run MCP correlation enrichment on alerts.",
    },
    {
        "id": "tsoc_spl_use_rest_predict",
        "category": "splunk_mcp",
        "key": "TSOC_SPL_USE_REST_PREDICT",
        "field": "tsoc_spl_use_rest_predict",
        "value_type": "bool",
        "description": "Generate investigation SPL via Splunk REST /predict (UI write_spl path).",
    },
    {
        "id": "tsoc_spl_predict_timeout_seconds",
        "category": "splunk_mcp",
        "key": "TSOC_SPL_PREDICT_TIMEOUT_SECONDS",
        "field": "tsoc_spl_predict_timeout_seconds",
        "value_type": "float",
        "description": "Max seconds to poll /predict chathistory.",
    },
    {
        "id": "tsoc_execute_investigation_spl",
        "category": "splunk_mcp",
        "key": "TSOC_EXECUTE_INVESTIGATION_SPL",
        "field": "tsoc_execute_investigation_spl",
        "value_type": "bool",
        "description": "Run investigation SPL via MCP splunk_run_query (All Time).",
    },
    {
        "id": "tsoc_spl_execute_via_mcp",
        "category": "splunk_mcp",
        "key": "TSOC_SPL_EXECUTE_VIA_MCP",
        "field": "tsoc_spl_execute_via_mcp",
        "value_type": "bool",
        "description": "Prefer MCP splunk_run_query over REST oneshot for execute.",
    },
    {
        "id": "tsoc_investigation_spl_time_window",
        "category": "splunk_mcp",
        "key": "TSOC_INVESTIGATION_SPL_TIME_WINDOW",
        "field": "tsoc_investigation_spl_time_window",
        "description": "All Time label (SPL earliest=1 latest=now; REST earliest_time=0). Ignored at runtime.",
    },
    {
        "id": "tsoc_mcp_saia_spl_only",
        "category": "splunk_mcp",
        "key": "TSOC_MCP_SAIA_SPL_ONLY",
        "field": "tsoc_mcp_saia_spl_only",
        "value_type": "bool",
        "description": "Debug POST /mcp/spl-generate only: saia_generate_spl spl_only flag.",
    },
    {
        "id": "tsoc_mcp_saia_optimize_spl",
        "category": "splunk_mcp",
        "key": "TSOC_MCP_SAIA_OPTIMIZE_SPL",
        "field": "tsoc_mcp_saia_optimize_spl",
        "value_type": "bool",
        "description": "Debug /mcp/spl-generate: run saia_optimize_spl after generate.",
    },
    {
        "id": "tsoc_mcp_saia_explain_spl",
        "category": "splunk_mcp",
        "key": "TSOC_MCP_SAIA_EXPLAIN_SPL",
        "field": "tsoc_mcp_saia_explain_spl",
        "value_type": "bool",
        "description": "Debug /mcp/spl-generate: run saia_explain_spl after optimize.",
    },
    {
        "id": "tsoc_analysis_saia_spl_review",
        "category": "splunk_mcp",
        "key": "TSOC_ANALYSIS_SAIA_SPL_REVIEW",
        "field": "tsoc_analysis_saia_spl_review",
        "value_type": "bool",
        "description": "SOC Analysis (default on): SAIA optimize+explain on each investigation SPL via MCP.",
        "default": True,
    },
    {
        "id": "tsoc_spl_llm_review",
        "category": "splunk_mcp",
        "key": "TSOC_SPL_LLM_REVIEW",
        "field": "tsoc_spl_llm_review",
        "value_type": "bool",
        "description": "LiteLLM review/fix SPL after parser errors (predict path).",
    },
    # VirusTotal
    {
        "id": "virustotal_api_key",
        "category": "virustotal",
        "key": "VIRUSTOTAL_API_KEY",
        "field": "virustotal_api_key",
        "is_secret": True,
        "description": "VirusTotal API v3 key.",
    },
    {
        "id": "virustotal_base_url",
        "category": "virustotal",
        "key": "VIRUSTOTAL_BASE_URL",
        "field": "virustotal_base_url",
        "description": "VirusTotal API base URL.",
    },
    {
        "id": "virustotal_timeout_seconds",
        "category": "virustotal",
        "key": "VIRUSTOTAL_TIMEOUT_SECONDS",
        "field": "virustotal_timeout_seconds",
        "value_type": "float",
        "description": "VirusTotal HTTP timeout (seconds).",
    },
    {
        "id": "virustotal_enable",
        "category": "virustotal",
        "key": "VIRUSTOTAL_ENABLE",
        "field": "virustotal_enable",
        "value_type": "bool",
        "description": "Enable VirusTotal enrichment.",
    },
    {
        "id": "virustotal_max_iocs",
        "category": "virustotal",
        "key": "VIRUSTOTAL_MAX_IOCS",
        "field": "virustotal_max_iocs",
        "value_type": "int",
        "description": "Max IOCs per analysis.",
    },
    # Ingest / analysis
    {
        "id": "tsoc_ingest_token",
        "category": "ingest",
        "key": "TSOC_INGEST_TOKEN",
        "field": "tsoc_ingest_token",
        "is_secret": True,
        "description": "Optional Bearer token for ingest routes.",
    },
    {
        "id": "tsoc_ingest_auto_analyze",
        "category": "ingest",
        "key": "TSOC_INGEST_AUTO_ANALYZE",
        "field": "tsoc_ingest_auto_analyze",
        "value_type": "bool",
        "description": "Run triage in background after ingest (controlled by TSOC_INGEST_AUTO_ANALYZE in backend/.env).",
    },
    {
        "id": "tsoc_ingest_auto_analyze_pipeline",
        "category": "ingest",
        "key": "TSOC_INGEST_AUTO_ANALYZE_PIPELINE",
        "field": "tsoc_ingest_auto_analyze_pipeline",
        "description": "triage | route | none",
    },
    {
        "id": "tsoc_classifier_llm",
        "category": "analysis",
        "key": "TSOC_CLASSIFIER_LLM",
        "field": "tsoc_classifier_llm",
        "value_type": "bool",
        "description": "Classify alerts via LLM (full payload); manual_review when LLM unavailable.",
    },
    # ThinkingSOC Forge
    {
        "id": "tsoc_runbook_enabled",
        "category": "runbook",
        "key": "TSOC_RUNBOOK_ENABLED",
        "field": "tsoc_runbook_enabled",
        "value_type": "bool",
        "description": "Enable compile, approval, and guided reuse operations for ThinkingSOC Forge.",
    },
    {
        "id": "tsoc_runbook_autopilot_enabled",
        "category": "runbook",
        "key": "TSOC_RUNBOOK_AUTOPILOT_ENABLED",
        "field": "tsoc_runbook_autopilot_enabled",
        "value_type": "bool",
        "description": "Enable bounded Runbook Agent orchestration; human approval and execution gates remain fixed.",
    },
    {
        "id": "tsoc_runbook_max_steps",
        "category": "runbook",
        "key": "TSOC_RUNBOOK_MAX_STEPS",
        "field": "tsoc_runbook_max_steps",
        "value_type": "int",
        "description": "Maximum ordered runbook steps accepted from the compiler (1..3).",
    },
    {
        "id": "tsoc_runbook_default_manual_minutes",
        "category": "runbook",
        "key": "TSOC_RUNBOOK_DEFAULT_MANUAL_MINUTES",
        "field": "tsoc_runbook_default_manual_minutes",
        "value_type": "int",
        "description": "Default visible manual-investigation baseline used for reuse metrics (5..120 minutes).",
    },
    {
        "id": "tsoc_runbook_artifact_scan_limit",
        "category": "runbook",
        "key": "TSOC_RUNBOOK_ARTIFACT_SCAN_LIMIT",
        "field": "tsoc_runbook_artifact_scan_limit",
        "value_type": "int",
        "description": "Bounded append-only artifact lookup limit (50..1000 records per type).",
    },
    {
        "id": "tsoc_runbook_analyst_hourly_cost_usd",
        "category": "runbook",
        "key": "TSOC_RUNBOOK_ANALYST_HOURLY_COST_USD",
        "field": "tsoc_runbook_analyst_hourly_cost_usd",
        "value_type": "float",
        "description": "Loaded SOC analyst hourly cost used for projected Shadow Replay savings.",
    },
    {
        "id": "tsoc_runbook_input_cost_per_1m_tokens",
        "category": "runbook",
        "key": "TSOC_RUNBOOK_INPUT_COST_PER_1M_TOKENS",
        "field": "tsoc_runbook_input_cost_per_1m_tokens",
        "value_type": "float",
        "description": "Configured compiler-model input cost per one million tokens.",
    },
    {
        "id": "tsoc_runbook_output_cost_per_1m_tokens",
        "category": "runbook",
        "key": "TSOC_RUNBOOK_OUTPUT_COST_PER_1M_TOKENS",
        "field": "tsoc_runbook_output_cost_per_1m_tokens",
        "value_type": "float",
        "description": "Configured compiler-model output cost per one million tokens.",
    },
]

_BUILTIN_BY_ID = {row["id"]: row for row in _BUILTIN}

# Splunk CSV inventory lookups were removed; legacy UI rows may still say "inventory".
_LEGACY_INVENTORY_BUILTIN_IDS = frozenset(
    {
        "tsoc_inventory_source",
        "tsoc_lookup_users",
        "tsoc_lookup_assets",
        "tsoc_lookup_relationships",
    }
)


def _normalize_category(category: str) -> SettingCategory:
    if category == "inventory":
        return "custom"
    if category in {
        "splunk_rest",
        "splunk_mcp",
        "litellm",
        "postgres",
        "virustotal",
        "ingest",
        "analysis",
        "runbook",
        "custom",
    }:
        return category  # type: ignore[return-value]
    return "custom"


def _default_store() -> Dict[str, Any]:
    return {"overrides": {}, "custom": [], "hidden_builtin": []}


def _parse_store_file(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return _default_store()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_store()
    if not isinstance(raw, dict):
        return _default_store()
    store = _default_store()
    for key in store:
        val = raw.get(key)
        if key == "overrides" and isinstance(val, dict):
            store["overrides"] = {str(k): v for k, v in val.items()}
        elif key == "custom" and isinstance(val, list):
            store["custom"] = [x for x in val if isinstance(x, dict)]
        elif key == "hidden_builtin" and isinstance(val, list):
            store["hidden_builtin"] = [str(x) for x in val]
    return store


def _merge_store_data(primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two stores; primary wins on key conflicts."""
    merged = _default_store()
    merged["overrides"] = {
        **(secondary.get("overrides") or {}),
        **(primary.get("overrides") or {}),
    }
    custom_by_id: Dict[str, Dict[str, Any]] = {}
    for row in (secondary.get("custom") or []) + (primary.get("custom") or []):
        if isinstance(row, dict) and row.get("id"):
            custom_by_id[str(row["id"])] = row
    merged["custom"] = list(custom_by_id.values())
    hidden = list(secondary.get("hidden_builtin") or []) + list(primary.get("hidden_builtin") or [])
    merged["hidden_builtin"] = sorted(set(str(x) for x in hidden))
    return merged


def _migrate_legacy_store_if_needed() -> None:
    """One-time merge from backend/services/data into backend/data."""
    if not _LEGACY_STORE_PATH.is_file():
        return
    if _LEGACY_STORE_PATH.resolve() == _STORE_PATH.resolve():
        return
    canonical = _parse_store_file(_STORE_PATH)
    legacy = _parse_store_file(_LEGACY_STORE_PATH)
    _write_store(_merge_store_data(canonical, legacy))
    try:
        _LEGACY_STORE_PATH.unlink()
    except OSError:
        pass


def _read_store() -> Dict[str, Any]:
    _migrate_legacy_store_if_needed()
    return _parse_store_file(_STORE_PATH)


def _write_store(store: Dict[str, Any]) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_setting_overrides() -> Dict[str, Any]:
    """Field-name overrides applied when building Settings (see config.get_settings)."""
    store = _read_store()
    out: Dict[str, Any] = {}
    for setting_id, raw in store.get("overrides", {}).items():
        if setting_id in _LEGACY_INVENTORY_BUILTIN_IDS:
            continue
        meta = _BUILTIN_BY_ID.get(setting_id)
        if not meta:
            continue
        field = meta["field"]
        try:
            out[field] = _coerce_value(raw, meta.get("value_type"))
        except ValueError:
            continue
    return out


def _coerce_value(raw: Any, value_type: Optional[str]) -> Any:
    if value_type is None:
        if raw is None:
            return None
        return str(raw)
    text = str(raw).strip().lower() if raw is not None else ""
    if value_type == "bool":
        return text in ("1", "true", "yes", "on")
    if value_type == "int":
        return int(str(raw).strip())
    if value_type == "float":
        return float(str(raw).strip())
    return str(raw)


def _serialize_value(value: Any, value_type: Optional[str]) -> str:
    if value is None:
        return ""
    if value_type == "bool":
        return "true" if bool(value) else "false"
    return str(value)


def _field_value(settings: Settings, field: str) -> Any:
    return getattr(settings, field)


def _builtin_record(settings: Settings, meta: Dict[str, Any], store: Dict[str, Any]) -> IntegrationSettingRecord:
    field = meta["field"]
    value_type = meta.get("value_type")
    overrides = store.get("overrides", {})
    if meta["id"] in overrides:
        current = _coerce_value(overrides[meta["id"]], value_type)
    else:
        current = _field_value(settings, field)

    is_secret = bool(meta.get("is_secret"))
    configured = bool(current) if is_secret else True
    display = _serialize_value(current, value_type)
    if is_secret and configured:
        display = _SECRET_MASK

    return IntegrationSettingRecord(
        id=meta["id"],
        category=meta["category"],
        key=meta["key"],
        value=display,
        description=meta.get("description"),
        is_secret=is_secret,
        builtin=True,
        env_var=meta["key"],
        configured=configured,
    )


def _custom_record(row: Dict[str, Any]) -> IntegrationSettingRecord:
    is_secret = bool(row.get("is_secret"))
    raw_value = str(row.get("value") or "")
    configured = bool(raw_value) if is_secret else True
    display = _SECRET_MASK if is_secret and configured else raw_value
    return IntegrationSettingRecord(
        id=str(row["id"]),
        category=_normalize_category(str(row.get("category") or "custom")),
        key=str(row.get("key") or row["id"]),
        value=display,
        description=row.get("description"),
        is_secret=is_secret,
        builtin=False,
        env_var=None,
        configured=configured,
    )


def list_integration_settings(settings: Settings) -> List[IntegrationSettingRecord]:
    store = _read_store()
    rows: List[IntegrationSettingRecord] = []
    for meta in _BUILTIN:
        if meta["id"] in _LEGACY_INVENTORY_BUILTIN_IDS:
            continue
        rows.append(_builtin_record(settings, meta, store))
    for row in store.get("custom") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        rows.append(_custom_record(row))
    return rows


def get_integration_setting(settings: Settings, setting_id: str) -> IntegrationSettingRecord:
    for row in list_integration_settings(settings):
        if row.id == setting_id:
            return row
    raise KeyError(setting_id)


def create_integration_setting(
    settings: Settings, body: IntegrationSettingCreate
) -> IntegrationSettingRecord:
    store = _read_store()
    setting_id = body.id.strip()
    if not _CUSTOM_ID_RE.match(setting_id):
        raise ValueError("id must be lowercase letters, digits, and underscores")
    if setting_id in _BUILTIN_BY_ID:
        raise ValueError("id conflicts with a built-in setting")
    custom = store.get("custom") or []
    if any(str(r.get("id")) == setting_id for r in custom):
        raise ValueError("setting already exists")
    row = {
        "id": setting_id,
        "category": body.category,
        "key": body.key.strip(),
        "value": body.value,
        "description": body.description,
        "is_secret": body.is_secret,
    }
    custom.append(row)
    store["custom"] = custom
    _write_store(store)
    return _custom_record(row)


def update_integration_setting(
    settings: Settings, setting_id: str, body: IntegrationSettingUpdate
) -> Tuple[IntegrationSettingRecord, bool]:
    """Returns (record, settings_changed). settings_changed means get_settings cache should clear."""
    store = _read_store()
    changed_settings = False

    if setting_id in _BUILTIN_BY_ID:
        meta = _BUILTIN_BY_ID[setting_id]
        overrides = dict(store.get("overrides") or {})
        if body.value is not None:
            raw = body.value.strip()
            if meta.get("is_secret") and raw in ("", _SECRET_MASK):
                pass
            else:
                candidate = _coerce_value(raw, meta.get("value_type"))
                try:
                    validated = Settings.model_validate(
                        {**settings.model_dump(), meta["field"]: candidate}
                    )
                except ValidationError as exc:
                    raise ValueError(
                        f"invalid value for {meta['key']}: {exc.errors()[0]['msg']}"
                    ) from exc
                overrides[setting_id] = getattr(validated, meta["field"])
                changed_settings = True
        store["overrides"] = overrides
        _write_store(store)
        return _builtin_record(settings.model_copy(update=load_setting_overrides()), meta, store), changed_settings

    custom = list(store.get("custom") or [])
    idx = next((i for i, r in enumerate(custom) if str(r.get("id")) == setting_id), None)
    if idx is None:
        raise KeyError(setting_id)

    row = dict(custom[idx])
    if body.category is not None:
        row["category"] = body.category
    if body.key is not None:
        row["key"] = body.key.strip()
    if body.description is not None:
        row["description"] = body.description
    if body.is_secret is not None:
        row["is_secret"] = body.is_secret
    if body.value is not None:
        raw = body.value.strip()
        if row.get("is_secret") and raw in ("", _SECRET_MASK):
            pass
        else:
            row["value"] = raw
    custom[idx] = row
    store["custom"] = custom
    _write_store(store)
    return _custom_record(row), changed_settings


def delete_integration_setting(setting_id: str) -> bool:
    """Delete a custom setting. Built-in rows are fixed (value-only via PATCH)."""
    if setting_id in _BUILTIN_BY_ID:
        raise ValueError("built-in settings cannot be deleted")

    store = _read_store()
    changed_settings = False

    custom = [r for r in (store.get("custom") or []) if str(r.get("id")) != setting_id]
    if len(custom) == len(store.get("custom") or []):
        raise KeyError(setting_id)
    store["custom"] = custom
    _write_store(store)
    return changed_settings
