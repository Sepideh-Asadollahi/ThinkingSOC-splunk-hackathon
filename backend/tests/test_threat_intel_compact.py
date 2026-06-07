"""Compact threat-intel shaping for SOC analysis."""

from services.threat_intel.threat_intel_compact import compact_threat_intel_for_analysis


def test_compact_filters_clean_iocs() -> None:
    raw = {
        "virustotal": {
            "enabled": True,
            "requested": {"file_hashes": [], "ips": ["8.8.8.8"], "domains": [], "urls": []},
            "ips": {
                "8.8.8.8": {
                    "error": None,
                    "summary": {
                        "type": "ip_address",
                        "last_analysis_stats": {"malicious": 0, "suspicious": 0, "harmless": 60},
                        "reputation": 100,
                        "total_votes": {"harmless": 10, "malicious": 0},
                    },
                }
            },
            "files": {},
            "domains": {},
            "urls": {},
        }
    }
    out = compact_threat_intel_for_analysis(raw)
    assert out is not None
    assert out["status"] == "no_significant_hits"
    assert out["findings"] == []
    assert len(out["iocs"]) == 1
    assert out["iocs"][0]["ioc"] == "8.8.8.8"
    assert out["iocs"][0]["verdict"] == "harmless"


def test_compact_keeps_malicious_iocs() -> None:
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
                            "malicious": 12,
                            "suspicious": 1,
                            "harmless": 2,
                            "undetected": 0,
                            "timeout": 0,
                        },
                        "reputation": -50,
                        "tags": ["malware", "c2"],
                        "total_votes": {"harmless": 0, "malicious": 1},
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
    assert out["status"] == "ok"
    assert len(out["findings"]) == 1
    f = out["findings"][0]
    assert f["ioc"] == "203.0.113.9"
    assert f["vt_type"] == "ip_address"
    assert f["verdict"] == "malicious"
    assert f["last_analysis_stats"]["malicious"] == 12
    assert f["tags"] == ["malware", "c2"]
    assert len(out["iocs"]) == 1
    assert out["iocs"][0]["link"] is None or out["iocs"][0]["ioc"] == "203.0.113.9"


def test_compact_disabled_vt() -> None:
    out = compact_threat_intel_for_analysis({"virustotal": {"enabled": False}})
    assert out is not None
    assert out["status"] == "unavailable"
    assert out["findings"] == []


def test_compact_significant_via_negative_reputation() -> None:
    raw = {
        "virustotal": {
            "enabled": True,
            "requested": {"file_hashes": [], "ips": ["198.51.100.7"], "domains": [], "urls": []},
            "ips": {
                "198.51.100.7": {
                    "summary": {
                        "type": "ip_address",
                        "last_analysis_stats": {
                            "malicious": 0,
                            "suspicious": 0,
                            "harmless": 50,
                        },
                        "reputation": -80,
                        "total_votes": {"harmless": 0, "malicious": 0},
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
    assert len(out["findings"]) == 1
    assert out["findings"][0]["reputation"] == -80


def test_compact_significant_via_community_votes() -> None:
    raw = {
        "virustotal": {
            "enabled": True,
            "requested": {"file_hashes": [], "ips": ["203.0.113.1"], "domains": [], "urls": []},
            "ips": {
                "203.0.113.1": {
                    "summary": {
                        "type": "ip_address",
                        "last_analysis_stats": {"malicious": 0, "suspicious": 0, "harmless": 10},
                        "reputation": 0,
                        "total_votes": {"harmless": 0, "malicious": 3},
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
    assert out["findings"][0]["total_votes"]["malicious"] == 3


def test_compact_passthrough_already_compact() -> None:
    compact = {
        "status": "ok",
        "source": "virustotal",
        "findings": [{"ioc": "1.2.3.4", "ioc_type": "ip", "verdict": "malicious"}],
        "note": "x",
    }
    out = compact_threat_intel_for_analysis(compact)
    assert out is not None
    assert out["findings"] == compact["findings"]
    assert out["iocs"] == compact["findings"]
