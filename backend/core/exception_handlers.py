import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.core.exceptions import BusinessException, ErrorCode
from backend.core.responses import Result

logger = logging.getLogger(__name__)


def _http_status(error_code: ErrorCode) -> int:
    """Map business error codes to proper HTTP status codes."""
    if error_code == ErrorCode.UNAUTHORIZED:
        return 401
    if error_code == ErrorCode.FORBIDDEN:
        return 403
    if error_code in (ErrorCode.NOT_FOUND, ErrorCode.USER_NOT_FOUND,
                      ErrorCode.SKILL_NOT_FOUND, ErrorCode.DISCUSSION_NOT_FOUND):
        return 404
    if error_code in (ErrorCode.USERNAME_EXISTS, ErrorCode.PHONE_EXISTS,
                      ErrorCode.SKILL_NAME_EXISTS, ErrorCode.SKILL_IN_USE):
        return 409
    if error_code == ErrorCode.INVALID_PARAMS:
        return 422
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessException)
    async def handle_business_exception(
        _request: Request, exc: BusinessException
    ) -> JSONResponse:
        result = Result.fail(exc.error_code, exc.detail)
        return JSONResponse(status_code=_http_status(exc.error_code), content=result.model_dump())

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unexpected error: %s", exc)
        result = Result.fail(ErrorCode.INTERNAL_ERROR, "Internal server error")
        return JSONResponse(status_code=500, content=result.model_dump())
