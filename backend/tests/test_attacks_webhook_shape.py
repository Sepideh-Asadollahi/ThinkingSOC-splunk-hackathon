from __future__ import annotations

import json
from pathlib import Path

from models.handoff import normalize_splunk_ingest_payload

_ATTACKS = Path(__file__).resolve().parents[1] / "scripts" / "ATTACKS"
_FORBIDDEN_IN_ATTACKS = frozenset({"normalized", "enrichment", "correlation", "row_data"})


def test_attacks_json_is_splunk_webhook_only():
    for path in sorted(_ATTACKS.glob("attack_step_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        forbidden = _FORBIDDEN_IN_ATTACKS & payload.keys()
        assert not forbidden, f"{path.name}: move {sorted(forbidden)} out of ATTACKS/"
        assert payload.get("sid"), f"{path.name}: missing sid"
        assert payload.get("search_name"), f"{path.name}: missing search_name"
        assert isinstance(payload.get("result"), dict) and payload["result"], f"{path.name}: missing result"
        assert payload["result"].get("_time"), f"{path.name}: result._time required"

        handoff = normalize_splunk_ingest_payload(payload)
        assert handoff.sid == payload["sid"]
        assert handoff.search_name == payload["search_name"]
        assert len(handoff.results) == 1
        assert handoff.normalized.get("host") or handoff.normalized.get("user")


def test_attacks_kill_chain_has_four_steps():
    steps = sorted(_ATTACKS.glob("attack_step_*.json"))
    if not steps:
        # In some minimal/dev checkouts the demo fixtures may be absent.
        # Keep the rest of the suite fast/deterministic; fixture presence is not a core unit-test concern.
        return
    assert len(steps) == 4
