"""Root-cause hypothesis generator for observability pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.observability import DiagnoserSection, RootCauseHypothesis


def _to_float(v: Any) -> Optional[float]:
    try:
        if v is None or str(v).strip() == "":
            return None
        return float(v)
    except Exception:
        return None


def _build_searches(host: str | None, service: str | None) -> List[str]:
    host_clause = ' host="{0}"'.format(host) if host else ""
    service_clause = ' service="{0}"'.format(service) if service else ""
    return [
        "index=* earliest=-30m{0}{1} (cpu OR memory OR disk OR latency_ms OR error_rate)".format(
            host_clause, service_clause
        ),
        "index=* earliest=-30m{0}{1} (status>=500 OR timeout OR unavailable)".format(host_clause, service_clause),
    ]


def build_diagnoser(normalized: Dict[str, Any]) -> DiagnoserSection:
    host = str(normalized.get("host") or "").strip() or None
    service = str(normalized.get("service") or "").strip() or None

    cpu = _to_float(normalized.get("cpu"))
    mem = _to_float(normalized.get("memory"))
    disk = _to_float(normalized.get("disk"))
    latency = _to_float(normalized.get("latency_ms"))
    err = _to_float(normalized.get("error_rate"))
    status_code = str(normalized.get("status_code") or "").strip()

    hypotheses: List[RootCauseHypothesis] = []
    if cpu is not None and cpu >= 90:
        hypotheses.append(
            RootCauseHypothesis(
                hypothesis="CPU saturation on the affected host is likely causing service degradation.",
                confidence="medium",
                evidence_refs=["normalized.cpu={0}".format(cpu)],
                what_would_confirm="Process-level CPU trend and matching latency/error increase in same window.",
            )
        )
    if mem is not None and mem >= 90:
        hypotheses.append(
            RootCauseHypothesis(
                hypothesis="Memory pressure may be impacting process stability and response time.",
                confidence="medium",
                evidence_refs=["normalized.memory={0}".format(mem)],
                what_would_confirm="OOM/restart logs and memory growth trend for the service.",
            )
        )
    if disk is not None and disk >= 90:
        hypotheses.append(
            RootCauseHypothesis(
                hypothesis="Disk capacity pressure may be causing write failures or latency.",
                confidence="medium",
                evidence_refs=["normalized.disk={0}".format(disk)],
                what_would_confirm="I/O wait increase and disk usage trend around alert time.",
            )
        )
    if latency is not None and latency >= 1000:
        hypotheses.append(
            RootCauseHypothesis(
                hypothesis="Application/service latency is elevated beyond normal threshold.",
                confidence="high" if err and err >= 2 else "medium",
                evidence_refs=["normalized.latency_ms={0}".format(latency)],
                what_would_confirm="Correlated latency and error rate rise for same host/service.",
            )
        )
    if status_code and status_code.isdigit() and int(status_code) >= 500:
        hypotheses.append(
            RootCauseHypothesis(
                hypothesis="Server-side error responses indicate service degradation or dependency failure.",
                confidence="medium",
                evidence_refs=["normalized.status_code={0}".format(status_code)],
                what_would_confirm="Error log correlation and downstream dependency health checks.",
            )
        )

    if not hypotheses:
        hypotheses.append(
            RootCauseHypothesis(
                hypothesis="Insufficient operational evidence for a single root-cause hypothesis.",
                confidence="low",
                evidence_refs=[],
                what_would_confirm="Additional metrics and logs for host/service in the alert window.",
            )
        )

    return DiagnoserSection(
        root_cause_hypotheses=hypotheses,
        followup_searches=_build_searches(host, service),
    )
