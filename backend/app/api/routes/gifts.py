from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.gift import GiftCatalog
from app.models.snapshot import MarketSnapshot
from app.schemas.gift import GiftOut

router = APIRouter(prefix="/gifts", tags=["gifts"])


@router.get("", response_model=list[GiftOut])
async def list_gifts(session: AsyncSession = Depends(get_session)):
    """
    Return all gifts with the latest Fragment floor price.

    For each gift, picks the most recent market_snapshot (if any).
    """
    # Subquery: latest snapshot per slug
    latest_sq = (
        select(
            MarketSnapshot.gift_slug,
            func.max(MarketSnapshot.scanned_at).label("max_at"),
        )
        .group_by(MarketSnapshot.gift_slug)
        .subquery()
    )

    # Join gifts ← latest snapshot ← actual snapshot row
    stmt = (
        select(
            GiftCatalog.slug,
            GiftCatalog.name,
            GiftCatalog.image_url,
            GiftCatalog.total_supply,
            MarketSnapshot.price_amount.label("floor_price"),
            MarketSnapshot.currency,
        )
        .outerjoin(
            latest_sq,
            GiftCatalog.slug == latest_sq.c.gift_slug,
        )
        .outerjoin(
            MarketSnapshot,
            (MarketSnapshot.gift_slug == latest_sq.c.gift_slug)
            & (MarketSnapshot.scanned_at == latest_sq.c.max_at),
        )
        .order_by(GiftCatalog.name)
    )

    rows = await session.execute(stmt)
    return [GiftOut.model_validate(row._mapping) for row in rows]
