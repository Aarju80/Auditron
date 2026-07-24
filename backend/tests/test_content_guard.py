import pytest

from app.content_guard import assert_html_content_type, is_html_content_type
from app.errors import AppError


def test_allows_text_html_with_charset():
    assert_html_content_type("text/html; charset=utf-8")


def test_allows_text_html_without_charset():
    assert_html_content_type("text/html")


def test_allows_text_html_uppercase():
    assert_html_content_type("TEXT/HTML; CHARSET=UTF-8")


def test_allows_text_html_mixed_case():
    assert_html_content_type("Text/Html")


def test_rejects_application_pdf():
    with pytest.raises(AppError) as exc_info:
        assert_html_content_type("application/pdf")
    assert exc_info.value.code == "UNSUPPORTED_CONTENT_TYPE"
    assert exc_info.value.status == 415


def test_rejects_image_png():
    with pytest.raises(AppError) as exc_info:
        assert_html_content_type("image/png")
    assert exc_info.value.code == "UNSUPPORTED_CONTENT_TYPE"


def test_rejects_application_json():
    with pytest.raises(AppError) as exc_info:
        assert_html_content_type("application/json")
    assert exc_info.value.code == "UNSUPPORTED_CONTENT_TYPE"


def test_rejects_text_plain():
    with pytest.raises(AppError) as exc_info:
        assert_html_content_type("text/plain")
    assert exc_info.value.code == "UNSUPPORTED_CONTENT_TYPE"


def test_rejects_application_xml():
    with pytest.raises(AppError) as exc_info:
        assert_html_content_type("application/xml")
    assert exc_info.value.code == "UNSUPPORTED_CONTENT_TYPE"


def test_rejects_empty_string():
    with pytest.raises(AppError) as exc_info:
        assert_html_content_type("")
    assert exc_info.value.code == "UNSUPPORTED_CONTENT_TYPE"


def test_error_message_includes_received_content_type():
    with pytest.raises(AppError) as exc_info:
        assert_html_content_type("application/pdf")
    assert "application/pdf" in exc_info.value.message


def test_rejects_unknown_content_type_reports_unknown_in_message():
    with pytest.raises(AppError) as exc_info:
        assert_html_content_type("")
    assert "unknown" in exc_info.value.message


def test_is_html_returns_true_for_text_html():
    assert is_html_content_type("text/html; charset=utf-8") is True


def test_is_html_returns_true_case_insensitively():
    assert is_html_content_type("TEXT/HTML") is True


def test_is_html_returns_false_for_pdf():
    assert is_html_content_type("application/pdf") is False


def test_is_html_returns_false_for_empty_string():
    assert is_html_content_type("") is False
