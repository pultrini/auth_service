from __future__ import annotations

import httpx

from auth_service.config import settings

_BASE = f"{settings.supabase_url}/auth/v1"

_ANON_HEADERS = {
    "apikey": settings.supabase_anon_key,
    "Content-Type": "application/json",
}

_ADMIN_HEADERS = {
    "apikey": settings.supabase_service_role_key,
    "Authorization": f"Bearer {settings.supabase_service_role_key}",
    "Content-Type": "application/json",
}
HTTP_STATUS_OK=200


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


async def criar_usuario(email: str, password: str, name: str) -> dict:
    """
    Cria usuário via Admin API com service role key.
    email_confirm=True garante que o usuário já nasce confirmado,
    sem precisar de email de verificação.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_BASE}/admin/users",
            headers=_ADMIN_HEADERS,
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"name": name},
            },
            timeout=10,
        )

    data = resp.json()

    if resp.status_code not in (200, 201):
        msg = (
            data.get("msg")
            or data.get("error_description")
            or data.get("message")
            or "Erro ao criar conta."
        )
        raise AuthError(msg, status_code=resp.status_code)

    return data


async def fazer_login(email: str, password: str) -> dict:
    """Login via anon key — retorna access_token e user."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_BASE}/token?grant_type=password",
            headers=_ANON_HEADERS,
            json={"email": email, "password": password},
            timeout=10,
        )

    data = resp.json()

    if resp.status_code != HTTP_STATUS_OK:
        msg = data.get("error_description", "Credenciais inválidas.")
        raise AuthError(msg, status_code=401)

    return data


async def fazer_logout(access_token: str) -> None:
    """Invalida o token no lado do Supabase."""
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{_BASE}/logout",
            headers={
                **_ANON_HEADERS,
                "Authorization": f"Bearer {access_token}",
            },
            timeout=10,
        )
