from dataclasses import dataclass
from urllib.parse import urlparse

_ALLOWED_SCHEMES = frozenset({"http", "https"})


@dataclass(frozen=True)
class UrlValidationResult:
    valid: bool
    url: str | None = None
    code: str | None = None


def validate_url(raw_input: object) -> UrlValidationResult:
    if not isinstance(raw_input, str) or not raw_input.strip():
        return UrlValidationResult(valid=False, code="MISSING_URL")

    candidate = raw_input.strip()

    try:
        parsed = urlparse(candidate)
    except ValueError:
        return UrlValidationResult(valid=False, code="INVALID_URL")

    if parsed.scheme not in _ALLOWED_SCHEMES or not parsed.netloc:
        return UrlValidationResult(valid=False, code="INVALID_URL")

    return UrlValidationResult(valid=True, url=candidate)
