"""
Market statistics API endpoints.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.market_stats import GiftMarketStats, RarityTierStats, market_stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/market")
async def get_market_stats(
    slug: Optional[str] = Query(None, description="Filter to a single gift slug"),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """
    Return market statistics for all gifts, sorted by liquidity_score descending.

    Pass ?slug=xxx to retrieve stats for a single gift only.

    Each entry contains:
    - active_listings, floor_price, avg_listing_price
    - sales_7d, sales_30d, avg/median sale prices
    - liquidity_score (0–1), price_trend_7d, days_of_inventory
    - rarity_breakdown: per-tier floor price, sales median, premium vs common
    """
    all_stats = await market_stats_service.get_stats_for_all_gifts(session)

    if slug:
        all_stats = [s for s in all_stats if s.slug == slug]

    return [_to_dict(s) for s in all_stats]


def _to_dict(s: GiftMarketStats) -> dict[str, Any]:
    """Convert GiftMarketStats to a JSON-serialisable dict."""
    return {
        "slug": s.slug,
        "name": s.name,
        "active_listings": s.active_listings,
        "floor_price": float(s.floor_price) if s.floor_price is not None else None,
        "avg_listing_price": (
            float(s.avg_listing_price) if s.avg_listing_price is not None else None
        ),
        "sales_7d": s.sales_7d,
        "sales_30d": s.sales_30d,
        "avg_sale_price_7d": (
            float(s.avg_sale_price_7d) if s.avg_sale_price_7d is not None else None
        ),
        "median_sale_price_7d": (
            float(s.median_sale_price_7d)
            if s.median_sale_price_7d is not None
            else None
        ),
        "last_sale_days_ago": s.last_sale_days_ago,
        "liquidity_score": round(s.liquidity_score, 4),
        "price_trend_7d": s.price_trend_7d,
        "days_of_inventory": (
            round(s.days_of_inventory, 1) if s.days_of_inventory is not None else None
        ),
        "rarity_breakdown": {
            tier: _tier_to_dict(ts)
            for tier, ts in (s.rarity_breakdown or {}).items()
            if ts.active_listings > 0 or ts.sales_30d > 0
        },
    }


def _tier_to_dict(ts: RarityTierStats) -> dict[str, Any]:
    return {
        "active_listings": ts.active_listings,
        "floor_price": float(ts.floor_price) if ts.floor_price is not None else None,
        "median_sale_price_30d": (
            float(ts.median_sale_price_30d)
            if ts.median_sale_price_30d is not None
            else None
        ),
        "sales_30d": ts.sales_30d,
        "premium_vs_common": (
            round(ts.premium_vs_common, 2)
            if ts.premium_vs_common is not None
            else None
        ),
    }
