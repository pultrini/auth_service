from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from auth_service.services.supabase import AuthError


class FakeUser:
    def __init__(self, id_val, email, name):
        self.id = id_val
        self.email = email
        self.name = name


_FAKE_USER_DB = FakeUser(
    id_val=UUID("78d5cd52-9147-4d9d-bb38-08e0651f193d"),
    email="davi@teste.com",
    name="Davi",
)

_SUPABASE_RESULT = {
    "access_token": "jwt-token",
    "user": {
        "id": "78d5cd52-9147-4d9d-bb38-08e0651f193d",
        "email": "davi@teste.com",
        "user_metadata": {"name": "Davi"},
    },
}


@pytest.mark.asyncio
async def test_register_success(client):
    """POST /auth/cadastro should create user and return 201 with token."""
    with (
        patch("auth_service.routers.auth.criar_usuario", new_callable=AsyncMock),
        patch(
            "auth_service.routers.auth.fazer_login",
            new_callable=AsyncMock,
            return_value=_SUPABASE_RESULT,
        ),
        # 2. REMOVIDO: patch("auth_service.routers.auth.SessionDep", autospec=True)
        # Ao remover, paramos de quebrar o Pydantic.
        patch("sqlalchemy.ext.asyncio.AsyncSession.add"),
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.commit",
            new_callable=AsyncMock,
        ),
    ):
        resp = await client.post(
            "/auth/cadastro",
            json={
                "email": "davi@teste.com",
                "password": "senha123",
                "name": "Davi",
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Davi"
    assert "access_token" in data


@pytest.mark.asyncio
async def test_register_short_password_returns_422(client):
    """POST /auth/cadastro with short password should return 422."""
    resp = await client.post(
        "/auth/cadastro",
        json={"email": "davi@teste.com", "password": "123", "name": "Davi"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_short_name_returns_422(client):
    """POST /auth/cadastro with short name should return 422."""
    resp = await client.post(
        "/auth/cadastro",
        json={"email": "davi@teste.com", "password": "senha123", "name": "D"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email_returns_422(client):
    """POST /auth/cadastro with invalid email should return 422."""
    resp = await client.post(
        "/auth/cadastro",
        json={"email": "not-an-email", "password": "senha123", "name": "Davi"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    """POST /auth/login should return 200 with token when credentials are valid."""
    with (
        patch(
            "auth_service.routers.auth.fazer_login",
            new_callable=AsyncMock,
            return_value=_SUPABASE_RESULT,
        ),
        patch(
            "auth_service.routers.auth.select",
            return_value=MagicMock(),
        ),
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.execute",
            new_callable=AsyncMock,
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=_FAKE_USER_DB)
            ),
        ),
    ):
        resp = await client.post(
            "/auth/login",
            json={"email": "davi@teste.com", "password": "senha123"},
        )

    assert resp.status_code == 200
    assert resp.json()["access_token"] == "jwt-token"


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401(client):
    """POST /auth/login with wrong password should return 401."""

    with patch(
        "auth_service.routers.auth.fazer_login",
        new_callable=AsyncMock,
        side_effect=AuthError("Invalid login credentials", status_code=401),
    ):
        resp = await client.post(
            "/auth/login",
            json={"email": "davi@teste.com", "password": "wrong"},
        )

    assert resp.status_code == 401
    assert "Invalid login credentials" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_logout_success(client):
    """POST /auth/logout should return 204."""
    with patch(
        "auth_service.routers.auth.fazer_logout",
        new_callable=AsyncMock,
    ):
        resp = await client.post(
            "/auth/logout",
            json={"access_token": "jwt-token"},
        )

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_health(client):
    """GET /health should return 200 with status message."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "auth service is alive"
