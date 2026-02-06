"""
Gift catalog API endpoints with multi-marketplace price support.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.gift import GiftCatalog
from app.models.snapshot import MarketSnapshot
from app.schemas.gift import (
    GiftOut,
    GiftListResponse,
    GiftListMeta,
    MarketplacePrice,
    PriceSummary,
)

router = APIRouter(prefix="/gifts", tags=["gifts"])

# Known marketplace sources
SOURCES = ["Fragment", "Portals", "Mrkt", "Getgems", "Tonnel"]


@router.get("", response_model=GiftListResponse)
async def list_gifts(
    session: AsyncSession = Depends(get_session),
    sort_by: str = Query("name", enum=["name", "best_price", "spread_pct"]),
    sort_order: str = Query("asc", enum=["asc", "desc"]),
    min_spread_pct: Optional[float] = Query(None, ge=0, le=100),
    search: Optional[str] = Query(None, min_length=1, max_length=50),
):
    """
    Return all gifts with prices from all marketplaces.

    Supports sorting by name, best price, or spread percentage.
    Supports filtering by minimum spread and search query.
    """
    # Subquery: latest snapshot per (slug, source)
    latest_sq = (
        select(
            MarketSnapshot.gift_slug,
            MarketSnapshot.source,
            func.max(MarketSnapshot.scanned_at).label("max_at"),
        )
        .group_by(MarketSnapshot.gift_slug, MarketSnapshot.source)
        .subquery()
    )

    # Get all gifts with their catalog info
    gifts_stmt = select(
        GiftCatalog.slug,
        GiftCatalog.name,
        GiftCatalog.image_url,
        GiftCatalog.total_supply,
    )
    if search:
        gifts_stmt = gifts_stmt.where(
            GiftCatalog.name.ilike(f"%{search}%")
        )
    gifts_stmt = gifts_stmt.order_by(GiftCatalog.name)

    gifts_result = await session.execute(gifts_stmt)
    gifts_data = {row.slug: row._mapping for row in gifts_result}

    if not gifts_data:
        return GiftListResponse(
            gifts=[],
            meta=GiftListMeta(total=0, sources=SOURCES),
        )

    # Get latest snapshots for all gifts
    snapshots_stmt = (
        select(
            MarketSnapshot.gift_slug,
            MarketSnapshot.source,
            MarketSnapshot.price_amount,
            MarketSnapshot.currency,
            MarketSnapshot.scanned_at,
        )
        .join(
            latest_sq,
            and_(
                MarketSnapshot.gift_slug == latest_sq.c.gift_slug,
                MarketSnapshot.source == latest_sq.c.source,
                MarketSnapshot.scanned_at == latest_sq.c.max_at,
            ),
        )
        .where(MarketSnapshot.gift_slug.in_(gifts_data.keys()))
    )

    snapshots_result = await session.execute(snapshots_stmt)

    # Group snapshots by gift slug
    gift_prices: dict[str, list[MarketplacePrice]] = {
        slug: [] for slug in gifts_data
    }
    latest_scan: Optional[datetime] = None

    for row in snapshots_result:
        gift_prices[row.gift_slug].append(
            MarketplacePrice(
                source=row.source,
                price=row.price_amount,
                currency=row.currency,
                updated_at=row.scanned_at,
            )
        )
        if latest_scan is None or row.scanned_at > latest_scan:
            latest_scan = row.scanned_at

    # Build response objects
    gifts: list[GiftOut] = []

    for slug, info in gifts_data.items():
        prices = gift_prices.get(slug, [])

        # Calculate spread
        valid_prices = [
            (p.source, p.price, p.currency)
            for p in prices
            if p.price is not None
        ]

        best_price = None
        worst_price = None
        spread_ton = None
        spread_pct = None
        arbitrage_signal = False

        if valid_prices:
            sorted_prices = sorted(valid_prices, key=lambda x: x[1])
            best = sorted_prices[0]
            worst = sorted_prices[-1]

            best_price = PriceSummary(
                source=best[0], price=best[1], currency=best[2] or "TON"
            )

            if len(valid_prices) >= 2:
                worst_price = PriceSummary(
                    source=worst[0], price=worst[1], currency=worst[2] or "TON"
                )
                spread_ton = worst[1] - best[1]
                if best[1] > 0:
                    spread_pct = float((spread_ton / best[1]) * 100)
                    arbitrage_signal = spread_pct >= 5.0

        gift = GiftOut(
            slug=slug,
            name=info["name"],
            image_url=info["image_url"],
            total_supply=info["total_supply"],
            prices=prices,
            best_price=best_price,
            worst_price=worst_price,
            spread_ton=spread_ton,
            spread_pct=round(spread_pct, 2) if spread_pct else None,
            arbitrage_signal=arbitrage_signal,
        )

        # Apply spread filter
        if min_spread_pct is not None:
            if spread_pct is None or spread_pct < min_spread_pct:
                continue

        gifts.append(gift)

    # Sort results
    reverse = sort_order == "desc"

    if sort_by == "name":
        gifts.sort(key=lambda g: g.name.lower(), reverse=reverse)
    elif sort_by == "best_price":
        gifts.sort(
            key=lambda g: (
                g.best_price.price if g.best_price else Decimal("999999")
            ),
            reverse=reverse,
        )
    elif sort_by == "spread_pct":
        gifts.sort(
            key=lambda g: g.spread_pct if g.spread_pct else -1,
            reverse=reverse,
        )

    return GiftListResponse(
        gifts=gifts,
        meta=GiftListMeta(
            total=len(gifts),
            scan_timestamp=latest_scan,
            sources=SOURCES,
        ),
    )


@router.get("/{slug}", response_model=GiftOut)
async def get_gift(
    slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Get detailed info for a single gift with all marketplace prices."""
    # Get gift info
    gift_stmt = select(GiftCatalog).where(GiftCatalog.slug == slug)
    gift_result = await session.execute(gift_stmt)
    gift = gift_result.scalar_one_or_none()

    if not gift:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Gift not found")

    # Get latest prices from all sources
    latest_sq = (
        select(
            MarketSnapshot.source,
            func.max(MarketSnapshot.scanned_at).label("max_at"),
        )
        .where(MarketSnapshot.gift_slug == slug)
        .group_by(MarketSnapshot.source)
        .subquery()
    )

    snapshots_stmt = (
        select(
            MarketSnapshot.source,
            MarketSnapshot.price_amount,
            MarketSnapshot.currency,
            MarketSnapshot.scanned_at,
        )
        .join(
            latest_sq,
            and_(
                MarketSnapshot.source == latest_sq.c.source,
                MarketSnapshot.scanned_at == latest_sq.c.max_at,
            ),
        )
        .where(MarketSnapshot.gift_slug == slug)
    )

    snapshots_result = await session.execute(snapshots_stmt)
    prices = [
        MarketplacePrice(
            source=row.source,
            price=row.price_amount,
            currency=row.currency,
            updated_at=row.scanned_at,
        )
        for row in snapshots_result
    ]

    # Calculate spread
    valid_prices = [(p.source, p.price, p.currency) for p in prices if p.price]
    best_price = worst_price = None
    spread_ton = spread_pct = None
    arbitrage_signal = False

    if valid_prices:
        sorted_prices = sorted(valid_prices, key=lambda x: x[1])
        best = sorted_prices[0]
        worst = sorted_prices[-1]

        best_price = PriceSummary(
            source=best[0], price=best[1], currency=best[2] or "TON"
        )

        if len(valid_prices) >= 2:
            worst_price = PriceSummary(
                source=worst[0], price=worst[1], currency=worst[2] or "TON"
            )
            spread_ton = worst[1] - best[1]
            if best[1] > 0:
                spread_pct = float((spread_ton / best[1]) * 100)
                arbitrage_signal = spread_pct >= 5.0

    return GiftOut(
        slug=gift.slug,
        name=gift.name,
        image_url=gift.image_url,
        total_supply=gift.total_supply,
        prices=prices,
        best_price=best_price,
        worst_price=worst_price,
        spread_ton=spread_ton,
        spread_pct=round(spread_pct, 2) if spread_pct else None,
        arbitrage_signal=arbitrage_signal,
    )
