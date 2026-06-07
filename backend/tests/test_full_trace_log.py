"""Full trace log serialization (no truncation)."""

from __future__ import annotations

from services.llm.full_trace_log import serialize_full


def test_serialize_full_no_truncation() -> None:
    big = "x" * 50_000
    out = serialize_full({"payload": big, "nested": [big]})
    assert len(out) > 100_000
    assert big in out
