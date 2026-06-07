from __future__ import annotations

from graph_pipelines.demo_smart_analysis import _build_details


def test_build_details_sorts_contributing_alerts_chronologically():
    cluster = {
        "alerts": [
            {
                "alert_row_id": "ALERT-102",
                "name": "PsExec lateral movement",
                "timestamp": "2026-05-29T10:13:52Z",
                "status": "open",
                "risk_score": 78,
                "entity_identifiers": ["username:jdoe@corp.local"],
            },
            {
                "alert_row_id": "ALERT-090",
                "name": "Suspicious email link",
                "timestamp": "2026-05-25T06:13:51Z",
                "status": "closed",
                "risk_score": 55,
                "entity_identifiers": ["username:jdoe@corp.local"],
            },
            {
                "alert_row_id": "ALERT-091",
                "name": "Outbound C2 beacon",
                "timestamp": "2026-05-25T06:38:51Z",
                "status": "closed",
                "risk_score": 65,
                "entity_identifiers": ["ipv4:203.0.113.50"],
            },
        ]
    }
    report = {
        "title": "Demo campaign",
        "summary": "summary",
        "executive_summary": "exec",
        "attack_analysis_steps": [],
    }
    details = _build_details(cluster, report, [], {})
    ids = [a["alert_row_id"] for a in details["contributing_alerts"]]
    assert ids == ["ALERT-090", "ALERT-091", "ALERT-102"]
