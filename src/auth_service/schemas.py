from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

    @field_validator("password")
    @classmethod
    def minimal_password(cls, v: str) -> str:
        if len(v) < 6:  # noqa: PLR2004
            raise ValueError("A senha deve ter no mínimo 6 caracteres.")
        return v

    @field_validator("name")
    @classmethod
    def minimal_name(cls, v: str) -> str:
        if len(v.strip()) < 2:  # noqa: PLR2004
            raise ValueError("Nome deve ter ao menos 2 caracteres.")
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LogoutRequest(BaseModel):
    access_token: str


class TokenResponse(BaseModel):
    access_token: str
    user_id: UUID
    email: str
    name: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str

    model_config = {"from_attributes": True}


class UserAssetRequest(BaseModel):
    asset_id: UUID
    quantity: float | None = None
    target_allocation: float | None = None

    @field_validator("target_allocation")
    @classmethod
    def valid_allocation(cls, v: float | None) -> float | None:
        if v is not None and not (0 <= v <= 1):
            raise ValueError("target_allocation deve estar entre 0 e 1")
        return v

    @field_validator("quantity")
    @classmethod
    def positive_quantity(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("quantity deve ser positivo")
        return v


class UserAssetResponse(BaseModel):
    id: UUID
    asset_id: UUID
    ticker: str
    asset_name: str
    quantity: float | None
    target_allocation: float | None

    model_config = {"from_attributes": True}
