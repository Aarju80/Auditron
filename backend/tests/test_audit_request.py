import pytest
from pydantic import ValidationError

from app.routes.audit import AuditRequest


def test_accepts_a_valid_url_string():
    req = AuditRequest(url="https://example.com")
    assert req.url == "https://example.com"


def test_strips_surrounding_whitespace_from_url():
    req = AuditRequest(url="  https://example.com  ")
    assert req.url == "https://example.com"


def test_accepts_url_with_path_query_and_fragment():
    req = AuditRequest(url="https://example.com/page?ref=1#section")
    assert req.url == "https://example.com/page?ref=1#section"


def test_rejects_a_blank_url_string():
    with pytest.raises(ValidationError) as exc_info:
        AuditRequest(url="")
    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("url",)


def test_rejects_a_whitespace_only_url():
    with pytest.raises(ValidationError) as exc_info:
        AuditRequest(url="    ")
    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("url",)


def test_rejects_missing_url_field():
    with pytest.raises(ValidationError) as exc_info:
        AuditRequest()  # type: ignore[call-arg]
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("url",) for e in errors)


def test_rejects_non_string_url_value():
    with pytest.raises(ValidationError):
        AuditRequest(url=12345)  # type: ignore[arg-type]
