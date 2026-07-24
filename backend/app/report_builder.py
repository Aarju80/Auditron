from datetime import datetime, timezone
from typing import Any, TypedDict

from .errors import make_error
from .fetcher import fetch_page
from .parser.parse import parse_html
from .validators.url import validate_url


class AuditReport(TypedDict):
    url: str
    status: int
    responseTimeMs: int
    title: str | None
    metaDescription: str | None
    h1Count: int
    imagesMissingAlt: int
    totalImages: int
    approxWordCount: int
    fetchedAt: str


async def run_audit(raw_url: Any) -> AuditReport:
    validation = validate_url(raw_url)
    if not validation.valid:
        message = (
            'The "url" field is required.'
            if validation.code == "MISSING_URL"
            else f'"{raw_url}" is not a valid http(s) URL.'
        )
        raise make_error(validation.code, message)  # type: ignore[arg-type]

    assert validation.url is not None
    url = validation.url

    fetch_result = await fetch_page(url)
    signals = parse_html(fetch_result.body)

    fetched_at = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    return AuditReport(
        url=url,
        status=fetch_result.status,
        responseTimeMs=fetch_result.response_time_ms,
        title=signals["title"],
        metaDescription=signals["meta_description"],
        h1Count=signals["h1_count"],
        imagesMissingAlt=signals["images_missing_alt"],
        totalImages=signals["total_images"],
        approxWordCount=signals["approx_word_count"],
        fetchedAt=fetched_at,
    )
