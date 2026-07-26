from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auth_service.services.supabase import (
    AuthError,
    criar_usuario,
    fazer_login,
    fazer_logout,
)


@pytest.mark.asyncio
async def test_create_user_success():
    """criar_usuario should return user dict when Supabase responds 201."""
    mock_resp = MagicMock(
        status_code=201,
        json=lambda: {
            "id": "uuid-001",
            "email": "davi@teste.com",
            "user_metadata": {"name": "Davi"},
        },
    )

    with patch("auth_service.services.supabase.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_resp
        )
        result = await criar_usuario("davi@teste.com", "senha123", "Davi")

    assert result["email"] == "davi@teste.com"
    assert result["user_metadata"]["name"] == "Davi"


@pytest.mark.asyncio
async def test_create_user_already_exists_raises_auth_error():
    """criar_usuario should raise AuthError when Supabase returns 422."""
    mock_resp = MagicMock(
        status_code=422,
        json=lambda: {"message": "User already registered"},
    )

    with patch("auth_service.services.supabase.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_resp
        )
        with pytest.raises(AuthError, match="User already registered"):
            await criar_usuario("davi@teste.com", "senha123", "Davi")


@pytest.mark.asyncio
async def test_login_success():
    """fazer_login should return access_token and user when credentials are valid."""
    mock_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "access_token": "jwt-token",
            "user": {
                "id": "uuid-001",
                "email": "davi@teste.com",
                "user_metadata": {"name": "Davi"},
            },
        },
    )

    with patch("auth_service.services.supabase.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_resp
        )
        result = await fazer_login("davi@teste.com", "senha123")

    assert result["access_token"] == "jwt-token"
    assert result["user"]["email"] == "davi@teste.com"


@pytest.mark.asyncio
async def test_login_invalid_credentials_raises_auth_error():
    """fazer_login should raise AuthError with 401 when credentials are wrong."""
    mock_resp = MagicMock(
        status_code=400,
        json=lambda: {"error_description": "Invalid login credentials"},
    )

    with patch("auth_service.services.supabase.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_resp
        )
        with pytest.raises(AuthError) as exc_info:
            await fazer_login("davi@teste.com", "wrong-password")

    assert exc_info.value.status_code == 401
    assert "Invalid login credentials" in str(exc_info.value)


@pytest.mark.asyncio
async def test_logout_calls_supabase():
    """fazer_logout should call Supabase with the correct Bearer token."""
    with patch("auth_service.services.supabase.httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock(return_value=MagicMock(status_code=204))
        mock_client.return_value.__aenter__.return_value.post = mock_post

        await fazer_logout("jwt-token")

    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer jwt-token"
