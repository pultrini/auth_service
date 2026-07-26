from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from auth_service.app import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
