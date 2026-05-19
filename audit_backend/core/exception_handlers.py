from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from audit_backend.core.exceptions import (
    AuditException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from audit_backend.core.responses import Result


async def _audit_exception_handler(request: Request, exc: AuditException):
    return JSONResponse(
        status_code=500,
        content=Result.fail(exc.code, exc.message),
    )


async def _unauthorized_handler(request: Request, exc: UnauthorizedException):
    return JSONResponse(
        status_code=401,
        content=Result.fail(exc.code, exc.message),
    )


async def _forbidden_handler(request: Request, exc: ForbiddenException):
    return JSONResponse(
        status_code=403,
        content=Result.fail(exc.code, exc.message),
    )


async def _not_found_handler(request: Request, exc: NotFoundException):
    return JSONResponse(
        status_code=404,
        content=Result.fail(exc.code, exc.message),
    )


def register_handlers(app: FastAPI):
    app.add_exception_handler(AuditException, _audit_exception_handler)
    app.add_exception_handler(UnauthorizedException, _unauthorized_handler)
    app.add_exception_handler(ForbiddenException, _forbidden_handler)
    app.add_exception_handler(NotFoundException, _not_found_handler)
