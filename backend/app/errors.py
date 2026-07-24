from typing import Literal

ErrorCode = Literal[
    "MISSING_URL",
    "INVALID_URL",
    "UNREACHABLE",
    "TIMEOUT",
    "UNSUPPORTED_CONTENT_TYPE",
    "RESPONSE_TOO_LARGE",
    "INTERNAL_ERROR",
]

STATUS_BY_CODE: dict[str, int] = {
    "MISSING_URL": 400,
    "INVALID_URL": 400,
    "UNREACHABLE": 502,
    "TIMEOUT": 504,
    "UNSUPPORTED_CONTENT_TYPE": 415,
    "RESPONSE_TOO_LARGE": 413,
    "INTERNAL_ERROR": 500,
}


class AppError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code: str = code
        self.message: str = message
        self.status: int = STATUS_BY_CODE[code]


def make_error(code: str, message: str) -> AppError:
    return AppError(code, message)


def to_error_body(err: AppError) -> dict[str, dict[str, str]]:
    return {"error": {"code": err.code, "message": err.message}}
