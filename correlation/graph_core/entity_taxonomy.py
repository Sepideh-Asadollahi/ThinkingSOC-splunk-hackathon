"""Classify ``type:value`` entity identifiers for correlation (no alert-specific hardcoding).

Aligns with Neo4j graph roles:
- **anchor** — Identity / Asset (users, hosts, accounts, devices)
- **indicator** — IOC (IPs, domains, hashes, URLs, …)
- **other** — unknown prefixes still cluster via shared-entity graph union
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Any, FrozenSet

# Default prefix sets (lowercase, without trailing colon). Override via Settings.
DEFAULT_ANCHOR_PREFIXES: FrozenSet[str] = frozenset(
    {
        "username",
        "user",
        "email",
        "hostname",
        "host",
        "asset",
        "device",
        "computer",
        "src_host",
        "dest_host",
        "principal",
        "account",
        "service",
        "application",
    }
)
DEFAULT_IDENTITY_ANCHOR_PREFIXES: FrozenSet[str] = frozenset(
    {
        "username",
        "user",
        "email",
        "account",
        "principal",
    }
)

DEFAULT_INDICATOR_PREFIXES: FrozenSet[str] = frozenset(
    {
        "ipv4",
        "ipv6",
        "ip",
        "domain",
        "url",
        "hash",
        "md5",
        "sha1",
        "sha256",
        "sha512",
        "file",
        "cve",
        "mutex",
        "registry",
        "certificate",
        "ja3",
        "ja3s",
    }
)


class EntityKind(str, Enum):
    ANCHOR = "anchor"
    INDICATOR = "indicator"
    OTHER = "other"


def _parse_prefix_list(raw: str | None) -> FrozenSet[str] | None:
    if not raw or not str(raw).strip():
        return None
    parts = {p.strip().lower().rstrip(":") for p in str(raw).split(",") if p.strip()}
    return frozenset(parts) if parts else None


@lru_cache
def _configured_prefix_sets() -> tuple[FrozenSet[str], FrozenSet[str]]:
    try:
        from correlation_config import get_settings

        settings = get_settings()
        anchor_override = _parse_prefix_list(
            getattr(settings, "correlation_anchor_entity_prefixes", None)
        )
        indicator_override = _parse_prefix_list(
            getattr(settings, "correlation_indicator_entity_prefixes", None)
        )
    except Exception:
        anchor_override = None
        indicator_override = None
    return (
        anchor_override or DEFAULT_ANCHOR_PREFIXES,
        indicator_override or DEFAULT_INDICATOR_PREFIXES,
    )


def entity_prefix(identifier: str) -> str:
    text = str(identifier).strip()
    if ":" not in text:
        return ""
    return text.split(":", 1)[0].lower()


def entity_kind(identifier: str) -> EntityKind:
    prefix = entity_prefix(identifier)
    if not prefix:
        return EntityKind.OTHER
    anchor_prefixes, indicator_prefixes = _configured_prefix_sets()
    if prefix in indicator_prefixes:
        return EntityKind.INDICATOR
    if prefix in anchor_prefixes:
        return EntityKind.ANCHOR
    return EntityKind.OTHER


def is_anchor_entity(identifier: str) -> bool:
    return entity_kind(identifier) == EntityKind.ANCHOR


def is_indicator_entity(identifier: str) -> bool:
    return entity_kind(identifier) == EntityKind.INDICATOR


def is_identity_anchor(identifier: str) -> bool:
    return (
        is_anchor_entity(identifier)
        and entity_prefix(identifier) in DEFAULT_IDENTITY_ANCHOR_PREFIXES
    )


def is_asset_anchor(identifier: str) -> bool:
    return is_anchor_entity(identifier) and not is_identity_anchor(identifier)


def anchor_entities_from_identifiers(identifiers: list[str] | set[str] | None) -> set[str]:
    return {str(e) for e in (identifiers or []) if e and is_anchor_entity(str(e))}


def anchor_entities_on_alert(alert: dict[str, Any]) -> set[str]:
    return anchor_entities_from_identifiers(alert.get("entity_identifiers") or [])


def is_indicator_only_alert(alert: dict[str, Any]) -> bool:
    entities = [str(e) for e in (alert.get("entity_identifiers") or []) if e]
    if not entities:
        return False
    return all(is_indicator_entity(e) for e in entities)


def cluster_has_anchor(cluster: dict[str, Any]) -> bool:
    return any(anchor_entities_on_alert(a) for a in cluster.get("alerts") or [])


def cluster_is_indicator_only_singleton(cluster: dict[str, Any]) -> bool:
    alerts = cluster.get("alerts") or []
    if len(alerts) != 1:
        return False
    return is_indicator_only_alert(alerts[0])


def clusters_share_anchor_entities(
    cluster_a: dict[str, Any],
    cluster_b: dict[str, Any],
) -> bool:
    sets: list[set[str]] = []
    for cluster in (cluster_a, cluster_b):
        combined: set[str] = set()
        for alert in cluster.get("alerts") or []:
            combined.update(anchor_entities_on_alert(alert))
        sets.append(combined)
    return bool(sets[0] & sets[1])


def primary_anchor_display(cluster: dict[str, Any]) -> str:
    """Best-effort label for titles (first anchor value on any contributing alert)."""
    for alert in cluster.get("alerts") or []:
        for entity in alert.get("entity_identifiers") or []:
            text = str(entity)
            if is_anchor_entity(text) and ":" in text:
                return text.split(":", 1)[-1]
    return ""
