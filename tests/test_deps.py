"""Dependency injection unit tests."""
import uuid
import pytest
from unittest.mock import patch
from fastapi import HTTPException
from jose import jwt

from backend.config import settings
from backend.deps import get_current_user, require_user


def _make_token(user_id: str, secret: str | None = None, algorithm: str | None = None) -> str:
    return jwt.encode({"sub": user_id}, secret or settings.jwt_secret, algorithm=algorithm or settings.jwt_algorithm)


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_no_token_returns_empty_string(self):
        result = await get_current_user(credentials=None)
        assert result == ""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_id(self):
        uid = str(uuid.uuid4())
        token = _make_token(uid)
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        result = await get_current_user(credentials=creds)
        assert result == uid

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token.here")
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=creds)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_token_wrong_secret_raises_401(self):
        token = _make_token(str(uuid.uuid4()), secret="wrong-secret-12345")
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=creds)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_token_expired_raises_401(self):
        from datetime import datetime, timedelta, timezone
        expire = datetime.now(timezone.utc) - timedelta(minutes=10)
        token = jwt.encode({"sub": "test", "exp": expire}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=creds)
        assert exc.value.status_code == 401


class TestRequireUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_user_id(self):
        result = await require_user(user_id=str(uuid.uuid4()))
        assert result

    @pytest.mark.asyncio
    async def test_empty_string_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            await require_user(user_id="")
        assert exc.value.status_code == 401
