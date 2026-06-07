from services.investigation.investigation_spl_execute import _readable_rows


def test_readable_rows_truncates_long_lists() -> None:
    rows = [
        {
            "dest_ips": [str(i) for i in range(40)],
            "count": "40",
        }
    ]
    out = _readable_rows(rows)
    vals = out[0]["dest_ips"]
    assert isinstance(vals, list)
    assert len(vals) == 26
    assert vals[-1] == "... (+15 more)"


def test_readable_rows_truncates_long_strings() -> None:
    rows = [{"blob": "x" * 500}]
    out = _readable_rows(rows)
    blob = out[0]["blob"]
    assert isinstance(blob, str)
    assert blob.endswith("... (+180 chars)")
