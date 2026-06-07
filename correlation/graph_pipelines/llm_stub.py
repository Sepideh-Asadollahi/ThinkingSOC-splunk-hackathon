from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from correlation_config import get_settings
from graph_pipelines.attack_alert_filter import derive_title_fallback
from graph_pipelines.correlation_logging import log_step
from services.llm.litellm_service import LiteLLMNotConfiguredError, litellm_chat_completion
from services.soc_analysis.soc_analysis_json import parse_llm_json_response

logger = logging.getLogger(__name__)

_FIXTURES = Path(__file__).resolve().parent.parent / "seed" / "fixtures"
_PROMPT_PATH = Path(__file__).resolve().parent / "prompt_attack_discovery_system.md"
_MERGE_PROMPT_PATH = Path(__file__).resolve().parent / "prompt_cluster_merge_system.md"


def _load_fixture(name: str) -> dict[str, Any]:
    path = _FIXTURES / name
    return json.loads(path.read_text(encoding="utf-8"))


def _llm_available() -> bool:
    settings = get_settings()
    if not (settings.litellm_model or "").strip():
        return False
    if not settings.litellm_api_key and not settings.litellm_api_base:
        return False
    return True


_PHASE_FROM_ALERT = (
    ("phish", "Initial Access"),
    ("malicious url", "Initial Access"),
    ("powershell", "Execution"),
    ("psexec", "Lateral Movement"),
    ("rdp", "Lateral Movement"),
    ("lateral", "Lateral Movement"),
    ("scheduled task", "Persistence"),
    ("persistence", "Persistence"),
    ("c2", "Command and Control"),
    ("beacon", "Command and Control"),
    ("outbound", "Command and Control"),
    ("exfil", "Exfiltration"),
    ("credential", "Credential Access"),
    ("login", "Initial Access"),
)


def _phase_label_for_alert(name: str) -> str:
    lower = name.lower()
    for needle, phase in _PHASE_FROM_ALERT:
        if needle in lower:
            return phase
    return "Detection"


def _steps_from_cluster_alerts(cluster: dict[str, Any]) -> list[dict[str, Any]]:
    """Chronological narrative steps per alert when LLM/fixture steps are thin."""
    alerts = sorted(
        list(cluster.get("alerts") or []),
        key=lambda a: str(a.get("timestamp") or ""),
    )
    steps: list[dict[str, Any]] = []
    for index, alert in enumerate(alerts, start=1):
        name = str(alert.get("search_name") or alert.get("name") or "Correlated alert").strip()
        risk = int(alert.get("risk_score") or 0)
        ts = str(alert.get("timestamp") or "").strip()
        phase = _phase_label_for_alert(name)
        when = f" at {ts}" if ts else ""
        steps.append(
            {
                "phase_label": phase,
                "description": (
                    f"Step {index}: {name} was detected{when} "
                    f"(risk score {risk}), advancing the attack sequence."
                ),
            }
        )
    return steps


def _cluster_payload(cluster: dict[str, Any]) -> dict[str, Any]:
    alerts = sorted(
        list(cluster.get("alerts") or []),
        key=lambda a: str(a.get("timestamp") or ""),
    )
    items = []
    shared_entities: set[str] = set()
    for step_index, alert in enumerate(alerts, start=1):
        entities = [str(e) for e in (alert.get("entity_identifiers") or []) if e]
        shared_entities.update(entities)
        items.append(
            {
                "step_hint": step_index,
                "alert_row_id": alert.get("alert_row_id"),
                "name": alert.get("name") or alert.get("search_name"),
                "search_name": alert.get("search_name") or alert.get("name"),
                "risk_score": int(alert.get("risk_score") or 0),
                "status": alert.get("status"),
                "timestamp": str(alert.get("timestamp") or ""),
                "entities": entities,
            }
        )
    return {
        "alerts_chronological": items,
        "shared_entities": sorted(shared_entities),
        "alert_count": len(items),
        "narrative_instruction": (
            "Write attack_analysis_steps as a numbered chronological attack story "
            "(earliest alert first). Prefer one step per alert when alerts form a kill chain."
        ),
    }


def _cluster_entities(cluster: dict[str, Any]) -> set[str]:
    entities: set[str] = set()
    for alert in cluster.get("alerts") or []:
        entities.update(str(e) for e in (alert.get("entity_identifiers") or []) if e)
    return entities


def _merge_report(cluster: dict[str, Any], llm_data: dict[str, Any]) -> dict[str, Any]:
    fixture = _load_fixture("smart_report.json")
    title = str(llm_data.get("title") or "").strip()
    if not title or title.lower().startswith("operation shadow"):
        title = derive_title_fallback(cluster)

    summary = str(llm_data.get("summary") or llm_data.get("executive_summary") or "").strip()
    executive = str(llm_data.get("executive_summary") or summary or fixture.get("executive_summary", "")).strip()
    steps = llm_data.get("attack_analysis_steps")
    if not isinstance(steps, list) or not steps:
        steps = fixture.get("attack_analysis_steps", [])

    return {
        "title": title,
        "summary": summary or fixture.get("summary", ""),
        "executive_summary": executive,
        "attack_analysis_steps": steps,
        "attack_timeline_trees": fixture.get("attack_timeline_trees", []),
    }


def _normalize_merge_result(raw: dict[str, Any], cluster_count: int) -> dict[str, Any]:
    fixture = _load_fixture("cluster_merge.json")
    merge_groups: list[list[int]] = []
    seen: set[int] = set()

    for group in raw.get("merge_groups") or []:
        if not isinstance(group, list):
            continue
        indices: list[int] = []
        for item in group:
            if isinstance(item, bool):
                continue
            try:
                idx = int(item)
            except (TypeError, ValueError):
                continue
            if 0 <= idx < cluster_count and idx not in seen:
                indices.append(idx)
                seen.add(idx)
        if len(indices) >= 2:
            merge_groups.append(sorted(indices))

    potential_links = raw.get("potential_links")
    if not isinstance(potential_links, list):
        potential_links = fixture.get("potential_links", [])

    reasoning = str(raw.get("reasoning") or "").strip()
    if not reasoning:
        reasoning = str(fixture.get("reasoning") or "Cluster merge decision")

    return {
        "merge_groups": merge_groups,
        "potential_links": potential_links,
        "reasoning": reasoning,
        "source": raw.get("source", "llm"),
    }


def partition_clusters_by_merge(cluster_count: int, merge_result: dict[str, Any]) -> list[list[int]]:
    """Return disjoint groups of cluster indices (merged groups or singletons)."""
    if cluster_count <= 0:
        return []

    log_step("partition_merge_start", cluster_count=cluster_count, merge_groups=merge_result.get("merge_groups"))

    parent = list(range(cluster_count))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for group in merge_result.get("merge_groups") or []:
        if not isinstance(group, list) or len(group) < 2:
            continue
        anchor: int | None = None
        for item in group:
            try:
                idx = int(item)
            except (TypeError, ValueError):
                continue
            if not (0 <= idx < cluster_count):
                continue
            if anchor is None:
                anchor = idx
            else:
                union(anchor, idx)

    buckets: dict[int, list[int]] = defaultdict(list)
    for i in range(cluster_count):
        buckets[find(i)].append(i)

    groups = [sorted(indices) for indices in buckets.values()]
    log_step("partition_merge_done", incident_groups=groups)
    return groups


def merge_cluster_alerts(clusters: list[dict[str, Any]], indices: list[int]) -> dict[str, Any]:
    """Combine alerts from multiple clusters into one chronologically sorted cluster dict."""
    from graph_pipelines.attack_alert_filter import sort_alerts_by_time

    alerts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for idx in indices:
        if idx < 0 or idx >= len(clusters):
            continue
        for alert in clusters[idx].get("alerts") or []:
            aid = str(alert.get("alert_row_id") or "")
            if aid and aid in seen_ids:
                continue
            if aid:
                seen_ids.add(aid)
            alerts.append(alert)
    return {"alerts": sort_alerts_by_time(alerts)}


def _merge_correlation_payload(
    clusters: list[dict[str, Any]],
    reports: list[dict[str, Any]],
) -> dict[str, Any]:
    items = []
    for idx, cluster in enumerate(clusters):
        report = reports[idx] if idx < len(reports) else {}
        items.append(
            {
                "cluster_index": idx,
                "cluster": _cluster_payload(cluster),
                "report": {
                    "title": report.get("title"),
                    "summary": report.get("summary"),
                    "executive_summary": report.get("executive_summary"),
                },
            }
        )
    return {"clusters": items, "cluster_count": len(clusters)}


def _heuristic_cluster_merge(clusters: list[dict[str, Any]]) -> dict[str, Any]:
    """Fallback when LLM unavailable: merge only if clusters share entities."""
    n = len(clusters)
    if n <= 1:
        return _normalize_merge_result(_load_fixture("cluster_merge.json"), n)

    entity_sets = [_cluster_entities(c) for c in clusters]
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    potential_links: list[dict[str, Any]] = []
    from graph_pipelines.attack_alert_filter import merge_blocked_by_indicator_split

    for i in range(n):
        for j in range(i + 1, n):
            overlap = entity_sets[i] & entity_sets[j]
            if not overlap:
                continue
            if merge_blocked_by_indicator_split(clusters[i], clusters[j]):
                potential_links.append(
                    {
                        "cluster_indices": [i, j],
                        "link_type": "other",
                        "detail": "Shared IOC only — kept separate from host/user campaign.",
                        "shared_entities": sorted(overlap),
                    }
                )
                continue
            union(i, j)
            potential_links.append(
                {
                    "cluster_indices": [i, j],
                    "link_type": "shared_entity",
                    "detail": f"Shared: {', '.join(sorted(overlap)[:5])}",
                    "shared_entities": sorted(overlap),
                }
            )

    buckets: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        buckets[find(i)].append(i)

    merge_groups = [sorted(g) for g in buckets.values() if len(g) >= 2]
    reasoning = (
        "Heuristic: merged clusters with overlapping entities."
        if merge_groups
        else "Heuristic: no shared entities — treating as separate attacks."
    )
    return _normalize_merge_result(
        {
            "merge_groups": merge_groups,
            "potential_links": potential_links,
            "reasoning": reasoning,
            "source": "heuristic",
        },
        n,
    )


async def _correlate_clusters_with_llm(
    clusters: list[dict[str, Any]],
    reports: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not _llm_available():
        log_step("llm_merge_skip", reason="llm_not_configured")
        return None

    settings = get_settings()
    system = _MERGE_PROMPT_PATH.read_text(encoding="utf-8")
    payload = _merge_correlation_payload(clusters, reports)
    user_msg = json.dumps(payload, ensure_ascii=False, default=str)
    log_step("llm_merge_request", cluster_count=len(clusters), payload=payload)

    try:
        out = await litellm_chat_completion(
            settings,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=min(settings.litellm_analysis_max_tokens, 1024),
        )
        llm_data = parse_llm_json_response(str(out.get("content") or ""))
        llm_data["source"] = "llm"
        result = _normalize_merge_result(llm_data, len(clusters))
        log_step("llm_merge_response", raw=llm_data, normalized=result)
        return result
    except (LiteLLMNotConfiguredError, json.JSONDecodeError, ValueError) as exc:
        logger.warning("cluster_merge LLM fallback: %s", exc)
        log_step("llm_merge_fallback", error=str(exc))
        return None
    except Exception as exc:
        logger.warning("cluster_merge LLM error: %s", exc, exc_info=True)
        return None


async def _generate_report_with_llm(cluster: dict[str, Any]) -> dict[str, Any] | None:
    if not _llm_available():
        return None

    settings = get_settings()
    system = _PROMPT_PATH.read_text(encoding="utf-8")
    payload = _cluster_payload(cluster)
    user_msg = (
        "Produce the Attack Discovery JSON for this correlated alert cluster. "
        "attack_analysis_steps must be the numbered attack narrative (chronological).\n\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )

    try:
        out = await litellm_chat_completion(
            settings,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=min(settings.litellm_analysis_max_tokens, 2048),
        )
        llm_data = parse_llm_json_response(str(out.get("content") or ""))
        return _merge_report(cluster, llm_data)
    except (LiteLLMNotConfiguredError, json.JSONDecodeError, ValueError) as exc:
        logger.warning("attack_discovery LLM fallback: %s", exc)
        return None
    except Exception as exc:
        logger.warning("attack_discovery LLM error: %s", exc, exc_info=True)
        return None


async def generate_smart_finding_report(cluster: dict[str, Any]) -> dict[str, Any]:
    alert_ids = [a.get("alert_row_id") for a in cluster.get("alerts") or []]
    llm_report = await _generate_report_with_llm(cluster)
    if llm_report is not None:
        log_step("llm_report_source", source="llm", alert_ids=alert_ids, title=llm_report.get("title"))
        return llm_report

    report = dict(_load_fixture("smart_report.json"))
    alerts = cluster.get("alerts") or []
    report["title"] = derive_title_fallback(cluster)
    cluster_steps = _steps_from_cluster_alerts(cluster)
    if cluster_steps:
        report["attack_analysis_steps"] = cluster_steps
    if alerts:
        names = ", ".join(str(a.get("name") or "") for a in alerts[:3] if a.get("name"))
        report["summary"] = f"Correlated attack alerts: {names}.".strip()
        report["executive_summary"] = report["summary"]
    log_step("llm_report_source", source="fixture", alert_ids=alert_ids, title=report.get("title"))
    return report


async def correlate_clusters(
    clusters: list[dict[str, Any]],
    reports: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Decide whether multiple attack clusters should merge into one incident."""
    from graph_pipelines.attack_alert_filter import apply_indicator_split_merge_guard

    n = len(clusters)
    if n <= 1:
        result = _normalize_merge_result(_load_fixture("cluster_merge.json"), n)
        if n == 1:
            result["reasoning"] = "Single cluster — no merge decision needed."
        log_step("correlate_clusters", mode="single", result=result)
        return result

    report_list = reports if reports is not None else [{} for _ in clusters]
    llm_result = await _correlate_clusters_with_llm(clusters, report_list)
    if llm_result is not None:
        guarded = apply_indicator_split_merge_guard(clusters, llm_result)
        log_step("correlate_clusters", mode="llm", result=guarded)
        return guarded

    heuristic = apply_indicator_split_merge_guard(clusters, _heuristic_cluster_merge(clusters))
    log_step("correlate_clusters", mode="heuristic", result=heuristic)
    return heuristic
