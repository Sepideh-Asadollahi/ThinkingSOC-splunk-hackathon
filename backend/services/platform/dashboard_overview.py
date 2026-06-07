"""Build dashboard overview from PostgreSQL stats and triage queue."""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from config import Settings
from models.mcp import McpStatusResponse
from services.splunk_integration.splunk_mcp_service import get_mcp_status
from services.platform.system_resources import collect_system_resources
from models.dashboard import (
    ActivityTimelinePoint,
    CountByPriority,
    CountByType,
    CountByVerdict,
    DashboardIntegrations,
    DashboardKpis,
    DashboardOverview,
    TopPriorityItem,
    TrackSplit,
)
from services.splunk_json_store import splunk_store_configured
from services.triage.triage_queue import build_triage_queue_items
from services.splunk_json_store.stats import (
    fetch_activity_by_day,
    fetch_analyses_last_24h,
    fetch_inventory_counts,
    fetch_record_counts_by_type,
    fetch_records_last_24h,
    fetch_total_records,
)
_TOP_PRIORITY_LIMIT = 5
_TRIAGE_SAMPLE_LIMIT = 50
_INTEGRATIONS_CACHE_TTL_SECONDS = 45.0
_MCP_PROBE_TIMEOUT_SECONDS = 8.0
_NEO4J_PROBE_TIMEOUT_SECONDS = 3.0

_integrations_cache: Optional[Tuple[float, DashboardIntegrations]] = None


def _compute_health_score(integrations: DashboardIntegrations) -> int:
    score = 0
    if integrations.postgres:
        score += 25
    if integrations.llm:
        score += 25
    if integrations.mcp:
        score += 25
    if integrations.neo4j:
        score += 25
    return min(100, score)


async def _neo4j_reachable(settings: Settings) -> bool:
    if not settings.tsoc_correlation_enabled or not splunk_store_configured(settings):
        return False
    try:
        from services.correlation_integration import _ensure_correlation_path

        _ensure_correlation_path()
        from graph_core.neo4j_driver import verify_connectivity

        return await verify_connectivity(settings)
    except Exception:
        return False


async def _collect_triage_items(settings: Settings) -> List[Dict[str, Any]]:
    return await build_triage_queue_items(
        settings, track="all", limit=_TRIAGE_SAMPLE_LIMIT
    )


async def _mcp_status_for_dashboard(settings: Settings) -> McpStatusResponse:
    if not settings.tsoc_mcp_enabled:
        return await get_mcp_status(settings)
    try:
        return await asyncio.wait_for(
            get_mcp_status(settings),
            timeout=_MCP_PROBE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return McpStatusResponse(
            configured=True,
            connected=False,
            message="MCP status probe timed out on dashboard load.",
        )


async def _neo4j_reachable_bounded(settings: Settings) -> bool:
    try:
        return await asyncio.wait_for(
            _neo4j_reachable(settings),
            timeout=_NEO4J_PROBE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return False


async def _integrations_status(settings: Settings) -> DashboardIntegrations:
    global _integrations_cache
    now = time.monotonic()
    if _integrations_cache is not None:
        cached_at, cached = _integrations_cache
        if now - cached_at < _INTEGRATIONS_CACHE_TTL_SECONDS:
            return cached

    postgres_ok = splunk_store_configured(settings)
    mcp_status, neo4j_ok = await asyncio.gather(
        _mcp_status_for_dashboard(settings),
        _neo4j_reachable_bounded(settings),
    )
    integrations = DashboardIntegrations(
        postgres=postgres_ok,
        llm=bool(settings.litellm_api_key),
        mcp=bool(mcp_status.connected),
        neo4j=neo4j_ok,
    )
    _integrations_cache = (now, integrations)
    return integrations


async def build_dashboard_overview(settings: Settings) -> DashboardOverview:
    if not splunk_store_configured(settings):
        raise RuntimeError("PostgreSQL store not configured")

    (
        integrations,
        total_records,
        analyses_24h,
        inventory_counts,
        record_type_counts_raw,
        activity_raw,
        triage_items,
    ) = await asyncio.gather(
        _integrations_status(settings),
        fetch_total_records(settings),
        fetch_analyses_last_24h(settings),
        fetch_inventory_counts(settings),
        fetch_record_counts_by_type(settings),
        fetch_activity_by_day(settings, days=30),
        _collect_triage_items(settings),
    )
    users, assets = inventory_counts
    health_score = _compute_health_score(integrations)
    generated_at = datetime.now(timezone.utc).isoformat()

    verdict_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    track_split: Counter[str] = Counter()
    needs_human = 0
    score_sum = 0
    score_n = 0

    for item in triage_items:
        verdict = str(item.get("review_verdict") or "UNKNOWN")
        priority = str(item.get("investigation_priority") or "unknown")
        track = str(item.get("source_track") or "security")
        verdict_counts[verdict] += 1
        priority_counts[priority] += 1
        track_split[track] += 1
        if item.get("needs_human_review"):
            needs_human += 1
        score_sum += int(item.get("triage_score") or 0)
        score_n += 1

    avg_score = round(score_sum / score_n, 1) if score_n else 0.0

    top_priority = [
        TopPriorityItem.model_validate(item)
        for item in triage_items[:_TOP_PRIORITY_LIMIT]
    ]

    return DashboardOverview(
        generated_at=generated_at,
        postgres_configured=True,
        system_resources=collect_system_resources(),
        kpis=DashboardKpis(
            total_records=total_records,
            analyses_24h=analyses_24h,
            needs_human_review=needs_human,
            avg_triage_score=avg_score,
            users=users,
            assets=assets,
        ),
        activity_timeline=[ActivityTimelinePoint.model_validate(p) for p in activity_raw],
        record_type_counts=[CountByType.model_validate(r) for r in record_type_counts_raw],
        triage_by_verdict=[
            CountByVerdict(verdict=k, count=v) for k, v in verdict_counts.most_common()
        ],
        triage_by_priority=[
            CountByPriority(priority=k, count=v) for k, v in priority_counts.most_common()
        ],
        track_split=TrackSplit(
            security=int(track_split.get("security", 0)),
            observability=int(track_split.get("observability", 0)),
        ),
        integrations=integrations,
        health_score=health_score,
        top_priority=top_priority,
    )
