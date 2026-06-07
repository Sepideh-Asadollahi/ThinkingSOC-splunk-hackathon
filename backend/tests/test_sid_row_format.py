"""Per-row storage sid helpers."""

from __future__ import annotations

from services.soc_analysis.analysis_audit import (
    build_raw_alert,
    format_row_sid,
    resolve_storage_context,
    splunk_job_sid,
)


def test_format_row_sid_single_row_unchanged() -> None:
    assert format_row_sid("1780870386.6468", 0, 1) == "1780870386.6468"


def test_format_row_sid_multi_row_1_based() -> None:
    assert format_row_sid("1780870386.6468", 0, 2) == "1780870386.6468-1"
    assert format_row_sid("1780870386.6468", 1, 2) == "1780870386.6468-2"


def test_splunk_job_sid_strips_row_suffix() -> None:
    assert splunk_job_sid("1780870386.6468-2") == "1780870386.6468"
    assert splunk_job_sid("1780870386.6468") == "1780870386.6468"


def test_build_raw_alert_preserves_storage_sid() -> None:
    raw = build_raw_alert(
        sid="1780870386.6468-1",
        search_name="New TesT",
        normalized={"host": "we8105desk"},
        splunk_results=[{"host": "we8105desk", "User": "bob"}],
        row_index=0,
    )
    assert raw["sid"] == "1780870386.6468-1"
    assert raw["splunk_job_sid"] == "1780870386.6468"


def test_format_row_sid_three_rows() -> None:
    base = "job.123"
    assert format_row_sid(base, 2, 3) == "job.123-3"


def test_splunk_job_sid_leaves_unsuffixed_sid_unchanged() -> None:
    assert splunk_job_sid("scheduler__admin__search__x_at_1.99") == "scheduler__admin__search__x_at_1.99"


def test_resolve_storage_context_multi_row_slice() -> None:
    sid, idx, job_n = resolve_storage_context(
        sid="job.1-1",
        splunk_results=[{"a": 1}],
        job_row_count=2,
    )
    assert sid == "job.1-1"
    assert idx == 0
    assert job_n == 2
