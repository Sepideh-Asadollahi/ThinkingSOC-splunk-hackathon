from __future__ import annotations

from services.alert.graph_correlation import (
    build_entity_identifiers,
    derive_alert_row_id,
    normalize_row_data,
)


def test_derive_alert_row_id_stable():
    a = derive_alert_row_id(sid="scheduler__x", search_name="Test Alert")
    b = derive_alert_row_id(sid="scheduler__x", search_name="Test Alert")
    c = derive_alert_row_id(sid="scheduler__y", search_name="Test Alert")
    assert a == b
    assert a.startswith("ALERT-")
    assert a != c


def test_build_entity_identifiers_from_alert_fields():
    row = normalize_row_data(
        {
            "host": "DESKTOP-BRUCE",
            "user": r"WAYNECORPINC\bwayne",
            "src_ip": "203.0.113.111",
            "dest_ip": "198.51.100.10",
            "src": "10.1.1.15",
        }
    )
    entities = build_entity_identifiers(row, enrichment=None)
    assert "hostname:DESKTOP-BRUCE" in entities
    assert "username:WAYNECORPINC\\bwayne" in entities
    assert "ipv4:203.0.113.111" in entities
    assert "ipv4:198.51.100.10" in entities
    assert "ipv4:10.1.1.15" not in entities
