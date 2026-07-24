import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from ..errors import AppError, make_error, to_error_body
from ..report_builder import run_audit

router = APIRouter()
logger = logging.getLogger("auditron")


class AuditRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def url_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(
                "The 'url' field must not be blank. "
                "Provide a valid http(s):// URL."
            )
        return stripped


class AuditErrorDetail(BaseModel):
    code: str
    message: str


class AuditErrorResponse(BaseModel):
    error: AuditErrorDetail


@router.post(
    "/audit",
    response_model=None,
    summary="Audit a URL",
    description=(
        "Accepts a public URL and returns a structured JSON report covering "
        "HTTP status, response time, SEO signals (title, meta description, "
        "H1 count), accessibility gaps (images missing alt text), and an "
        "approximate visible word count."
    ),
    responses={
        200: {"description": "Audit report for the given URL."},
        400: {"model": AuditErrorResponse, "description": "Invalid or missing URL."},
        413: {"model": AuditErrorResponse, "description": "Response body too large."},
        415: {"model": AuditErrorResponse, "description": "Non-HTML content type."},
        422: {"description": "Request body failed schema validation."},
        502: {"model": AuditErrorResponse, "description": "Target URL unreachable."},
        504: {"model": AuditErrorResponse, "description": "Target URL timed out."},
        500: {"model": AuditErrorResponse, "description": "Unexpected internal error."},
    },
    tags=["audit"],
)
async def audit(body: AuditRequest) -> JSONResponse:
    try:
        report = await run_audit(body.url)
        return JSONResponse(status_code=200, content=report)
    except AppError as err:
        return JSONResponse(status_code=err.status, content=to_error_body(err))
    except Exception:
        logger.exception("Unexpected error in POST /api/audit")
        fallback = make_error(
            "INTERNAL_ERROR",
            "An unexpected error occurred while auditing this page.",
        )
        return JSONResponse(
            status_code=fallback.status, content=to_error_body(fallback)
        )
