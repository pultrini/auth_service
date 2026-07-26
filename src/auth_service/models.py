from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """
    Espelho local do auth.users do Supabase.
    O id é o mesmo UUID gerado pelo Supabase Auth — não geramos aqui.
    Criado no cadastro, sincronizado via FastAPI (nunca pelo pipeline).
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        comment="Mesmo UUID do auth.users do Supabase",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    assets: Mapped[list[UserAsset]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class UserAsset(Base):
    """
    Relação entre um usuário e um ativo de seu interesse.
    asset_id aponta para silver.assets.iid (gerenciado pelo pipeline).

    quantity e target_allocation são opcionais — o usuário pode adicionar
    um ativo só para acompanhar, sem necessariamente ter uma posição.
    """

    __tablename__ = "user_assets"
    __table_args__ = (UniqueConstraint("user_id", "asset_id", name="uq_user_asset"),)

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        comment="Ref: silver.assets.iid",
    )
    quantity: Mapped[float | None] = mapped_column(
        Numeric(18, 8),
        nullable=True,
        comment="Quantidade possuída (opcional)",
    )
    target_allocation: Mapped[float | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        comment="Meta de alocação 0.0 a 1.0 (opcional)",
    )
    added_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="assets")

    def __repr__(self) -> str:
        return f"<UserAsset user_id={self.user_id} asset_id={self.asset_id}>"
