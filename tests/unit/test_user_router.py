from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from auth_service.app import app
from auth_service.dependencies import get_current_user


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

_FAKE_ASSET_ROW = {
    "id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    "asset_id": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
    "ticker": "PETR4.SA",
    "asset_name": "Petrobras",
    "quantity": 100.0,
    "target_allocation": 0.2,
}


@pytest.fixture(autouse=True)
def override_auth():
    """Substitui o `get_current_user` pelo _FAKE_USER_DB durante os testes."""
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER_DB
    yield
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_list_assets_returns_empty_for_new_user(client):
    """GET /users/me/assets should return empty list for user with no assets."""
    with (
        patch(
            "auth_service.dependencies.get_current_user",
            return_value=_FAKE_USER_DB,
        ),
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.execute",
            new_callable=AsyncMock,
            return_value=MagicMock(
                mappings=MagicMock(
                    return_value=MagicMock(all=MagicMock(return_value=[]))
                )
            ),
        ),
    ):
        resp = await client.get(
            "/users/me/assets",
            headers={"Authorization": "Bearer fake-token"},
        )

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_add_asset_success(client):
    """POST /users/me/assets should return 201 with asset data."""
    mock_asset_check = MagicMock(
        mappings=MagicMock(
            return_value=MagicMock(
                one_or_none=MagicMock(
                    return_value={
                        "iid": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                        "ticker": "PETR4.SA",
                        "name": "Petrobras",
                    }
                )
            )
        )
    )
    mock_existing = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    async def fake_refresh(obj):
        obj.id = UUID("11111111-1111-1111-1111-111111111111")

    with (
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.execute",
            new_callable=AsyncMock,
            side_effect=[mock_asset_check, mock_existing],
        ),
        patch("sqlalchemy.ext.asyncio.AsyncSession.add"),
        patch("sqlalchemy.ext.asyncio.AsyncSession.commit", new_callable=AsyncMock),
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.refresh", 
            new_callable=AsyncMock, 
            side_effect=fake_refresh  # <--- Injetamos o UUID aqui
        ),
    ):
        resp = await client.post(
            "/users/me/assets",
            headers={"Authorization": "Bearer fake-token"},
            json={
                "asset_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "quantity": 100.0,
                "target_allocation": 0.2,
            },
        )

    assert resp.status_code == 201

    data = resp.json()
    assert data["id"] == "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
async def test_add_asset_not_found_returns_404(client):
    """POST /users/me/assets with unknown asset_id should return 404."""
    mock_not_found = MagicMock(
        mappings=MagicMock(
            return_value=MagicMock(one_or_none=MagicMock(return_value=None))
        )
    )

    with (
        patch(
            "auth_service.dependencies.get_current_user",
            return_value=_FAKE_USER_DB,
        ),
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.execute",
            new_callable=AsyncMock,
            return_value=mock_not_found,
        ),
    ):
        resp = await client.post(
            "/users/me/assets",
            headers={"Authorization": "Bearer fake-token"},
            json={"asset_id": "cccccccc-cccc-cccc-cccc-cccccccccccc"},
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_asset_invalid_allocation_returns_422(client):
    """POST /users/me/assets with target_allocation > 1 should return 422."""
    resp = await client.post(
        "/users/me/assets",
        headers={"Authorization": "Bearer fake-token"},
        json={
            "asset_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "target_allocation": 1.5,  # inválido
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_remove_asset_not_found_returns_404(client):
    """DELETE /users/me/assets/{id} for asset not in portfolio should return 404."""
    with (
        patch(
            "auth_service.dependencies.get_current_user",
            return_value=_FAKE_USER_DB,
        ),
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.execute",
            new_callable=AsyncMock,
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ),
    ):
        resp = await client.delete(
            "/users/me/assets/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            headers={"Authorization": "Bearer fake-token"},
        )

    assert resp.status_code == 404
