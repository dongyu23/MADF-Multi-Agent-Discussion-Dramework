import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.fixture(scope="session")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
async def auth_headers(client):
    await client.post("/api/v1/auth/register", json={
        "username": "int_test_user", "password": "test123456",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "username": "int_test_user", "password": "test123456",
    })
    token = resp.json()["data"]["token"]["token"]
    return {"Authorization": f"Bearer {token}"}
