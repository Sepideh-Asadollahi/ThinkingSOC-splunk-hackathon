"""VirusTotal API v3 parsing — fixtures aligned with official docs examples."""

from services.threat_intel.threat_intel_compact import compact_threat_intel_for_analysis
from services.threat_intel.virustotal_schema import (
    VT_TYPE_DOMAIN,
    VT_TYPE_FILE,
    VT_TYPE_IP,
    VT_TYPE_URL,
    build_vt_summary,
    extract_vt_object,
    normalize_last_analysis_stats,
    stats_imply_malicious,
    stats_imply_suspicious,
)


def test_build_vt_summary_ip_official_shape() -> None:
    # Minimal excerpt from https://docs.virustotal.com/reference/ip-object
    api = {
        "data": {
            "id": "31.139.365.245",
            "type": "ip_address",
            "links": {"self": "https://www.virustotal.com/api/v3/ip_addresses/31.139.365.245"},
            "attributes": {
                "last_analysis_date": 1671691600,
                "last_analysis_stats": {
                    "harmless": 5,
                    "malicious": 0,
                    "suspicious": 0,
                    "timeout": 0,
                    "undetected": 0,
                },
                "reputation": 0,
                "tags": [],
                "total_votes": {"harmless": 0, "malicious": 0},
            },
        }
    }
    s = build_vt_summary(api)
    assert s is not None
    assert s["type"] == VT_TYPE_IP
    assert s["id"] == "31.139.365.245"
    assert s["last_analysis_stats"]["harmless"] == 5
    assert "categories" not in s


def test_build_vt_summary_url_includes_categories() -> None:
    api = {
        "data": {
            "id": "661q6ceqa60e4qaf1998qa8aa8q6d8daq4c51qc2qfqc5fcd6d885700c0acee3b",
            "type": "url",
            "links": {"self": "https://www.virustotal.com/ui/urls/abc"},
            "attributes": {
                "last_analysis_stats": {
                    "harmless": 64,
                    "malicious": 7,
                    "suspicious": 0,
                    "timeout": 0,
                    "undetected": 9,
                },
                "reputation": -44,
                "categories": {"BitDefender": "business"},
                "tags": ["base64-embedded"],
                "total_votes": {"harmless": 0, "malicious": 1},
            },
        }
    }
    s = build_vt_summary(api)
    assert s is not None
    assert s["type"] == VT_TYPE_URL
    assert s["categories"]["BitDefender"] == "business"
    assert stats_imply_malicious(s["last_analysis_stats"])


def test_build_vt_summary_file_extra_stat_keys() -> None:
    api = {
        "data": {
            "id": "abc" * 16,
            "type": "file",
            "links": {"self": "https://www.virustotal.com/ui/files/abc"},
            "attributes": {
                "md5": "d" * 32,
                "sha256": "a" * 64,
                "last_analysis_stats": {
                    "harmless": 0,
                    "malicious": 42,
                    "suspicious": 1,
                    "timeout": 0,
                    "undetected": 10,
                    "confirmed-timeout": 0,
                    "failure": 0,
                    "type-unsupported": 2,
                },
                "reputation": -10,
                "tags": ["trojan"],
                "total_votes": {"harmless": 0, "malicious": 3},
            },
        }
    }
    s = build_vt_summary(api)
    assert s is not None
    assert s["type"] == VT_TYPE_FILE
    assert s["md5"] == "d" * 32
    assert s["last_analysis_stats"]["type-unsupported"] == 2
    assert "categories" not in s


def test_build_vt_summary_domain() -> None:
    api = {
        "data": {
            "id": "evil.example",
            "type": "domain",
            "links": {"self": "https://www.virustotal.com/api/v3/domains/evil.example"},
            "attributes": {
                "last_analysis_stats": {
                    "harmless": 0,
                    "malicious": 5,
                    "suspicious": 0,
                    "timeout": 0,
                    "undetected": 0,
                },
                "reputation": -12,
                "categories": {"Dr.Web": "malware"},
                "tags": ["dga"],
                "total_votes": {"harmless": 0, "malicious": 1},
            },
        }
    }
    s = build_vt_summary(api)
    assert s is not None
    assert s["type"] == VT_TYPE_DOMAIN
    assert s["categories"]["Dr.Web"] == "malware"


def test_extract_vt_object_errors() -> None:
    obj, err = extract_vt_object(None)
    assert obj is None
    assert err == "empty_response"
    obj, err = extract_vt_object({"error": "x"})
    assert obj is None
    assert err == "missing_data"
    obj, err = extract_vt_object({"data": {"id": "x"}})
    assert obj is None
    assert err == "missing_attributes"


def test_normalize_stats_ip_ignores_file_only_keys() -> None:
    stats = normalize_last_analysis_stats(
        {
            "malicious": 1,
            "failure": 9,
            "type-unsupported": 3,
        },
        vt_type=VT_TYPE_IP,
    )
    assert stats["malicious"] == 1
    assert "failure" not in stats
    assert "type-unsupported" not in stats


def test_stats_imply_suspicious_only_when_no_malicious() -> None:
    assert stats_imply_suspicious({"suspicious": 2, "malicious": 0}) is True
    assert stats_imply_suspicious({"suspicious": 2, "malicious": 1}) is False


def test_build_vt_summary_returns_none_on_bad_envelope() -> None:
    assert build_vt_summary({}) is None
    assert build_vt_summary({"data": {}}) is None


def test_compact_preserves_vt_field_names() -> None:
    raw = {
        "virustotal": {
            "enabled": True,
            "requested": {"file_hashes": [], "ips": ["203.0.113.9"], "domains": [], "urls": []},
            "ips": {
                "203.0.113.9": {
                    "summary": {
                        "id": "203.0.113.9",
                        "type": "ip_address",
                        "last_analysis_stats": {
                            "harmless": 2,
                            "malicious": 12,
                            "suspicious": 1,
                            "timeout": 0,
                            "undetected": 3,
                        },
                        "reputation": -50,
                        "total_votes": {"harmless": 0, "malicious": 2},
                        "tags": ["malware"],
                    }
                }
            },
            "files": {},
            "domains": {},
            "urls": {},
        }
    }
    out = compact_threat_intel_for_analysis(raw)
    assert out is not None
    f = out["findings"][0]
    assert f["vt_type"] == "ip_address"
    assert f["last_analysis_stats"]["malicious"] == 12
    assert f["total_votes"]["malicious"] == 2
