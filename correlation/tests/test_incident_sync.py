from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from graph_crud.incident_sync import sync_finding_incident_to_neo4j


@pytest.mark.asyncio
async def test_sync_skips_empty_ids():
    assert await sync_finding_incident_to_neo4j(
        incident_id="demo-incident-x",
        title="Test",
        alert_row_ids=[],
    ) == 0


@pytest.mark.asyncio
async def test_sync_returns_linked_count():
    with patch(
        "graph_crud.incident_sync.run_write_query",
        new_callable=AsyncMock,
        side_effect=[[{"linked": 3}], [{"edges": 2}]],
    ):
        linked = await sync_finding_incident_to_neo4j(
            incident_id="demo-incident-abc",
            title="RDP and PsExec",
            alert_row_ids=["ALERT-099", "ALERT-101", "ALERT-102"],
        )
    assert linked == 3
