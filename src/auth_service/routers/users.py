from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, text

from auth_service.dependencies import CurrentUser, SessionDep
from auth_service.models import UserAsset
from auth_service.schemas import UserAssetRequest, UserAssetResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/assets", response_model=list[UserAssetResponse])
async def listar_assets(current_user: CurrentUser, session: SessionDep) -> list[UserAssetResponse]:
    """
    Retorna os ativos de interesse do usuário autenticado,
    com ticker e nome vindos de silver.assets via JOIN.
    """
    query = text("""
        SELECT
            ua.id,
            ua.asset_id,
            sa.ticker,
            sa.name AS asset_name,
            ua.quantity,
            ua.target_allocation
        FROM public.user_assets ua
        JOIN silver.assets sa ON sa.iid = ua.asset_id
        WHERE ua.user_id = :user_id
        ORDER BY sa.ticker
    """)

    result = await session.execute(query, {"user_id": current_user.id})
    rows = result.mappings().all()

    return [UserAssetResponse(**row) for row in rows]


@router.post("/me/assets", response_model=UserAssetResponse, status_code=status.HTTP_201_CREATED)
async def adicionar_asset(
    body: UserAssetRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> UserAssetResponse:
    """
    Adiciona um ativo ao portfólio do usuário.
    Verifica se o asset_id existe em silver.assets antes de inserir.
    """
    # Verifica se o ativo existe no pipeline
    asset_check = await session.execute(
        text("SELECT iid, ticker, name FROM silver.assets WHERE iid = :asset_id"),
        {"asset_id": body.asset_id},
    )
    asset = asset_check.mappings().one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ativo {body.asset_id} não encontrado em silver.assets.",
        )

    existing = await session.execute(
        select(UserAsset).where(
            UserAsset.user_id == current_user.id,
            UserAsset.asset_id == body.asset_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ativo já está na sua carteira.",
        )

    user_asset = UserAsset(
        user_id=current_user.id,
        asset_id=body.asset_id,
        quantity=body.quantity,
        target_allocation=body.target_allocation,
    )
    session.add(user_asset)
    await session.commit()
    await session.refresh(user_asset)

    return UserAssetResponse(
        id=user_asset.id,
        asset_id=user_asset.asset_id,
        ticker=asset["ticker"],
        asset_name=asset["name"],
        quantity=user_asset.quantity,
        target_allocation=user_asset.target_allocation,
    )


@router.delete("/me/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_asset(
    asset_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
) -> None:
    """Remove um ativo da carteira do usuário."""
    result = await session.execute(
        select(UserAsset).where(
            UserAsset.user_id == current_user.id,
            UserAsset.asset_id == asset_id,
        )
    )
    user_asset = result.scalar_one_or_none()

    if not user_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ativo não encontrado na sua carteira.",
        )

    await session.delete(user_asset)
    await session.commit()
