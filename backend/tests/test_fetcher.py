import unittest.mock as mock

import httpx
import pytest

from app.errors import AppError
from app.fetcher import MAX_BYTES, fetch_page

_MINIMAL_HTML = b"<html><head><title>Test</title></head><body>Hello</body></html>"


def _make_transport(
    *,
    body: bytes = _MINIMAL_HTML,
    status: int = 200,
    content_type: str = "text/html; charset=utf-8",
    content_length: str | None = None,
) -> httpx.MockTransport:
    headers = {"content-type": content_type}
    if content_length is not None:
        headers["content-length"] = content_length

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status, content=body, headers=headers)

    return httpx.MockTransport(handler)


async def _fetch(url: str = "https://example.com", **transport_kwargs):
    import app.fetcher as fetcher_module

    transport = _make_transport(**transport_kwargs)

    class _MockedAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            kwargs["transport"] = transport
            kwargs.pop("timeout", None)
            super().__init__(**kwargs)

    with mock.patch.object(fetcher_module.httpx, "AsyncClient", _MockedAsyncClient):
        return await fetch_page(url)


@pytest.mark.anyio
async def test_returns_fetch_result_on_success():
    result = await _fetch()
    assert result.status == 200
    assert result.body == _MINIMAL_HTML.decode("utf-8")
    assert "text/html" in result.content_type
    assert result.response_time_ms >= 0


@pytest.mark.anyio
async def test_captures_non_200_target_status_as_finding():
    result = await _fetch(status=404)
    assert result.status == 404


@pytest.mark.anyio
async def test_returns_correct_content_type_in_result():
    result = await _fetch(content_type="text/html; charset=utf-8")
    assert result.content_type == "text/html; charset=utf-8"


@pytest.mark.anyio
async def test_raises_unsupported_content_type_for_pdf():
    with pytest.raises(AppError) as exc_info:
        await _fetch(content_type="application/pdf")
    assert exc_info.value.code == "UNSUPPORTED_CONTENT_TYPE"
    assert exc_info.value.status == 415


@pytest.mark.anyio
async def test_raises_unsupported_content_type_for_json():
    with pytest.raises(AppError) as exc_info:
        await _fetch(content_type="application/json")
    assert exc_info.value.code == "UNSUPPORTED_CONTENT_TYPE"


@pytest.mark.anyio
async def test_raises_unsupported_content_type_for_image():
    with pytest.raises(AppError) as exc_info:
        await _fetch(content_type="image/jpeg")
    assert exc_info.value.code == "UNSUPPORTED_CONTENT_TYPE"


@pytest.mark.anyio
async def test_raises_response_too_large_when_content_length_exceeds_cap():
    oversized = str(MAX_BYTES + 1)
    with pytest.raises(AppError) as exc_info:
        await _fetch(content_length=oversized)
    assert exc_info.value.code == "RESPONSE_TOO_LARGE"
    assert exc_info.value.status == 413


@pytest.mark.anyio
async def test_malformed_content_length_header_does_not_crash():
    result = await _fetch(content_length="not-a-number")
    assert result.status == 200


@pytest.mark.anyio
async def test_raises_timeout_when_request_exceeds_budget():
    import app.fetcher as fetcher_module

    class _TimeoutTransport(httpx.MockTransport):
        def __init__(self):
            pass

        def handle_request(self, _request):
            raise httpx.TimeoutException("timed out", request=_request)

        async def handle_async_request(self, _request):
            raise httpx.TimeoutException("timed out", request=_request)

    class _MockedAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            kwargs["transport"] = _TimeoutTransport()
            kwargs.pop("timeout", None)
            super().__init__(**kwargs)

    with mock.patch.object(fetcher_module.httpx, "AsyncClient", _MockedAsyncClient):
        with pytest.raises(AppError) as exc_info:
            await fetch_page("https://example.com")

    assert exc_info.value.code == "TIMEOUT"
    assert exc_info.value.status == 504


@pytest.mark.anyio
async def test_raises_unreachable_on_connection_failure():
    import app.fetcher as fetcher_module

    class _ConnectErrorTransport(httpx.MockTransport):
        def __init__(self):
            pass

        async def handle_async_request(self, request):
            raise httpx.ConnectError("connection refused", request=request)

    class _MockedAsyncClient(httpx.AsyncClient):
        def __init__(self, **kwargs):
            kwargs["transport"] = _ConnectErrorTransport()
            kwargs.pop("timeout", None)
            super().__init__(**kwargs)

    with mock.patch.object(fetcher_module.httpx, "AsyncClient", _MockedAsyncClient):
        with pytest.raises(AppError) as exc_info:
            await fetch_page("https://example.com")

    assert exc_info.value.code == "UNREACHABLE"
    assert exc_info.value.status == 502
