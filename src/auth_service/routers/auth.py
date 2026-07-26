from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from auth_service.database import get_session
from auth_service.dependencies import CurrentUser, SessionDep
from auth_service.models import User
from auth_service.schemas import (
    LoginRequest,
    LogoutRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from auth_service.services.supabase import (
    AuthError,
    criar_usuario,
    fazer_login,
    fazer_logout,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/cadastro",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def cadastro(body: RegisterRequest, session: SessionDep) -> TokenResponse:
    try:
        await criar_usuario(body.email, body.password, body.name)
        resultado = await fazer_login(body.email, body.password)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e

    user_data = resultado["user"]

    user = User(
        id=user_data["id"],
        email=user_data["email"],
        name=user_data.get("user_metadata", {}).get("name", body.name),
    )
    session.add(user)
    await session.commit()

    return TokenResponse(
        access_token=resultado["access_token"],
        user_id=user.id,
        email=user.email,
        name=user.name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: SessionDep) -> TokenResponse:
    try:
        resultado = await fazer_login(body.email, body.password)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e

    user_data = resultado["user"]

    result = await session.execute(
        select(User).where(User.email == body.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado. Faça o cadastro primeiro.",
        )

    return TokenResponse(
        access_token=resultado["access_token"],
        user_id=user.id,
        email=user.email,
        name=user.name,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest) -> None:
    await fazer_logout(body.access_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    """Retorna os dados do usuário autenticado."""
    return UserResponse.model_validate(current_user)
