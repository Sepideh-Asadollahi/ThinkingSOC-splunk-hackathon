from services.soc_analysis.soc_analysis_root_cause_spl import sanitize_root_cause_spl_output


def test_sanitize_enforces_non_raw_output_with_table() -> None:
    rc = sanitize_root_cause_spl_output(
        {
            "spl": 'search index=botsv1 host=we8105desk Image="*osk.exe*"',
            "time_window": "earliest=1 latest=now",
        }
    )
    assert rc is not None
    assert "| table " in (rc.spl or "")
    assert "auto_table_projection_for_non_raw_output" in (rc.notes or [])


def test_sanitize_keeps_stats_pipeline_without_projection() -> None:
    spl = 'search index=botsv1 host=we8105desk Image="*osk.exe*" | stats count by User'
    rc = sanitize_root_cause_spl_output(
        {
            "spl": spl,
            "time_window": "earliest=1 latest=now",
        }
    )
    assert rc is not None
    assert 'source="WinEventLog:Microsoft-Windows-Sysmon/Operational"' in (rc.spl or "")
    assert "| stats count by User" in (rc.spl or "")
    assert "auto_table_projection_for_non_raw_output" not in (rc.notes or [])
