import pytest

from app.validators.url import validate_url


def test_accepts_a_valid_https_url():
    result = validate_url("https://example.com")
    assert result.valid is True
    assert result.url == "https://example.com"
    assert result.code is None


def test_accepts_a_valid_http_url():
    result = validate_url("http://example.com")
    assert result.valid is True
    assert result.url == "http://example.com"


def test_strips_leading_and_trailing_whitespace_before_validating():
    result = validate_url("  https://example.com  ")
    assert result.valid is True
    assert result.url == "https://example.com"


def test_accepts_url_with_path_and_query():
    result = validate_url("https://example.com/path?q=1&page=2")
    assert result.valid is True


def test_rejects_an_empty_string():
    result = validate_url("")
    assert result.valid is False
    assert result.code == "MISSING_URL"


def test_rejects_a_whitespace_only_string():
    result = validate_url("   ")
    assert result.valid is False
    assert result.code == "MISSING_URL"


def test_rejects_none():
    result = validate_url(None)
    assert result.valid is False
    assert result.code == "MISSING_URL"


def test_rejects_an_integer():
    result = validate_url(42)
    assert result.valid is False
    assert result.code == "MISSING_URL"


def test_rejects_a_list():
    result = validate_url(["https://example.com"])
    assert result.valid is False
    assert result.code == "MISSING_URL"


def test_rejects_ftp_scheme():
    result = validate_url("ftp://example.com")
    assert result.valid is False
    assert result.code == "INVALID_URL"


def test_rejects_javascript_scheme():
    result = validate_url("javascript:alert(1)")
    assert result.valid is False
    assert result.code == "INVALID_URL"


def test_rejects_file_scheme():
    result = validate_url("file:///etc/passwd")
    assert result.valid is False
    assert result.code == "INVALID_URL"


def test_rejects_a_bare_hostname_with_no_scheme():
    result = validate_url("example.com")
    assert result.valid is False
    assert result.code == "INVALID_URL"


def test_rejects_a_plaintext_string_with_no_url_structure():
    result = validate_url("not a url")
    assert result.valid is False
    assert result.code == "INVALID_URL"


def test_rejects_a_url_with_missing_netloc():
    result = validate_url("https://")
    assert result.valid is False
    assert result.code == "INVALID_URL"
