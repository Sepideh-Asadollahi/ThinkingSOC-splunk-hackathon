"""Tests for MITRE + Kill Chain framework mapping helpers."""

from services.soc_analysis.framework_mapping import (
    KILL_CHAIN_FRAMEWORK_LABEL,
    MITRE_FRAMEWORK_LABEL,
    default_dual_framework_fallback,
    ensure_mitre_and_kill_chain,
    is_kill_chain_framework,
    is_mitre_framework,
    parse_framework_mapping_items,
)


def test_framework_labels_detected() -> None:
    assert is_mitre_framework("MITRE ATT&CK")
    assert is_kill_chain_framework("Cyber Kill Chain")


def test_default_dual_fallback_has_both() -> None:
    items = default_dual_framework_fallback()
    assert len(items) == 2
    assert any(x.framework == MITRE_FRAMEWORK_LABEL for x in items)
    assert any(x.framework == KILL_CHAIN_FRAMEWORK_LABEL for x in items)


def test_ensure_adds_missing_kill_chain() -> None:
    only_mitre = parse_framework_mapping_items(
        [
            {
                "framework": "MITRE ATT&CK",
                "id": "T1110",
                "name": "Brute Force",
                "confidence": "medium",
                "rationale": "auth failures",
            }
        ]
    )
    out = ensure_mitre_and_kill_chain(only_mitre, normalized={"action": "login"})
    assert any(is_mitre_framework(x.framework) for x in out)
    assert any(is_kill_chain_framework(x.framework) for x in out)


def test_ensure_adds_missing_mitre() -> None:
    only_kc = parse_framework_mapping_items(
        [
            {
                "framework": "Cyber Kill Chain",
                "id": "KC-3",
                "name": "Delivery",
                "confidence": "low",
                "rationale": "phish",
            }
        ]
    )
    out = ensure_mitre_and_kill_chain(only_kc)
    assert any(is_mitre_framework(x.framework) for x in out)
    assert any(is_kill_chain_framework(x.framework) for x in out)
