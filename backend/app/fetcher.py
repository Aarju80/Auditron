import os
import time
from dataclasses import dataclass

import httpx

from .content_guard import assert_html_content_type
from .errors import AppError, make_error

TIMEOUT_SECONDS: float = float(os.environ.get("TIMEOUT_SECONDS", "8"))
MAX_BYTES: int = int(os.environ.get("MAX_BODY_BYTES", str(5 * 1024 * 1024)))
USER_AGENT: str = "Auditron/1.0 (+https://digitalheroesco.com)"


@dataclass(frozen=True)
class FetchResult:
    status: int
    content_type: str
    body: str
    response_time_ms: int


async def fetch_page(url: str) -> FetchResult:
    start = time.monotonic()

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            async with client.stream("GET", url) as response:
                content_type = response.headers.get("content-type", "")

                assert_html_content_type(content_type)

                declared_length = response.headers.get("content-length")
                if declared_length:
                    try:
                        declared_bytes = int(declared_length)
                    except ValueError:
                        declared_bytes = 0
                    if declared_bytes > MAX_BYTES:
                        raise make_error(
                            "RESPONSE_TOO_LARGE",
                            f"The response is larger than the {MAX_BYTES:,} byte limit.",
                        )

                chunks = bytearray()
                async for chunk in response.aiter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > MAX_BYTES:
                        raise make_error(
                            "RESPONSE_TOO_LARGE",
                            f"The response body exceeded the {MAX_BYTES:,} byte limit.",
                        )

                body = chunks.decode("utf-8", errors="replace")
                status = response.status_code

    except AppError:
        raise
    except httpx.TimeoutException:
        raise make_error(
            "TIMEOUT",
            f"The target page did not respond within {int(TIMEOUT_SECONDS * 1000)} ms.",
        )
    except httpx.RequestError as exc:
        raise make_error(
            "UNREACHABLE",
            f"Could not reach the target URL: {exc}",
        )

    response_time_ms = int((time.monotonic() - start) * 1000)

    return FetchResult(
        status=status,
        content_type=content_type,
        body=body,
        response_time_ms=response_time_ms,
    )
