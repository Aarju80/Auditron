import json

import pytest

from app.errors import AppError, STATUS_BY_CODE, make_error, to_error_body


def test_status_by_code_contains_all_seven_error_codes():
    expected = {
        "MISSING_URL",
        "INVALID_URL",
        "UNREACHABLE",
        "TIMEOUT",
        "UNSUPPORTED_CONTENT_TYPE",
        "RESPONSE_TOO_LARGE",
        "INTERNAL_ERROR",
    }
    assert set(STATUS_BY_CODE.keys()) == expected


def test_all_status_codes_are_valid_http_4xx_or_5xx():
    for code, status in STATUS_BY_CODE.items():
        assert 400 <= status < 600, (
            f"Error code {code!r} maps to {status}, which is not a 4xx or 5xx HTTP status"
        )


@pytest.mark.parametrize(
    "code, expected_status",
    [
        ("MISSING_URL", 400),
        ("INVALID_URL", 400),
        ("UNREACHABLE", 502),
        ("TIMEOUT", 504),
        ("UNSUPPORTED_CONTENT_TYPE", 415),
        ("RESPONSE_TOO_LARGE", 413),
        ("INTERNAL_ERROR", 500),
    ],
)
def test_app_error_resolves_correct_http_status(code, expected_status):
    err = AppError(code, "test message")
    assert err.status == expected_status


def test_app_error_stores_code_attribute():
    err = AppError("TIMEOUT", "timed out")
    assert err.code == "TIMEOUT"


def test_app_error_stores_message_attribute():
    err = AppError("TIMEOUT", "timed out")
    assert err.message == "timed out"


def test_app_error_is_an_exception_subclass():
    err = AppError("INTERNAL_ERROR", "something broke")
    assert isinstance(err, Exception)


def test_app_error_str_is_the_message():
    err = AppError("INVALID_URL", "bad url provided")
    assert str(err) == "bad url provided"


def test_app_error_can_be_raised_and_caught():
    with pytest.raises(AppError) as exc_info:
        raise AppError("TIMEOUT", "request timed out")
    assert exc_info.value.code == "TIMEOUT"
    assert exc_info.value.status == 504


def test_app_error_unknown_code_raises_key_error():
    with pytest.raises(KeyError):
        AppError("NONEXISTENT_CODE", "this should not exist")


def test_make_error_returns_an_app_error_instance():
    err = make_error("TIMEOUT", "too slow")
    assert isinstance(err, AppError)


def test_make_error_does_not_raise():
    try:
        err = make_error("INVALID_URL", "bad input")
    except Exception as exc:
        pytest.fail(f"make_error raised unexpectedly: {exc}")
    assert err.code == "INVALID_URL"


def test_make_error_sets_all_attributes_correctly():
    err = make_error("UNREACHABLE", "cannot connect")
    assert err.code == "UNREACHABLE"
    assert err.message == "cannot connect"
    assert err.status == 502


def test_to_error_body_returns_correct_envelope_shape():
    err = AppError("TIMEOUT", "the page timed out")
    body = to_error_body(err)
    assert "error" in body
    assert body["error"]["code"] == "TIMEOUT"
    assert body["error"]["message"] == "the page timed out"


def test_to_error_body_envelope_has_only_error_key():
    err = AppError("INVALID_URL", "bad url")
    body = to_error_body(err)
    assert list(body.keys()) == ["error"]


def test_to_error_body_error_object_has_exactly_code_and_message():
    err = AppError("INTERNAL_ERROR", "something failed")
    body = to_error_body(err)
    assert set(body["error"].keys()) == {"code", "message"}


def test_to_error_body_is_json_serialisable():
    err = AppError("RESPONSE_TOO_LARGE", "body too big")
    body = to_error_body(err)
    serialised = json.dumps(body)
    assert isinstance(serialised, str)
