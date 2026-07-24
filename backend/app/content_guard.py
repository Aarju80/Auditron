from .errors import make_error


def assert_html_content_type(content_type: str) -> None:
    normalised = (content_type or "").lower()
    if "text/html" not in normalised:
        raise make_error(
            "UNSUPPORTED_CONTENT_TYPE",
            f'Expected an HTML page but received content-type "{content_type or "unknown"}". '
            "Only text/html responses can be audited.",
        )


def is_html_content_type(content_type: str) -> bool:
    return "text/html" in (content_type or "").lower()
