from __future__ import annotations

import httpx

from api.app_errors import AppError, map_exception, splunk_rest_error


def test_map_splunk_404_to_job_not_found():
    req = httpx.Request("GET", "https://127.0.0.1:8089/services/search/jobs/demo")
    res = httpx.Response(404, request=req)
    err = httpx.HTTPStatusError("404", request=req, response=res)
    mapped = splunk_rest_error(err, sid="demo")
    assert mapped.code == "splunk_job_not_found"
    assert "demo" in (mapped.reason or "")


def test_map_value_error_to_bad_request():
    mapped = map_exception(ValueError("sid missing"))
    assert mapped.status_code == 400
    assert mapped.code == "invalid_request"


def test_build_error_body_shape():
    from api.exception_handlers import build_error_body

    body = build_error_body(
        code="validation_error",
        message="Invalid field 'sid'",
        reason="Fix the request body.",
        request_id="rid-1",
        details={"fields": [{"field": "sid", "message": "required"}]},
    )
    assert body["detail"] == "Invalid field 'sid'"
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["reason"] == "Fix the request body."
    assert body["request_id"] == "rid-1"
