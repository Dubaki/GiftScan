"""
Market statistics service — aggregates listing and sales data per gift/collection.

Computes:
- Active inventory (count, floor price, avg listing price)
- Sales velocity (7d, 30d counts and prices)
- Per-rarity-tier breakdown (floor price, sales median, premium vs common)
- Derived metrics: liquidity score, price trend, days of inventory
"""

import logging
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gift import GiftCatalog
from app.models.listing import GiftListing
from app.models.sale import GiftSale
from app.models.snapshot import MarketSnapshot

logger = logging.getLogger(__name__)


@dataclass
class RarityTierStats:
    """Statistics for a single rarity tier within a gift collection."""
    tier: str
    active_listings: int
    floor_price: Optional[Decimal]       # cheapest active listing in this tier
    median_sale_price_30d: Optional[Decimal]
    sales_30d: int
    premium_vs_common: Optional[float]   # floor_price / common_floor; None if no common data


@dataclass
class GiftMarketStats:
    slug: str
    name: str
    # Current inventory
    active_listings: int
    floor_price: Optional[Decimal]
    avg_listing_price: Optional[Decimal]
    # Sales history
    sales_7d: int
    sales_30d: int
    avg_sale_price_7d: Optional[Decimal]
    median_sale_price_7d: Optional[Decimal]
    last_sale_days_ago: Optional[int]
    # Derived metrics
    liquidity_score: float       # sales_7d / max(active_listings, 1), capped 0–1
    price_trend_7d: str          # "up" | "down" | "stable" | "unknown"
    days_of_inventory: Optional[float]  # active_listings / (sales_7d / 7); None if 0 sales
    # Per-rarity breakdown (key = tier name)
    rarity_breakdown: dict[str, RarityTierStats] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.rarity_breakdown is None:
            self.rarity_breakdown = {}


class MarketStatsService:
    """Aggregates market data from gift_listings, gift_sales, and market_snapshots."""

    async def get_stats_for_all_gifts(
        self, session: AsyncSession
    ) -> list[GiftMarketStats]:
        """
        Compute GiftMarketStats for every gift in the catalog.
        Returns results sorted by liquidity_score descending.
        """
        now = datetime.utcnow()
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)

        # ── 1. Gift catalog ────────────────────────────────────────────────
        gifts_result = await session.execute(
            select(GiftCatalog.slug, GiftCatalog.name)
        )
        gifts: dict[str, str] = {row.slug: row.name for row in gifts_result}

        if not gifts:
            return []

        # ── 2. Active listing aggregates per gift ──────────────────────────
        active_result = await session.execute(
            select(
                GiftListing.gift_slug,
                func.count().label("cnt"),
                func.min(GiftListing.price_ton).label("floor_price"),
                func.avg(GiftListing.price_ton).label("avg_price"),
            )
            .where(GiftListing.sold_at.is_(None))
            .group_by(GiftListing.gift_slug)
        )
        listing_stats: dict[str, dict] = {}
        for row in active_result:
            listing_stats[row.gift_slug] = {
                "active_listings": row.cnt,
                "floor_price": row.floor_price,
                "avg_listing_price": row.avg_price,
            }

        # ── 3. Individual sale prices last 7d (needed for median) ──────────
        sales_7d_result = await session.execute(
            select(GiftSale.gift_slug, GiftSale.sale_price_ton)
            .where(GiftSale.detected_at >= cutoff_7d)
        )
        sales_7d_prices: dict[str, list[float]] = {}
        for row in sales_7d_result:
            sales_7d_prices.setdefault(row.gift_slug, []).append(
                float(row.sale_price_ton)
            )

        # ── 4. Sales count last 30d ────────────────────────────────────────
        sales_30d_result = await session.execute(
            select(
                GiftSale.gift_slug,
                func.count().label("cnt"),
            )
            .where(GiftSale.detected_at >= cutoff_30d)
            .group_by(GiftSale.gift_slug)
        )
        sales_30d: dict[str, int] = {}
        for row in sales_30d_result:
            sales_30d[row.gift_slug] = row.cnt

        # ── 5. Last sale timestamp per gift ───────────────────────────────
        last_sale_result = await session.execute(
            select(
                GiftSale.gift_slug,
                func.max(GiftSale.detected_at).label("last_sale_at"),
            )
            .group_by(GiftSale.gift_slug)
        )
        last_sale: dict[str, datetime] = {}
        for row in last_sale_result:
            last_sale[row.gift_slug] = row.last_sale_at

        # ── 6a. Active listings per (slug, tier) — for rarity breakdown ───
        tier_listings_result = await session.execute(
            select(
                GiftListing.gift_slug,
                GiftListing.rarity_tier,
                func.count().label("cnt"),
                func.min(GiftListing.price_ton).label("floor"),
            )
            .where(GiftListing.sold_at.is_(None))
            .group_by(GiftListing.gift_slug, GiftListing.rarity_tier)
        )
        # tier_listing[(slug, tier)] = (count, floor)
        tier_listing: dict[tuple[str, str], tuple[int, Decimal]] = {}
        for row in tier_listings_result:
            tier_listing[(row.gift_slug, row.rarity_tier)] = (row.cnt, row.floor)

        # ── 6b. Sale prices per (slug, tier) last 30d — for median ─────────
        tier_sales_result = await session.execute(
            select(
                GiftSale.gift_slug,
                GiftSale.rarity_tier,
                GiftSale.sale_price_ton,
            )
            .where(GiftSale.detected_at >= cutoff_30d)
        )
        tier_raw_prices: dict[tuple[str, str], list[float]] = {}
        for row in tier_sales_result:
            tier_raw_prices.setdefault(
                (row.gift_slug, row.rarity_tier), []
            ).append(float(row.sale_price_ton))

        # ── 7. Floor price history from market_snapshots (last 7d) ────────
        # Grouped by (slug, scanned_at) to get one floor price per scan pass
        snapshots_result = await session.execute(
            select(
                MarketSnapshot.gift_slug,
                MarketSnapshot.scanned_at,
                func.min(MarketSnapshot.price_amount).label("floor_price"),
            )
            .where(MarketSnapshot.scanned_at >= cutoff_7d)
            .group_by(MarketSnapshot.gift_slug, MarketSnapshot.scanned_at)
            .order_by(MarketSnapshot.gift_slug, MarketSnapshot.scanned_at)
        )
        price_history: dict[str, list[float]] = {}
        for row in snapshots_result:
            price_history.setdefault(row.gift_slug, []).append(
                float(row.floor_price)
            )

        # ── 8. Build per-gift stats ────────────────────────────────────────
        results: list[GiftMarketStats] = []

        for slug, name in gifts.items():
            ld = listing_stats.get(slug, {})
            active = ld.get("active_listings", 0)
            floor = ld.get("floor_price")
            avg_listing = ld.get("avg_listing_price")

            prices_7d = sales_7d_prices.get(slug, [])
            s7d = len(prices_7d)
            s30d = sales_30d.get(slug, 0)

            avg_7d: Optional[Decimal] = (
                Decimal(str(round(statistics.mean(prices_7d), 9)))
                if prices_7d
                else None
            )
            median_7d: Optional[Decimal] = (
                Decimal(str(round(statistics.median(prices_7d), 9)))
                if prices_7d
                else None
            )

            last_at = last_sale.get(slug)
            last_days_ago: Optional[int] = (now - last_at).days if last_at else None

            liquidity = min(s7d / max(active, 1), 1.0)

            trend = _compute_price_trend(price_history.get(slug, []))

            doi: Optional[float] = (
                active / (s7d / 7) if s7d > 0 else None
            )

            # ── Rarity breakdown ──────────────────────────────────────────
            common_floor: Optional[Decimal] = (
                tier_listing.get((slug, "common"), (0, None))[1]
            )
            rarity_breakdown: dict[str, RarityTierStats] = {}
            for tier in ("ultra_rare", "rare", "uncommon", "common"):
                t_info = tier_listing.get((slug, tier))
                t_prices = tier_raw_prices.get((slug, tier), [])
                t_count = t_info[0] if t_info else 0
                t_floor = t_info[1] if t_info else None
                t_sales = len(t_prices)
                t_median: Optional[Decimal] = (
                    Decimal(str(round(statistics.median(t_prices), 9)))
                    if t_prices
                    else None
                )
                premium: Optional[float] = (
                    float(t_floor / common_floor)
                    if t_floor and common_floor and common_floor > 0
                    else None
                )
                rarity_breakdown[tier] = RarityTierStats(
                    tier=tier,
                    active_listings=t_count,
                    floor_price=t_floor,
                    median_sale_price_30d=t_median,
                    sales_30d=t_sales,
                    premium_vs_common=premium,
                )

            results.append(
                GiftMarketStats(
                    slug=slug,
                    name=name,
                    active_listings=active,
                    floor_price=floor,
                    avg_listing_price=avg_listing,
                    sales_7d=s7d,
                    sales_30d=s30d,
                    avg_sale_price_7d=avg_7d,
                    median_sale_price_7d=median_7d,
                    last_sale_days_ago=last_days_ago,
                    liquidity_score=liquidity,
                    price_trend_7d=trend,
                    days_of_inventory=doi,
                    rarity_breakdown=rarity_breakdown,
                )
            )

        results.sort(key=lambda x: x.liquidity_score, reverse=True)
        return results


def _compute_price_trend(floor_prices: list[float]) -> str:
    """
    Compare median of oldest 3 scan floor prices vs newest 3.

    Returns "up", "down", "stable", or "unknown" (< 6 data points).
    Thresholds: > 5% change → up/down, otherwise stable.
    """
    if len(floor_prices) < 6:
        return "unknown"

    old_median = statistics.median(floor_prices[:3])
    new_median = statistics.median(floor_prices[-3:])

    if old_median == 0:
        return "unknown"

    change_pct = (new_median - old_median) / old_median * 100

    if change_pct > 5:
        return "up"
    if change_pct < -5:
        return "down"
    return "stable"


# Singleton
market_stats_service = MarketStatsService()
