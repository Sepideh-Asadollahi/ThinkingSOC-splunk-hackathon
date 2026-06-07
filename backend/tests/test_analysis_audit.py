"""Analysis audit: row_index, raw_alert, input/output helpers."""

from __future__ import annotations

from models.analysis import HunterSection, JudgeVerdict, SocAnalysisResult
from models.enrichment import EnrichmentResult
from services.alert.alert_fields import build_alert_fields_for_llm
from services.soc_analysis.analysis_audit import (
    build_analysis_input,
    build_analysis_output,
    build_raw_alert,
    resolve_row_index,
)


def test_resolve_row_index_defaults_to_zero() -> None:
    assert resolve_row_index(None, [{"a": 1}]) == 0
    assert resolve_row_index(2, [{"a": 1}, {"b": 2}]) == 2


def test_build_raw_alert_includes_result_row() -> None:
    rows = [{"host": "h1", "count": 1}, {"host": "h2", "count": 2}]
    raw = build_raw_alert(
        sid="sid-1",
        search_name="alert-name",
        normalized={"severity": "low"},
        splunk_results=rows,
        row_index=1,
    )
    assert raw["sid"] == "sid-1"
    assert raw["search_name"] == "alert-name"
    assert raw["row_index"] == 1
    assert raw["splunk_results_row_count"] == 2
    assert raw["result_row"]["host"] == "h2"


def test_build_alert_fields_uses_row_index() -> None:
    rows = [{"host": "first"}, {"host": "second"}]
    fields = build_alert_fields_for_llm(
        search_name="n",
        normalized={},
        splunk_results_preview=rows,
        row_index=1,
    )
    assert fields["row_index"] == 1
    assert fields["host"] == "second"


def test_build_analysis_output_from_result() -> None:
    result = SocAnalysisResult(
        defender="d",
        hunter=HunterSection(narrative="h"),
        judge=JudgeVerdict(
            verdict="needs_investigation",
            priority="high",
            recommended_next_step="investigate",
            rationale="r",
        ),
        enrichment=EnrichmentResult(
            confidence="low",
            notes="n",
        ),
        risk_context="risk",
    )
    out = build_analysis_output(result)
    assert out["verdict"] == "needs_investigation"
    assert out["priority"] == "high"


def test_build_analysis_input_wraps_alert_fields() -> None:
    inp = build_analysis_input(
        search_name="demo",
        normalized={},
        splunk_results=[{"host": "x"}],
        row_index=0,
    )
    assert inp["row_index"] == 0
    assert inp["alert_fields"]["host"] == "x"
