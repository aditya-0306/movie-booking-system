from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils.logger import logger


class AppException(Exception):
    """Base class for expected, application-level errors (not bugs)."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # exc.errors() can contain raw, non-JSON-safe values -- most commonly
        # the raw request body as `bytes` when the body wasn't valid JSON at
        # all (e.g. a form-encoded body sent to a JSON-only endpoint, or a
        # malformed/empty body). Plain JSONResponse uses json.dumps directly
        # and has no idea how to serialize bytes, which is exactly what
        # crashed here. jsonable_encoder is FastAPI's own tool for turning
        # values like this into something JSON actually supports (bytes get
        # decoded to a string), so we run the error list through it first.
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation error", "errors": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Anything that reaches here is a genuine bug, not expected user error.
        # Log the full detail server-side, but never leak internals to the client.
        logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )
