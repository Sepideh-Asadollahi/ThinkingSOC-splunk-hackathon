"""MITRE ATT&CK + Cyber Kill Chain framework mapping helpers."""

from __future__ import annotations

from typing import Any, Dict, List

from models.analysis import FrameworkMappingItem

MITRE_FRAMEWORK_LABEL = "MITRE ATT&CK"
KILL_CHAIN_FRAMEWORK_LABEL = "Cyber Kill Chain"

KILL_CHAIN_PHASES = (
    ("KC-1", "Reconnaissance"),
    ("KC-2", "Weaponization"),
    ("KC-3", "Delivery"),
    ("KC-4", "Exploitation"),
    ("KC-5", "Installation"),
    ("KC-6", "Command and Control"),
    ("KC-7", "Actions on Objectives"),
)


def _norm_framework(value: str) -> str:
    return (value or "").strip().lower().replace("&", "and")


def is_mitre_framework(framework: str) -> bool:
    n = _norm_framework(framework)
    return "mitre" in n or "att&ck" in n or "attck" in n


def is_kill_chain_framework(framework: str) -> bool:
    n = _norm_framework(framework)
    return "kill chain" in n or n == "killchain"


def parse_framework_mapping_items(raw: Any) -> List[FrameworkMappingItem]:
    if not isinstance(raw, list):
        return []
    out: List[FrameworkMappingItem] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        conf = item.get("confidence", "low")
        if conf not in ("high", "medium", "low"):
            conf = "low"
        fw = str(item.get("framework") or MITRE_FRAMEWORK_LABEL).strip() or MITRE_FRAMEWORK_LABEL
        entry_id = str(item.get("id") or "").strip()
        name = str(item.get("name") or "").strip()
        if not entry_id and not name:
            continue
        out.append(
            FrameworkMappingItem(
                framework=fw,
                id=entry_id or name,
                name=name or entry_id,
                confidence=conf,
                rationale=str(item.get("rationale") or ""),
            )
        )
    return out


def default_dual_framework_fallback() -> List[FrameworkMappingItem]:
    return [
        FrameworkMappingItem(
            framework=MITRE_FRAMEWORK_LABEL,
            id="T1078",
            name="Valid Accounts",
            confidence="low",
            rationale="Placeholder MITRE mapping — verify technique against alert evidence.",
        ),
        FrameworkMappingItem(
            framework=KILL_CHAIN_FRAMEWORK_LABEL,
            id="KC-4",
            name="Exploitation",
            confidence="low",
            rationale="Placeholder Kill Chain phase — confirm where the attack sits in the chain.",
        ),
    ]


def _infer_kill_chain_phase(normalized: Dict[str, Any]) -> tuple[str, str]:
    """Heuristic default Kill Chain phase from alert shape."""
    text = " ".join(
        str(normalized.get(k) or "")
        for k in ("signature", "search_name", "action", "category", "description")
    ).lower()
    if any(x in text for x in ("exfil", "download", "upload", "dns", "beacon", "c2", "command")):
        return "KC-6", "Command and Control"
    if any(x in text for x in ("install", "service", "registry", "persistence", "scheduled")):
        return "KC-5", "Installation"
    if any(x in text for x in ("login", "auth", "credential", "password", "brute", "mfa")):
        return "KC-4", "Exploitation"
    if any(x in text for x in ("phish", "email", "attachment", "macro")):
        return "KC-3", "Delivery"
    return "KC-4", "Exploitation"


def ensure_mitre_and_kill_chain(
    items: List[FrameworkMappingItem],
    *,
    normalized: Dict[str, Any] | None = None,
) -> List[FrameworkMappingItem]:
    """Ensure at least one MITRE ATT&CK and one Kill Chain entry when list is non-empty."""
    if not items:
        return default_dual_framework_fallback()

    has_mitre = any(is_mitre_framework(x.framework) for x in items)
    has_kill_chain = any(is_kill_chain_framework(x.framework) for x in items)
    out = list(items)

    if not has_mitre:
        out.insert(
            0,
            FrameworkMappingItem(
                framework=MITRE_FRAMEWORK_LABEL,
                id="T1078",
                name="Valid Accounts",
                confidence="low",
                rationale="Inferred MITRE mapping — no ATT&CK technique returned; validate against entities in the alert.",
            ),
        )

    if not has_kill_chain:
        kc_id, kc_name = _infer_kill_chain_phase(normalized or {})
        out.append(
            FrameworkMappingItem(
                framework=KILL_CHAIN_FRAMEWORK_LABEL,
                id=kc_id,
                name=kc_name,
                confidence="low",
                rationale="Inferred Kill Chain phase — no kill-chain mapping returned; adjust based on investigation findings.",
            )
        )

    return out
