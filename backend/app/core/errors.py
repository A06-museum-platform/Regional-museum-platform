"""Contract-shaped API errors: every error responds {detail, code}.

FastAPI's own errors are reshaped too, so no response falls back to the
framework default:
  request validation  -> 422 {detail: first problem, code: VALIDATION_ERROR,
                               fields: {field: message}}
  HTTPException       -> same status, {detail, code} with a code derived
                         from the status (404 NOT_FOUND, 405 ...)
  anything unexpected -> 500 {detail, code: INTERNAL_ERROR}, no stack trace
"""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("museum.api")

_STATUS_CODES = {
    400: "VALIDATION_ERROR",
    401: "AUTH_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "FILE_TOO_LARGE",
    422: "VALIDATION_ERROR",
}


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str, code: str):
        self.status_code = status_code
        self.detail = detail
        self.code = code


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


def _field_name(loc) -> str:
    # ("body", "visitor", "email") -> "visitor.email"; drop the location part.
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "header")]
    return ".".join(parts) or "request"


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    fields: dict[str, str] = {}
    for error in exc.errors():
        message = error.get("msg", "Invalid value")
        # Our own model validators raise ValueError; pydantic prefixes it.
        message = message.removeprefix("Value error, ")
        fields.setdefault(_field_name(error.get("loc", ())), message)
    first = next(iter(fields.items()), ("request", "Invalid input data"))
    return JSONResponse(
        status_code=422,
        content={
            "detail": f"{first[0]}: {first[1]}" if first[0] != "request" else first[1],
            "code": "VALIDATION_ERROR",
            "fields": fields,
        },
    )


async def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail, "code": _STATUS_CODES.get(exc.status_code, "ERROR")},
        headers=getattr(exc, "headers", None),
    )


async def unexpected_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our side. Please try again.",
                 "code": "INTERNAL_ERROR"},
    )


def install_error_handlers(app) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
