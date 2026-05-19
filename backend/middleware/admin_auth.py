"""服务间 JWT 验证 — 审计后端调主系统 /api/v1/admin/* 时的鉴权。

独立 ADMIN_JWT_SECRET，5 分钟过期，jti 防重放。
"""
import os
import time
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

_admin_bearer = HTTPBearer(auto_error=False)

ADMIN_JWT_SECRET = os.getenv("ADMIN_JWT_SECRET", "change-me-in-production")
ADMIN_JWT_ALGORITHM = os.getenv("ADMIN_JWT_ALGORITHM", "HS256")

_jti_cache: dict[str, float] = {}


async def verify_admin_service(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_admin_bearer),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin token required")

    try:
        payload = jwt.decode(
            credentials.credentials,
            ADMIN_JWT_SECRET,
            algorithms=[ADMIN_JWT_ALGORITHM],
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")

    if payload.get("sub") != "audit-backend":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an audit service token")

    jti = payload.get("jti", "")
    if jti:
        now = time.time()
        if jti in _jti_cache and now - _jti_cache[jti] < 300:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token already used")
        _jti_cache[jti] = now
        stale = [k for k, v in _jti_cache.items() if now - v > 300]
        for k in stale:
            del _jti_cache[k]

    return {
        "admin_id": payload.get("admin_id", ""),
        "admin_username": payload.get("admin_username", ""),
        "role": payload.get("role", ""),
    }
