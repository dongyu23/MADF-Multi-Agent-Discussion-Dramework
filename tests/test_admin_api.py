"""Admin API integration tests."""
import pytest
import httpx
from jose import jwt
import uuid, time

BASE = "http://localhost:8000"
ADMIN_SECRET = "change-me-in-production"


def _token():
    return jwt.encode({
        "sub": "audit-backend", "jti": str(uuid.uuid4()),
        "admin_id": str(uuid.uuid4()), "admin_username": "test-admin",
        "role": "superadmin", "exp": int(time.time()) + 300,
    }, ADMIN_SECRET, algorithm="HS256")


@pytest.mark.asyncio
async def test_health_detailed():
    async with httpx.AsyncClient(base_url=BASE) as c:
        r = await c.get("/api/v1/health/detailed")
        assert r.status_code == 200
        data = r.json()["data"]
        assert "components" in data
        assert "database" in data["components"]


@pytest.mark.asyncio
async def test_admin_auth_rejects_no_token():
    async with httpx.AsyncClient(base_url=BASE) as c:
        r = await c.get("/api/v1/admin/stats/overview")
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_auth_accepts_valid_token():
    async with httpx.AsyncClient(base_url=BASE) as c:
        r = await c.get("/api/v1/admin/stats/overview", headers={"Authorization": f"Bearer {_token()}"})
        assert r.status_code == 200
        assert r.json()["code"] == 200


@pytest.mark.asyncio
async def test_admin_auth_rejects_replay():
    t = _token()
    async with httpx.AsyncClient(base_url=BASE) as c:
        r1 = await c.get("/api/v1/admin/stats/overview", headers={"Authorization": f"Bearer {t}"})
        assert r1.status_code == 200
        r2 = await c.get("/api/v1/admin/stats/overview", headers={"Authorization": f"Bearer {t}"})
        assert r2.status_code == 403  # jti replay rejected


@pytest.mark.asyncio
async def test_admin_users_list():
    async with httpx.AsyncClient(base_url=BASE) as c:
        r = await c.get("/api/v1/admin/users?page_size=5", headers={"Authorization": f"Bearer {_token()}"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert "items" in data


@pytest.mark.asyncio
async def test_admin_health_overview():
    async with httpx.AsyncClient(base_url=BASE) as c:
        r = await c.get("/api/v1/admin/health/overview", headers={"Authorization": f"Bearer {_token()}"})
        assert r.status_code == 200
        comps = r.json()["data"]["components"]
        assert comps["database"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_admin_discussions_list():
    async with httpx.AsyncClient(base_url=BASE) as c:
        r = await c.get("/api/v1/admin/discussions?page_size=5", headers={"Authorization": f"Bearer {_token()}"})
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_characters_list():
    async with httpx.AsyncClient(base_url=BASE) as c:
        r = await c.get("/api/v1/admin/characters?page_size=5", headers={"Authorization": f"Bearer {_token()}"})
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_audit_events():
    async with httpx.AsyncClient(base_url=BASE) as c:
        r = await c.get("/api/v1/admin/audit/events?page_size=5&level=P0", headers={"Authorization": f"Bearer {_token()}"})
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_stats_overview():
    async with httpx.AsyncClient(base_url=BASE) as c:
        r = await c.get("/api/v1/admin/stats/overview", headers={"Authorization": f"Bearer {_token()}"})
        assert r.status_code == 200
        d = r.json()["data"]
        assert "total_users" in d
        assert "total_audit_events" in d
        assert d["total_audit_events"] > 0

