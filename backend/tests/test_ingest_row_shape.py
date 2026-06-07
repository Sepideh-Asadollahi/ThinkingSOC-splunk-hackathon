"""Multi-row detection and console logging shape."""

from __future__ import annotations

import logging

from services.alert.ingest_row_shape import (
    detect_splunk_result_row_shape,
    log_splunk_result_row_shape,
)


def test_detect_single_row() -> None:
    shape = detect_splunk_result_row_shape(sid="1780870386.6468", total_rows=1)
    assert shape["multi_row"] is False
    assert shape["total_rows"] == 1
    assert shape["rows_to_analyze"] == 1
    assert shape["analysis_mode"] == "single_row"
    assert shape["planned_storage_sids"] == ["1780870386.6468"]


def test_detect_multi_row_two_rows() -> None:
    shape = detect_splunk_result_row_shape(sid="1780870386.6468", total_rows=2)
    assert shape["multi_row"] is True
    assert shape["total_rows"] == 2
    assert shape["rows_to_analyze"] == 2
    assert shape["analysis_mode"] == "per_row_sequential"
    assert shape["planned_storage_sids"] == [
        "1780870386.6468-1",
        "1780870386.6468-2",
    ]


def test_detect_multi_row_respects_max_rows_cap() -> None:
    shape = detect_splunk_result_row_shape(sid="job.1", total_rows=5, max_rows=2)
    assert shape["multi_row"] is True
    assert shape["rows_to_analyze"] == 2
    assert shape["planned_storage_sids"] == ["job.1-1", "job.1-2"]


def test_detect_no_rows() -> None:
    shape = detect_splunk_result_row_shape(sid="job.1", total_rows=0)
    assert shape["multi_row"] is False
    assert shape["analysis_mode"] == "no_rows"
    assert shape["planned_storage_sids"] == []


def test_log_multi_row_emits_info(caplog) -> None:
    caplog.set_level(logging.INFO)
    shape = detect_splunk_result_row_shape(sid="1780870386.6468", total_rows=2)
    log_splunk_result_row_shape(stage="after_enrich", search_name="New TesT", shape=shape)
    assert len(caplog.records) == 1
    msg = caplog.records[0].getMessage()
    assert "ingest_row_shape" in msg
    assert "multi_row=true" in msg
    assert "total_rows=2" in msg
    assert "1780870386.6468-1" in msg


def test_log_single_row_emits_info(caplog) -> None:
    caplog.set_level(logging.INFO)
    shape = detect_splunk_result_row_shape(sid="1780870386.6468", total_rows=1)
    log_splunk_result_row_shape(stage="after_enrich", search_name="solo", shape=shape)
    msg = caplog.records[0].getMessage()
    assert "multi_row=false" in msg
    assert "analysis_mode=single_row" in msg
