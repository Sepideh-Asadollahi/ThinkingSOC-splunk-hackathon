"""Unit tests for SAIA cloud config auto-repair helpers."""

from splunk.saia_config_repair import (
    is_saia_configs_repair_error,
    kv_needs_repair,
    merge_saia_configs,
)


def test_is_saia_configs_repair_error():
    assert is_saia_configs_repair_error("local variable 'configs' referenced before assignment")
    assert is_saia_configs_repair_error("SCS configs are not available properly for on-prem stack")
    assert not is_saia_configs_repair_error("connection refused")


def test_kv_needs_repair_empty_tenant():
    assert kv_needs_repair({"tenant_name": "", "scs_token": "x", "encoded_onboarding_data": "y"})
    assert not kv_needs_repair(
        {
            "tenant_name": "t",
            "tenant_hostname": "t.api.scs.splunk.com",
            "scs_region": "sin10",
            "service_principal": "sp",
            "scs_token": "tok",
            "scs_token_expiry": "1",
            "encoded_onboarding_data": "data",
        }
    )


def test_merge_saia_configs_from_jwt(monkeypatch):
    monkeypatch.setattr("splunk.saia_config_repair.parse_saia_log_defaults", lambda: {})
    token = (
        "eyJhbGciOiJIUzI1NiJ9."
        "eyJ0ZW5hbnQiOiJ0ZW5hbnQtYSIsInN1YiI6InNwLTEyMyJ9."
        "sig"
    )
    merged = merge_saia_configs(
        {
            "scs_token": token,
            "scs_token_expiry": "999",
            "encoded_onboarding_data": "onboard",
            "tenant_name": "",
            "tenant_hostname": "",
            "scs_region": "sin10",
            "service_principal": "",
        }
    )
    assert merged["tenant_name"] == "tenant-a"
    assert merged["service_principal"] == "sp-123"
    assert merged["tenant_hostname"] == "tenant-a.api.splunk.scs.splunk.com"
