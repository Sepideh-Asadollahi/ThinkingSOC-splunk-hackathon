"""Graph wiring constants (node order matches edges in ``graph.py``)."""

from __future__ import annotations

GRAPH_NODE_ORDER: str = ",".join(
    (
        "prepare",
        "risk_engine",
        "virustotal",
        "defender",
        "hunter",
        "judge",
        "framework_mapping",
        "investigation_questions",
        "root_cause_spl",
    )
)
