"""
Sales Tracker — detects actual NFT sales and calculates fair value.

How sales are detected:
  Each scan saves the nft_address of every listed NFT.
  If an NFT was present in scan N but absent in scan N+1, it was sold
  (or delisted, but we assume sold at last known price).

Fair value:
  Median sale price from the last `lookback_days` days for a given
  (gift_slug, rarity_tier) pair.  Used instead of the highest listing
  price when evaluating arbitrage opportunities.
"""

import logging
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import GiftListing
from app.models.sale import GiftSale
from app.models.snapshot import MarketSnapshot

if TYPE_CHECKING:
    from app.services.parsers.tonapi_enhanced import NFTListing

logger = logging.getLogger(__name__)


@dataclass
class FairValue:
    """Realistic sell price estimate based on historical sales."""

    gift_slug: str
    rarity_tier: str
    median_price: Decimal
    avg_price: Decimal
    sales_count: int        # total sales in lookback window
    recent_count: int       # sales in last 7 days
    last_sale_days_ago: Optional[int]
    confidence: float       # 0.0 – 1.0


class SalesTracker:
    """Tracks gift sales and computes fair value estimates."""

    # ------------------------------------------------------------------
    # Sales detection
    # ------------------------------------------------------------------

    async def detect_and_record_sales(self, session: AsyncSession) -> int:
        """
        Compare the two most recent scan timestamps.
        NFTs present in the earlier scan but absent in the later one
        are recorded as GiftSale entries.

        Returns the number of new sales recorded.
        """
        # Find the two most recent distinct scanned_at timestamps
        times_result = await session.execute(
            select(func.distinct(MarketSnapshot.scanned_at))
            .where(MarketSnapshot.nft_address.isnot(None))
            .order_by(MarketSnapshot.scanned_at.desc())
            .limit(2)
        )
        times = list(times_result.scalars())

        if len(times) < 2:
            logger.debug("SalesTracker: need ≥2 scans to detect sales, skipping")
            return 0

        current_time, prev_time = times[0], times[1]

        # Addresses from current scan (latest)
        current_result = await session.execute(
            select(
                MarketSnapshot.nft_address,
                MarketSnapshot.gift_slug,
                MarketSnapshot.price_amount,
                MarketSnapshot.serial_number,
                MarketSnapshot.source,
                MarketSnapshot.attributes,
            )
            .where(MarketSnapshot.scanned_at == current_time)
            .where(MarketSnapshot.nft_address.isnot(None))
        )
        current_rows = {row.nft_address: row for row in current_result.all()}

        # Addresses from previous scan
        prev_result = await session.execute(
            select(
                MarketSnapshot.nft_address,
                MarketSnapshot.gift_slug,
                MarketSnapshot.price_amount,
                MarketSnapshot.serial_number,
                MarketSnapshot.source,
                MarketSnapshot.attributes,
            )
            .where(MarketSnapshot.scanned_at == prev_time)
            .where(MarketSnapshot.nft_address.isnot(None))
        )
        prev_rows = {row.nft_address: row for row in prev_result.all()}

        # Already-recorded addresses (avoid duplicates on re-runs)
        existing_result = await session.execute(
            select(GiftSale.nft_address)
            .where(GiftSale.detected_at >= prev_time)
        )
        already_recorded = {row for row in existing_result.scalars()}

        # Disappeared NFTs = sold
        disappeared = set(prev_rows.keys()) - set(current_rows.keys())
        new_sales = 0

        for nft_address in disappeared:
            if nft_address in already_recorded:
                continue

            row = prev_rows[nft_address]
            if row.price_amount <= 0:
                continue

            rarity_tier = _get_rarity_tier(row.serial_number, row.attributes)

            session.add(
                GiftSale(
                    gift_slug=row.gift_slug,
                    nft_address=nft_address,
                    serial_number=row.serial_number,
                    rarity_tier=rarity_tier,
                    sale_price_ton=row.price_amount,
                    marketplace=row.source.replace("TonAPI-", ""),
                    detected_at=current_time,
                )
            )
            new_sales += 1

        if new_sales:
            await session.commit()
            logger.info("SalesTracker: recorded %d new sales", new_sales)
        else:
            logger.debug("SalesTracker: no new sales detected")

        return new_sales

    # ------------------------------------------------------------------
    # Full-listings sync (replaces detect_and_record_sales in scanner)
    # ------------------------------------------------------------------

    async def sync_all_listings(
        self,
        session: AsyncSession,
        listings: "list[NFTListing]",
    ) -> int:
        """
        Sync gift_listings table with the current set of active NFT listings.

        Steps:
        1. Load all currently-active rows from gift_listings (sold_at IS NULL).
        2. Diff against the incoming scan.
        3. Disappeared NFTs → set sold_at, create GiftSale.
        4. New NFTs → INSERT into gift_listings.
        5. Existing NFTs → UPDATE last_seen_at and price_ton.

        Returns the number of new sales detected.
        """
        now = datetime.utcnow()

        # Load every active listing from DB
        active_result = await session.execute(
            select(GiftListing).where(GiftListing.sold_at.is_(None))
        )
        active_db: dict[str, GiftListing] = {
            row.nft_address: row for row in active_result.scalars()
        }

        # Build a lookup of inbound addresses (deduplicated; last wins for price)
        inbound: dict[str, "NFTListing"] = {}
        for listing in listings:
            inbound[listing.nft_address] = listing

        # Avoid duplicate sales recorded within the last hour (re-run safety)
        cutoff = now - timedelta(hours=1)
        existing_sales_result = await session.execute(
            select(GiftSale.nft_address).where(GiftSale.detected_at >= cutoff)
        )
        already_sold: set[str] = set(existing_sales_result.scalars())

        new_sales = 0

        # ── Disappeared → sold ────────────────────────────────────────────
        for nft_address, db_row in active_db.items():
            if nft_address in inbound or nft_address in already_sold:
                continue

            if db_row.price_ton <= 0:
                continue

            session.add(
                GiftSale(
                    gift_slug=db_row.gift_slug,
                    nft_address=nft_address,
                    serial_number=db_row.serial_number,
                    rarity_tier=db_row.rarity_tier,
                    sale_price_ton=db_row.price_ton,
                    marketplace=db_row.marketplace,
                    detected_at=now,
                )
            )
            db_row.sold_at = now
            new_sales += 1

        # ── New or updated listings ───────────────────────────────────────
        for nft_address, listing in inbound.items():
            if nft_address in active_db:
                # Update price and last-seen timestamp
                row = active_db[nft_address]
                row.last_seen_at = now
                row.price_ton = listing.price_ton
            else:
                # Could have been sold previously — insert fresh row
                rarity_tier = _get_rarity_tier(
                    listing.serial_number, listing.attributes
                )
                session.add(
                    GiftListing(
                        nft_address=nft_address,
                        gift_slug=listing.gift_slug,
                        serial_number=listing.serial_number,
                        rarity_tier=rarity_tier,
                        price_ton=listing.price_ton,
                        marketplace=listing.marketplace,
                        first_seen_at=now,
                        last_seen_at=now,
                    )
                )

        await session.commit()

        if new_sales:
            logger.info("SalesTracker.sync_all_listings: recorded %d new sales", new_sales)
        else:
            logger.debug(
                "SalesTracker.sync_all_listings: %d active listings synced, no sales",
                len(inbound),
            )

        return new_sales

    # ------------------------------------------------------------------
    # Fair value calculation
    # ------------------------------------------------------------------

    async def get_fair_value(
        self,
        session: AsyncSession,
        gift_slug: str,
        rarity_tier: str,
        lookback_days: int = 30,
    ) -> Optional[FairValue]:
        """
        Calculate fair value for a gift / rarity tier from recent sales.

        Returns None if there are no sales at all in the lookback window.
        """
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        recent_cutoff = datetime.utcnow() - timedelta(days=7)

        result = await session.execute(
            select(GiftSale.sale_price_ton, GiftSale.detected_at)
            .where(GiftSale.gift_slug == gift_slug)
            .where(GiftSale.rarity_tier == rarity_tier)
            .where(GiftSale.detected_at >= cutoff)
            .order_by(GiftSale.detected_at.desc())
        )
        sales = result.all()

        if not sales:
            return None

        prices = [float(row.sale_price_ton) for row in sales]
        median_price = Decimal(str(statistics.median(prices)))
        avg_price = Decimal(str(statistics.mean(prices)))

        recent_count = sum(
            1 for row in sales if row.detected_at >= recent_cutoff
        )

        days_since_last = (datetime.utcnow() - sales[0].detected_at).days

        confidence = _calculate_confidence(
            total_count=len(sales),
            recent_count=recent_count,
            days_since_last=days_since_last,
        )

        return FairValue(
            gift_slug=gift_slug,
            rarity_tier=rarity_tier,
            median_price=median_price,
            avg_price=avg_price,
            sales_count=len(sales),
            recent_count=recent_count,
            last_sale_days_ago=days_since_last,
            confidence=confidence,
        )


# ------------------------------------------------------------------
# Helpers (module-level so scanner.py can also import them)
# ------------------------------------------------------------------

def _get_rarity_tier(serial: Optional[int], attributes: Optional[dict]) -> str:
    """Mirror of GiftScanner._get_rarity_tier (kept in sync)."""
    if not serial:
        return "unknown"

    if serial < 100:
        return "ultra_rare"
    if attributes and attributes.get("Backdrop") == "Black":
        return "ultra_rare"

    if serial < 1000:
        return "rare"

    sn_str = str(serial)
    if sn_str in {"777", "420", "1234", "5555", "6969", "8888"}:
        return "rare"
    if len(set(sn_str)) == 1:
        return "rare"

    if serial < 5000:
        return "uncommon"

    return "common"


def _calculate_confidence(
    total_count: int,
    recent_count: int,
    days_since_last: int,
) -> float:
    """
    Score 0.0–1.0 indicating how reliable the fair value estimate is.

    Rules:
      - 0 total → 0.0
      - Each additional sale adds confidence (caps at 10)
      - Recent sales (< 7 days) boost confidence
      - Stale sales (> 14 days ago) reduce confidence
    """
    if total_count == 0:
        return 0.0

    base = min(total_count / 10.0, 1.0)  # 0.1 per sale, max 1.0

    recency_boost = min(recent_count / 3.0, 0.3)  # up to +0.3

    staleness_penalty = 0.0
    if days_since_last > 14:
        staleness_penalty = min((days_since_last - 14) / 16.0, 0.4)

    score = base + recency_boost - staleness_penalty
    return max(0.0, min(1.0, score))


# Singleton
sales_tracker = SalesTracker()
