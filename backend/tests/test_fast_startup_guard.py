from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app


def test_testclient_startup_does_not_touch_splunk_or_embeddings_in_fast_mode() -> None:
    """
    Guardrail: if FastAPI lifespan accidentally runs in unit tests,
    it may log in to Splunk and/or load embedding models (slow/flaky).
    """

    async def _boom(*_a, **_k):
        raise AssertionError("unexpected integration startup during unit tests")

    with (
        patch("splunk.client.rest_client.SplunkRestClient.login", new_callable=AsyncMock, side_effect=_boom),
        patch("services.soc_rag.embeddings.ensure_embedding_model", new_callable=AsyncMock, side_effect=_boom),
    ):
        with TestClient(app) as c:
            r = c.get("/api/v1/health")
    assert r.status_code == 200


@pytest.mark.real_startup
def test_real_startup_marker_disables_autouse_lifespan_patches() -> None:
    """
    When explicitly opted-in, conftest should not auto-mock lifespan steps.
    The test can still patch them explicitly to keep this test fast.
    """
    with (
        patch("main.init_store", new_callable=AsyncMock) as init_store,
        patch("main._saia_startup", new_callable=AsyncMock) as saia_startup,
        patch("main._rag_startup", new_callable=AsyncMock) as rag_startup,
        patch("main.correlation_startup", new_callable=AsyncMock) as corr_startup,
        patch("main.correlation_shutdown", new_callable=AsyncMock) as corr_shutdown,
        patch("main.close_store", new_callable=AsyncMock) as close_store,
    ):
        with TestClient(app) as c:
            r = c.get("/api/v1/health")

    assert r.status_code == 200
    assert init_store.await_count == 1
    assert saia_startup.await_count == 1
    assert rag_startup.await_count == 1
    assert corr_startup.await_count == 1
    assert corr_shutdown.await_count == 1
    assert close_store.await_count == 1

