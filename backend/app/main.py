import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .errors import AppError, make_error, to_error_body
from .routes.audit import router as audit_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("page_pulse")


def _parse_allowed_origins() -> list[str]:
    raw = os.environ.get("ALLOWED_ORIGINS", "*")
    if raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def create_app() -> FastAPI:
    app = FastAPI(
        title="Page Pulse API",
        description=(
            "Audits any public URL and returns a structured JSON report on "
            "that page's HTTP status, load time, SEO basics, and accessibility gaps."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    allowed_origins = _parse_allowed_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content=to_error_body(exc))

    @app.exception_handler(Exception)
    async def generic_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception")
        fallback = make_error(
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please try again.",
        )
        return JSONResponse(
            status_code=fallback.status, content=to_error_body(fallback)
        )

    app.include_router(audit_router, prefix="/api")

    @app.get("/health", tags=["infra"])
    async def health() -> dict[str, bool]:
        return {"ok": True}

    logger.info("Page Pulse API initialised. Allowed origins: %s", allowed_origins)
    return app


app = create_app()
