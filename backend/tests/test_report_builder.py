import re
from unittest.mock import AsyncMock, patch

import pytest

from app.errors import AppError
from app.fetcher import FetchResult
from app.parser.parse import ParseResult
from app.report_builder import AuditReport, run_audit

_VALID_URL = "https://example.com"

_FETCH_RESULT = FetchResult(
    status=200,
    content_type="text/html; charset=utf-8",
    body="<html><head><title>Test</title></head><body><h1>Hi</h1></body></html>",
    response_time_ms=123,
)

_PARSE_RESULT = ParseResult(
    title="Test",
    meta_description=None,
    h1_count=1,
    total_images=0,
    images_missing_alt=0,
    approx_word_count=5,
)


def _mock_fetch(result: FetchResult = _FETCH_RESULT):
    return patch(
        "app.report_builder.fetch_page",
        new=AsyncMock(return_value=result),
    )


def _mock_parse(result: ParseResult = _PARSE_RESULT):
    return patch(
        "app.report_builder.parse_html",
        return_value=result,
    )


def test_audit_report_typeddict_has_all_required_keys():
    required = {
        "url",
        "status",
        "responseTimeMs",
        "title",
        "metaDescription",
        "h1Count",
        "imagesMissingAlt",
        "totalImages",
        "approxWordCount",
        "fetchedAt",
    }
    assert set(AuditReport.__annotations__.keys()) == required


@pytest.mark.anyio
async def test_run_audit_returns_audit_report_on_success():
    with _mock_fetch(), _mock_parse():
        report = await run_audit(_VALID_URL)

    assert isinstance(report, dict)
    assert report["url"] == _VALID_URL
    assert report["status"] == 200
    assert report["responseTimeMs"] == 123
    assert report["title"] == "Test"
    assert report["metaDescription"] is None
    assert report["h1Count"] == 1
    assert report["totalImages"] == 0
    assert report["imagesMissingAlt"] == 0
    assert report["approxWordCount"] == 5


@pytest.mark.anyio
async def test_run_audit_result_has_all_ten_keys():
    with _mock_fetch(), _mock_parse():
        report = await run_audit(_VALID_URL)

    expected_keys = {
        "url", "status", "responseTimeMs", "title", "metaDescription",
        "h1Count", "imagesMissingAlt", "totalImages", "approxWordCount", "fetchedAt",
    }
    assert set(report.keys()) == expected_keys


@pytest.mark.anyio
async def test_fetched_at_is_iso_8601_utc_with_z_suffix():
    with _mock_fetch(), _mock_parse():
        report = await run_audit(_VALID_URL)

    fetched_at = report["fetchedAt"]
    assert fetched_at.endswith("Z"), f"fetchedAt must end with Z, got: {fetched_at}"
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", fetched_at), (
        f"fetchedAt does not match expected ISO 8601 format: {fetched_at}"
    )


@pytest.mark.anyio
async def test_run_audit_passes_stripped_url_to_fetcher():
    with _mock_fetch() as mock_fetch, _mock_parse():
        report = await run_audit("  https://example.com  ")

    mock_fetch.assert_called_once_with("https://example.com")
    assert report["url"] == "https://example.com"


@pytest.mark.anyio
async def test_target_404_is_reported_as_finding_not_error():
    fetch_404 = FetchResult(
        status=404,
        content_type="text/html",
        body="<html><body>Not Found</body></html>",
        response_time_ms=50,
    )
    with _mock_fetch(fetch_404), _mock_parse():
        report = await run_audit(_VALID_URL)

    assert report["status"] == 404
    assert "error" not in report


@pytest.mark.anyio
async def test_target_500_is_reported_as_finding_not_error():
    fetch_500 = FetchResult(
        status=500,
        content_type="text/html",
        body="<html><body>Server Error</body></html>",
        response_time_ms=80,
    )
    with _mock_fetch(fetch_500), _mock_parse():
        report = await run_audit(_VALID_URL)

    assert report["status"] == 500
    assert "error" not in report


@pytest.mark.anyio
async def test_missing_url_raises_app_error_missing_url():
    with _mock_fetch() as mock_fetch:
        with pytest.raises(AppError) as exc_info:
            await run_audit("")

    assert exc_info.value.code == "MISSING_URL"
    assert exc_info.value.status == 400
    mock_fetch.assert_not_called()


@pytest.mark.anyio
async def test_none_url_raises_app_error_missing_url():
    with _mock_fetch() as mock_fetch:
        with pytest.raises(AppError) as exc_info:
            await run_audit(None)

    assert exc_info.value.code == "MISSING_URL"
    mock_fetch.assert_not_called()


@pytest.mark.anyio
async def test_invalid_url_raises_app_error_invalid_url():
    with _mock_fetch() as mock_fetch:
        with pytest.raises(AppError) as exc_info:
            await run_audit("not-a-url")

    assert exc_info.value.code == "INVALID_URL"
    assert exc_info.value.status == 400
    mock_fetch.assert_not_called()


@pytest.mark.anyio
async def test_javascript_scheme_raises_invalid_url():
    with _mock_fetch() as mock_fetch:
        with pytest.raises(AppError) as exc_info:
            await run_audit("javascript:alert(1)")

    assert exc_info.value.code == "INVALID_URL"
    mock_fetch.assert_not_called()


@pytest.mark.anyio
async def test_timeout_app_error_propagates_from_fetcher():
    timeout_err = AppError("TIMEOUT", "request timed out")
    with patch("app.report_builder.fetch_page", new=AsyncMock(side_effect=timeout_err)):
        with pytest.raises(AppError) as exc_info:
            await run_audit(_VALID_URL)

    assert exc_info.value.code == "TIMEOUT"
    assert exc_info.value.status == 504


@pytest.mark.anyio
async def test_unreachable_app_error_propagates_from_fetcher():
    unreachable_err = AppError("UNREACHABLE", "cannot connect")
    with patch("app.report_builder.fetch_page", new=AsyncMock(side_effect=unreachable_err)):
        with pytest.raises(AppError) as exc_info:
            await run_audit(_VALID_URL)

    assert exc_info.value.code == "UNREACHABLE"
    assert exc_info.value.status == 502
