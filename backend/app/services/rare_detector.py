"""
Rare-at-floor detector — finds rare NFTs listed at/near common-tier prices.

The core insight: a rare/ultra_rare NFT listed at or close to the collection's
common-tier floor price is severely underpriced. Every scan we compare each
rare listing against its expected price (derived from sales history or a default
rarity multiplier) and fire an immediate Telegram alert if the discount exceeds
MIN_DISCOUNT_PCT.

Detection flow per scan:
  1. Find cheapest common-tier listing per collection (common_floor).
  2. For each rare/ultra_rare active listing:
       expected = median_sale_price_30d  (if ≥ MIN_SALES_FOR_CONFIDENCE sales)
               OR common_floor × DEFAULT_PREMIUM[tier]
       discount = (expected − current_price) / expected
       if discount ≥ MIN_DISCOUNT_PCT → alert
  3. Deduplicate: same nft_address not re-alerted within DEDUP_HOURS.
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
from app.services.telegram_notifier import telegram_notifier

logger = logging.getLogger(__name__)


# ── Constants ──────────────────────────────────────────────────────────────────

# Default rarity premium multipliers applied to common_floor
# before enough sales history accumulates.
DEFAULT_PREMIUM: dict[str, Decimal] = {
    "ultra_rare": Decimal("5.0"),
    "rare":       Decimal("2.5"),
    "uncommon":   Decimal("1.3"),
    "common":     Decimal("1.0"),
}

TIER_ICON: dict[str, str] = {
    "ultra_rare": "💎",
    "rare":       "⭐",
    "uncommon":   "🔷",
    "common":     "⬜",
}

# Trigger an alert when current_price ≤ (1 − MIN_DISCOUNT_PCT) × expected
MIN_DISCOUNT_PCT = 0.30          # 30% below expected

# Minimum number of historical sales required to trust the median over defaults
MIN_SALES_FOR_CONFIDENCE = 3

# Don't re-alert the same NFT within this window
DEDUP_HOURS = 4


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class RareFloorAlert:
    nft_address: str
    gift_slug: str
    gift_name: str
    serial_number: Optional[int]
    rarity_tier: str
    marketplace: str
    current_price: Decimal
    common_floor: Decimal
    expected_price: Decimal
    discount_pct: float      # 0.0–1.0
    sales_count: int         # number of sales used for expected_price


# ── Detector ───────────────────────────────────────────────────────────────────

class RareFloorDetector:
    """
    Per-scan detector of rare NFTs priced well below their expected value.
    Sends immediate Telegram alerts with deduplication.
    """

    def __init__(self) -> None:
        # nft_address → timestamp of last alert (in-memory dedup)
        self._alerted: dict[str, datetime] = {}

    # ------------------------------------------------------------------

    async def check_and_alert(self, session: AsyncSession) -> list[RareFloorAlert]:
        """
        Scan gift_listings for rare/ultra_rare NFTs below expected price.

        Returns alerts fired this call (may be empty).
        """
        now = datetime.utcnow()
        cutoff_30d = now - timedelta(days=30)

        # ── 1. Common-tier floor price per gift ────────────────────────────
        floor_result = await session.execute(
            select(
                GiftListing.gift_slug,
                func.min(GiftListing.price_ton).label("floor"),
            )
            .where(GiftListing.sold_at.is_(None))
            .where(GiftListing.rarity_tier == "common")
            .group_by(GiftListing.gift_slug)
        )
        common_floors: dict[str, Decimal] = {
            row.gift_slug: row.floor for row in floor_result
        }

        if not common_floors:
            logger.debug("RareFloorDetector: no common-tier listings yet, skipping")
            return []

        # ── 2. Historical sale prices per (slug, tier) — last 30d ──────────
        sales_rows = await session.execute(
            select(
                GiftSale.gift_slug,
                GiftSale.rarity_tier,
                GiftSale.sale_price_ton,
            )
            .where(GiftSale.detected_at >= cutoff_30d)
            .where(GiftSale.rarity_tier.in_(["ultra_rare", "rare"]))
        )
        raw_prices: dict[tuple[str, str], list[float]] = {}
        for row in sales_rows:
            raw_prices.setdefault((row.gift_slug, row.rarity_tier), []).append(
                float(row.sale_price_ton)
            )

        # (slug, tier) → (count, median_price)
        median_sale: dict[tuple[str, str], tuple[int, Decimal]] = {
            k: (len(v), Decimal(str(statistics.median(v))))
            for k, v in raw_prices.items()
        }

        # ── 3. Gift names ──────────────────────────────────────────────────
        names_result = await session.execute(select(GiftCatalog.slug, GiftCatalog.name))
        gift_names: dict[str, str] = {row.slug: row.name for row in names_result}

        # ── 4. Scan active rare / ultra_rare listings ──────────────────────
        rare_result = await session.execute(
            select(GiftListing)
            .where(GiftListing.sold_at.is_(None))
            .where(GiftListing.rarity_tier.in_(["ultra_rare", "rare"]))
        )
        rare_listings = list(rare_result.scalars())

        alerts: list[RareFloorAlert] = []

        for listing in rare_listings:
            slug = listing.gift_slug
            tier = listing.rarity_tier

            common_floor = common_floors.get(slug)
            if not common_floor or common_floor <= 0:
                continue

            # Choose expected price source
            sale_info = median_sale.get((slug, tier))
            if sale_info and sale_info[0] >= MIN_SALES_FOR_CONFIDENCE:
                expected = sale_info[1]
                sales_count = sale_info[0]
            else:
                expected = common_floor * DEFAULT_PREMIUM[tier]
                sales_count = sale_info[0] if sale_info else 0

            if expected <= listing.price_ton:
                continue  # not underpriced

            discount = float((expected - listing.price_ton) / expected)
            if discount < MIN_DISCOUNT_PCT:
                continue

            # Deduplication
            last = self._alerted.get(listing.nft_address)
            if last and (now - last).total_seconds() < DEDUP_HOURS * 3600:
                continue

            alerts.append(
                RareFloorAlert(
                    nft_address=listing.nft_address,
                    gift_slug=slug,
                    gift_name=gift_names.get(slug, slug),
                    serial_number=listing.serial_number,
                    rarity_tier=tier,
                    marketplace=listing.marketplace,
                    current_price=listing.price_ton,
                    common_floor=common_floor,
                    expected_price=expected,
                    discount_pct=discount,
                    sales_count=sales_count,
                )
            )
            self._alerted[listing.nft_address] = now

        if not alerts:
            logger.debug("RareFloorDetector: no rare-at-floor opportunities this scan")
            return []

        alerts.sort(key=lambda a: a.discount_pct, reverse=True)
        await self._send_alerts(alerts)
        logger.info("RareFloorDetector: %d rare-at-floor alerts sent", len(alerts))
        return alerts

    # ------------------------------------------------------------------

    async def _send_alerts(self, alerts: list[RareFloorAlert]) -> None:
        """Format and push alerts to Telegram."""
        lines = [f"<b>🔥 RARE AT FLOOR — {len(alerts)} найдено</b>"]

        for alert in alerts:
            icon = TIER_ICON.get(alert.rarity_tier, "⭐")
            serial = f" #{alert.serial_number}" if alert.serial_number else ""
            discount_pct = int(alert.discount_pct * 100)

            line = (
                f"\n{icon} <b>{alert.gift_name}{serial}</b>\n"
                f"   Цена:      <b>{alert.current_price:.1f} TON</b>"
                f" @ {alert.marketplace}\n"
                f"   Ожидаемая: <b>{alert.expected_price:.1f} TON</b>"
                f"  (floor: {alert.common_floor:.1f} TON)\n"
                f"   Скидка:    <b>−{discount_pct}%</b>"
            )

            if alert.sales_count >= MIN_SALES_FOR_CONFIDENCE:
                line += f" · данные {alert.sales_count} продаж"
            else:
                line += " · оценка по умолч. мультипликатору"

            lines.append(line)

        lines.append(f"\n<i>GiftScan Rare Detector</i>")

        try:
            await telegram_notifier.send_raw_message("\n".join(lines))
        except Exception as e:
            logger.error("RareFloorDetector: Telegram send failed: %s", e)


# Singleton
rare_floor_detector = RareFloorDetector()
