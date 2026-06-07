"""VirusTotal API v3 JSON fixtures (shapes from official docs)."""

from __future__ import annotations

from typing import Any, Dict


def vt_ip_response(ip: str = "203.0.113.9", *, malicious: int = 12) -> Dict[str, Any]:
    return {
        "data": {
            "id": ip,
            "type": "ip_address",
            "links": {"self": f"https://www.virustotal.com/api/v3/ip_addresses/{ip}"},
            "attributes": {
                "last_analysis_date": 1671691600,
                "last_analysis_stats": {
                    "harmless": 2,
                    "malicious": malicious,
                    "suspicious": 1 if malicious else 0,
                    "timeout": 0,
                    "undetected": 3,
                },
                "reputation": -50 if malicious else 0,
                "tags": ["malware"] if malicious else [],
                "total_votes": {"harmless": 0, "malicious": 1 if malicious else 0},
            },
        }
    }


def vt_domain_response(domain: str = "evil.example") -> Dict[str, Any]:
    return {
        "data": {
            "id": domain,
            "type": "domain",
            "links": {"self": f"https://www.virustotal.com/api/v3/domains/{domain}"},
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


def vt_file_response(sha256: str) -> Dict[str, Any]:
    return {
        "data": {
            "id": sha256,
            "type": "file",
            "links": {"self": f"https://www.virustotal.com/ui/files/{sha256}"},
            "attributes": {
                "md5": "d" * 32,
                "sha256": sha256,
                "last_analysis_stats": {
                    "harmless": 0,
                    "malicious": 40,
                    "suspicious": 0,
                    "timeout": 0,
                    "undetected": 5,
                    "confirmed-timeout": 0,
                    "failure": 0,
                    "type-unsupported": 0,
                },
                "reputation": -20,
                "tags": ["trojan"],
                "total_votes": {"harmless": 0, "malicious": 2},
            },
        }
    }


def vt_url_response(url_id: str = "abc123") -> Dict[str, Any]:
    return {
        "data": {
            "id": url_id,
            "type": "url",
            "links": {"self": f"https://www.virustotal.com/api/v3/urls/{url_id}"},
            "attributes": {
                "url": "http://evil.example/path",
                "last_analysis_stats": {
                    "harmless": 10,
                    "malicious": 3,
                    "suspicious": 0,
                    "timeout": 0,
                    "undetected": 2,
                },
                "reputation": -10,
                "categories": {"BitDefender": "malware"},
                "tags": [],
                "total_votes": {"harmless": 0, "malicious": 0},
            },
        }
    }
