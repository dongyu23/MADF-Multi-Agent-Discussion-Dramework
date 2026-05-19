"""服务间 JWT 签发 — 审计后端调主系统 /api/v1/admin/* 时签发短时效服务 JWT。"""
import os, time, uuid
from jose import jwt

ADMIN_JWT_SECRET = os.getenv("ADMIN_JWT_SECRET", "change-me-in-production")

def issue_service_token(admin_id: str, admin_username: str, role: str) -> str:
    return jwt.encode({
        "sub": "audit-backend", "jti": str(uuid.uuid4()),
        "admin_id": admin_id, "admin_username": admin_username, "role": role,
        "exp": int(time.time()) + 300,
    }, ADMIN_JWT_SECRET, algorithm="HS256")
