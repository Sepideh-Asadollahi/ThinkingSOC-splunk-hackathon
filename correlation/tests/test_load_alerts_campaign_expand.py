from __future__ import annotations

import pytest

from graph_pipelines.attack_alert_filter import prepare_attack_clusters


@pytest.mark.asyncio
async def test_load_alerts_expands_shared_user_host_within_lookback():
    from graph_crud.correlation import load_alerts_from_neo4j
    from seed.seed import seed_neo4j

    await seed_neo4j()

    alerts = await load_alerts_from_neo4j(limit=4, lookback_days=7)
    ids = {a["alert_row_id"] for a in alerts}

    assert len(alerts) == 4
    assert "ALERT-102" in ids
    assert "ALERT-090" in ids, "precursor must expand via username:jdoe@corp.local"
    assert "ALERT-091" not in ids, "IOC-only row dropped when cap applies"

    selected = prepare_attack_clusters(alerts, window_hours=168, log_decisions=False)
    main = max(selected, key=lambda c: len(c.get("alerts") or []))
    main_ids = {a["alert_row_id"] for a in main["alerts"]}

    assert "ALERT-090" in main_ids
    assert "ALERT-099" in main_ids
    assert "ALERT-101" in main_ids
    assert "ALERT-102" in main_ids
    assert "ALERT-091" not in main_ids
