from models.handoff import SplunkAlertIngest


def test_splunk_alert_ingest_defaults() -> None:
    m = SplunkAlertIngest()
    assert m.sid is None
    assert m.results == []
    assert m.normalized == {}
    assert m.include_raw is False
    assert m.severity_override is None


def test_splunk_alert_ingest_roundtrip() -> None:
    m = SplunkAlertIngest(
        sid="abc",
        search_name="saved",
        results=[{"_raw": "x"}],
        normalized={"host": "h1"},
    )
    d = m.model_dump()
    assert d["sid"] == "abc"
    assert d["results"][0]["_raw"] == "x"
