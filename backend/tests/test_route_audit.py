from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.errors import AppError
from app.fetcher import FetchResult
from app.main import create_app
from app.report_builder import AuditReport

app = create_app()
client = TestClient(app, raise_server_exceptions=False)

_MOCK_REPORT: AuditReport = {
    "url": "https://example.com",
    "status": 200,
    "responseTimeMs": 123,
    "title": "Example Domain",
    "metaDescription": "An example page.",
    "h1Count": 1,
    "imagesMissingAlt": 0,
    "totalImages": 1,
    "approxWordCount": 42,
    "fetchedAt": "2026-07-24T10:15:00Z",
}

_AUDIT_URL = "/api/audit"
_VALID_PAYLOAD = {"url": "https://example.com"}


def _mock_run_audit(report: AuditReport = _MOCK_REPORT):
    return patch(
        "app.routes.audit.run_audit",
        new=AsyncMock(return_value=report),
    )


def _mock_run_audit_raising(error: Exception):
    return patch(
        "app.routes.audit.run_audit",
        new=AsyncMock(side_effect=error),
    )


def test_post_audit_returns_200_with_all_report_fields():
    with _mock_run_audit():
        response = client.post(_AUDIT_URL, json=_VALID_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    expected_keys = {
        "url", "status", "responseTimeMs", "title", "metaDescription",
        "h1Count", "imagesMissingAlt", "totalImages", "approxWordCount", "fetchedAt",
    }
    assert set(body.keys()) == expected_keys


def test_post_audit_200_field_values_match_report():
    with _mock_run_audit():
        response = client.post(_AUDIT_URL, json=_VALID_PAYLOAD)

    body = response.json()
    assert body["url"] == "https://example.com"
    assert body["status"] == 200
    assert body["responseTimeMs"] == 123
    assert body["title"] == "Example Domain"
    assert body["h1Count"] == 1
    assert body["fetchedAt"] == "2026-07-24T10:15:00Z"


def test_post_audit_strips_whitespace_from_url_before_calling_pipeline():
    with _mock_run_audit() as mock_audit:
        response = client.post(_AUDIT_URL, json={"url": "  https://example.com  "})

    assert response.status_code == 200
    mock_audit.assert_called_once_with("https://example.com")


def test_post_audit_non_200_target_status_returned_as_finding():
    report_404 = {**_MOCK_REPORT, "status": 404}
    with _mock_run_audit(report_404):
        response = client.post(_AUDIT_URL, json=_VALID_PAYLOAD)

    assert response.status_code == 200
    assert response.json()["status"] == 404


def test_blank_url_returns_422():
    response = client.post(_AUDIT_URL, json={"url": ""})
    assert response.status_code == 422


def test_whitespace_only_url_returns_422():
    response = client.post(_AUDIT_URL, json={"url": "    "})
    assert response.status_code == 422


def test_missing_url_field_returns_422():
    response = client.post(_AUDIT_URL, json={})
    assert response.status_code == 422


def test_integer_url_value_returns_422():
    response = client.post(_AUDIT_URL, json={"url": 12345})
    assert response.status_code == 422


def test_null_url_value_returns_422():
    response = client.post(_AUDIT_URL, json={"url": None})
    assert response.status_code == 422


def test_non_json_body_returns_422():
    response = client.post(
        _AUDIT_URL,
        content=b"not json at all",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_invalid_url_returns_400_with_error_envelope():
    invalid_url_err = AppError("INVALID_URL", "not a valid URL")
    with _mock_run_audit_raising(invalid_url_err):
        response = client.post(_AUDIT_URL, json={"url": "ftp://example.com"})

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_URL"
    assert "message" in body["error"]


@pytest.mark.parametrize(
    "code, expected_status",
    [
        ("TIMEOUT", 504),
        ("UNREACHABLE", 502),
        ("UNSUPPORTED_CONTENT_TYPE", 415),
        ("RESPONSE_TOO_LARGE", 413),
        ("INTERNAL_ERROR", 500),
    ],
)
def test_pipeline_app_error_returns_correct_status_and_envelope(code, expected_status):
    err = AppError(code, f"test: {code}")
    with _mock_run_audit_raising(err):
        response = client.post(_AUDIT_URL, json=_VALID_PAYLOAD)

    assert response.status_code == expected_status
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == code
    assert "message" in body["error"]


def test_error_envelope_has_only_error_key_on_failure():
    err = AppError("TIMEOUT", "timed out")
    with _mock_run_audit_raising(err):
        response = client.post(_AUDIT_URL, json=_VALID_PAYLOAD)

    assert list(response.json().keys()) == ["error"]


def test_error_envelope_has_code_and_message_keys():
    err = AppError("UNREACHABLE", "host unreachable")
    with _mock_run_audit_raising(err):
        response = client.post(_AUDIT_URL, json=_VALID_PAYLOAD)

    error_detail = response.json()["error"]
    assert set(error_detail.keys()) == {"code", "message"}


def test_unhandled_exception_returns_500_internal_error():
    with _mock_run_audit_raising(RuntimeError("something went very wrong")):
        response = client.post(_AUDIT_URL, json=_VALID_PAYLOAD)

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"


def test_unhandled_exception_response_never_leaks_traceback():
    with _mock_run_audit_raising(RuntimeError("internal details here")):
        response = client.post(_AUDIT_URL, json=_VALID_PAYLOAD)

    body = response.json()
    assert "internal details here" not in str(body)
    assert "Traceback" not in str(body)


def test_get_health_returns_200_ok_true():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_unknown_route_returns_404():
    response = client.get("/api/nonexistent")
    assert response.status_code == 404


def test_get_method_on_audit_endpoint_returns_405():
    response = client.get(_AUDIT_URL)
    assert response.status_code == 405


def test_content_type_header_is_application_json_on_success():
    with _mock_run_audit():
        response = client.post(_AUDIT_URL, json=_VALID_PAYLOAD)

    assert "application/json" in response.headers.get("content-type", "")


def test_content_type_header_is_application_json_on_error():
    err = AppError("TIMEOUT", "timed out")
    with _mock_run_audit_raising(err):
        response = client.post(_AUDIT_URL, json=_VALID_PAYLOAD)

    assert "application/json" in response.headers.get("content-type", "")
