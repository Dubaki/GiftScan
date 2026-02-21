"""
Market digest service — sends periodic market summaries to Telegram.

Each digest contains four sections:
  1. Top collections by liquidity (sales_7d / active_listings)
  2. Rarity premium table — floor price per tier per collection
  3. Rare-at-floor listings right now (discount ≥ 15%)
  4. Rare NFT sales in the last 24 hours

Default interval: 6 hours. The ContinuousScanner calls send_if_due() after
every scan; if enough time has elapsed, the digest is built and sent.
"""

import logging
import statistics
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gift import GiftCatalog
from app.models.listing import GiftListing
from app.models.sale import GiftSale
from app.services.rare_detector import (
    DEFAULT_PREMIUM,
    MIN_SALES_FOR_CONFIDENCE,
    TIER_ICON,
)
from app.services.telegram_notifier import telegram_notifier

logger = logging.getLogger(__name__)

# Minimum discount to list a rare NFT in the digest's "rare at floor" section
DIGEST_MIN_DISCOUNT = 0.15

# Number of top collections to include
TOP_N = 8


def _liquidity_bar(score: float, width: int = 5) -> str:
    """ASCII progress bar for liquidity score (0.0–1.0)."""
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


class MarketDigestService:
    """Builds and sends periodic market digests to Telegram."""

    def __init__(self, digest_interval_hours: int = 6) -> None:
        self.digest_interval_hours = digest_interval_hours
        self._last_digest_at: Optional[datetime] = None

    # ------------------------------------------------------------------

    def should_send(self) -> bool:
        if self._last_digest_at is None:
            return True
        elapsed = (datetime.utcnow() - self._last_digest_at).total_seconds()
        return elapsed >= self.digest_interval_hours * 3600

    async def send_if_due(self, session: AsyncSession) -> bool:
        """Send digest if the interval has elapsed. Returns True if sent."""
        if not self.should_send():
            return False
        await self.send_digest(session)
        return True

    async def send_digest(self, session: AsyncSession) -> None:
        """Build and push the full market digest to Telegram."""
        self._last_digest_at = datetime.utcnow()
        try:
            message = await self._build(session)
            await telegram_notifier.send_raw_message(message)
            logger.info("Market digest sent (%d chars)", len(message))
        except Exception as e:
            logger.error("Market digest failed: %s", e)

    # ------------------------------------------------------------------
    # Internal builders
    # ------------------------------------------------------------------

    async def _build(self, session: AsyncSession) -> str:
        now = datetime.utcnow()
        cutoff_7d  = now - timedelta(days=7)
        cutoff_24h = now - timedelta(hours=24)
        cutoff_30d = now - timedelta(days=30)
        timestamp = now.strftime("%d %b %Y, %H:%M UTC")

        # ── Gift names ─────────────────────────────────────────────────────
        names_result = await session.execute(
            select(GiftCatalog.slug, GiftCatalog.name)
        )
        gift_names: dict[str, str] = {row.slug: row.name for row in names_result}

        # ── Active listings: count + floor per (slug, tier) ────────────────
        listings_result = await session.execute(
            select(
                GiftListing.gift_slug,
                GiftListing.rarity_tier,
                func.count().label("cnt"),
                func.min(GiftListing.price_ton).label("floor"),
            )
            .where(GiftListing.sold_at.is_(None))
            .group_by(GiftListing.gift_slug, GiftListing.rarity_tier)
        )
        # tier_data[(slug, tier)] = (count, floor_price)
        tier_data: dict[tuple[str, str], tuple[int, Decimal]] = {}
        slug_active: dict[str, int] = {}
        for row in listings_result:
            tier_data[(row.gift_slug, row.rarity_tier)] = (row.cnt, row.floor)
            slug_active[row.gift_slug] = slug_active.get(row.gift_slug, 0) + row.cnt

        # ── Sales last 7d per slug ─────────────────────────────────────────
        sales_7d_result = await session.execute(
            select(GiftSale.gift_slug, func.count().label("cnt"))
            .where(GiftSale.detected_at >= cutoff_7d)
            .group_by(GiftSale.gift_slug)
        )
        sales_7d: dict[str, int] = {
            row.gift_slug: row.cnt for row in sales_7d_result
        }

        def _liquidity(slug: str) -> float:
            s = sales_7d.get(slug, 0)
            a = slug_active.get(slug, 0)
            return min(s / max(a, 1), 1.0)

        # ── Top slugs by liquidity ─────────────────────────────────────────
        top_slugs = sorted(slug_active.keys(), key=_liquidity, reverse=True)[:TOP_N]

        # ── Section 1: Top collections ─────────────────────────────────────
        medals = ["🥇", "🥈", "🥉"] + ["  "] * 10
        top_lines: list[str] = []
        for i, slug in enumerate(top_slugs):
            name = gift_names.get(slug, slug)
            common = tier_data.get((slug, "common"))
            floor_str = f"{common[1]:.0f} TON" if common else "—"
            s7d    = sales_7d.get(slug, 0)
            active = slug_active.get(slug, 0)
            liq    = _liquidity(slug)
            bar    = _liquidity_bar(liq)
            top_lines.append(
                f"{medals[i]} <b>{name}</b>\n"
                f"   floor {floor_str} | {s7d} продаж/7д"
                f" | {active} листингов | {bar}"
            )

        section_top = "<b>━━━ ТОП КОЛЛЕКЦИЙ ━━━</b>\n" + "\n".join(top_lines)

        # ── Section 2: Rarity premium table ───────────────────────────────
        prem_lines: list[str] = []
        for slug in top_slugs:
            name = gift_names.get(slug, slug)[:14].ljust(14)
            common_floor: Optional[Decimal] = None
            cells: list[str] = []
            for tier in ("common", "rare", "ultra_rare"):
                info = tier_data.get((slug, tier))
                cell = f"{info[1]:.0f} TON" if info else "—"
                cells.append(cell.ljust(9))
                if tier == "common" and info:
                    common_floor = info[1]

            ratio_parts: list[str] = []
            for tier in ("rare", "ultra_rare"):
                info = tier_data.get((slug, tier))
                if info and common_floor and common_floor > 0:
                    ratio_parts.append(f"{float(info[1] / common_floor):.1f}×")

            ratio = f"({' / '.join(ratio_parts)})" if ratio_parts else ""
            prem_lines.append(f"{name} {'  '.join(cells)} {ratio}")

        section_premium = (
            "<b>━━━ ПРЕМИИ ЗА РЕДКОСТЬ ━━━</b>\n"
            "<code>Коллекция       common    rare      ultra_rare</code>\n"
            + "\n".join(f"<code>{l}</code>" for l in prem_lines)
        )

        # ── Section 3: Rare-at-floor right now ────────────────────────────
        # Sales medians for expected-price calc
        raw_sales: dict[tuple[str, str], list[float]] = {}
        sales_30d_rows = await session.execute(
            select(GiftSale.gift_slug, GiftSale.rarity_tier, GiftSale.sale_price_ton)
            .where(GiftSale.detected_at >= cutoff_30d)
            .where(GiftSale.rarity_tier.in_(["ultra_rare", "rare"]))
        )
        for row in sales_30d_rows:
            raw_sales.setdefault((row.gift_slug, row.rarity_tier), []).append(
                float(row.sale_price_ton)
            )
        median_sale: dict[tuple[str, str], tuple[int, Decimal]] = {
            k: (len(v), Decimal(str(statistics.median(v))))
            for k, v in raw_sales.items()
        }

        rare_rows = await session.execute(
            select(GiftListing)
            .where(GiftListing.sold_at.is_(None))
            .where(GiftListing.rarity_tier.in_(["ultra_rare", "rare"]))
            .where(GiftListing.gift_slug.in_(top_slugs))
        )
        at_floor: list[tuple[float, str]] = []
        for listing in rare_rows.scalars():
            slug = listing.gift_slug
            tier = listing.rarity_tier
            common = tier_data.get((slug, "common"))
            if not common or common[1] <= 0:
                continue
            common_floor = common[1]

            sale_info = median_sale.get((slug, tier))
            if sale_info and sale_info[0] >= MIN_SALES_FOR_CONFIDENCE:
                expected = sale_info[1]
            else:
                expected = common_floor * DEFAULT_PREMIUM[tier]

            if expected <= listing.price_ton:
                continue

            discount = float((expected - listing.price_ton) / expected)
            if discount < DIGEST_MIN_DISCOUNT:
                continue

            icon   = TIER_ICON.get(tier, "⭐")
            serial = f" #{listing.serial_number}" if listing.serial_number else ""
            line = (
                f"{icon} <b>{gift_names.get(slug, slug)}{serial}</b>"
                f" — {listing.price_ton:.1f} TON"
                f" (ожид: {expected:.0f} TON, −{int(discount * 100)}%)"
                f" @ {listing.marketplace}"
            )
            at_floor.append((discount, line))

        at_floor.sort(key=lambda x: x[0], reverse=True)
        at_floor_lines = [l for _, l in at_floor[:10]]

        section_rare = (
            "<b>━━━ RARE У ФЛОРА ПРЯМО СЕЙЧАС ━━━</b>\n"
            + ("\n".join(at_floor_lines) if at_floor_lines else "Нет подходящих листингов")
        )

        # ── Section 4: Recent rare sales (24 h) ───────────────────────────
        recent_rows = await session.execute(
            select(GiftSale)
            .where(GiftSale.detected_at >= cutoff_24h)
            .where(GiftSale.rarity_tier.in_(["ultra_rare", "rare"]))
            .order_by(GiftSale.detected_at.desc())
            .limit(10)
        )
        sale_lines: list[str] = []
        for sale in recent_rows.scalars():
            icon   = TIER_ICON.get(sale.rarity_tier, "⭐")
            serial = f" #{sale.serial_number}" if sale.serial_number else ""
            hours_ago = int((now - sale.detected_at).total_seconds() / 3600)
            time_str  = f"{hours_ago}ч назад" if hours_ago > 0 else "только что"
            tier_label = sale.rarity_tier.replace("_", " ")
            sale_lines.append(
                f"{icon} {gift_names.get(sale.gift_slug, sale.gift_slug)}{serial}"
                f" → <b>{sale.sale_price_ton:.1f} TON</b>"
                f" ({tier_label}) · {time_str}"
            )

        section_sales = (
            "<b>━━━ ПРОДАЖИ RARE ЗА 24Ч ━━━</b>\n"
            + ("\n".join(sale_lines) if sale_lines else "Нет данных")
        )

        # ── Assemble ───────────────────────────────────────────────────────
        parts = [
            f"<b>📊 GIFTSCAN MARKET DIGEST</b>  |  {timestamp}",
            "",
            section_top,
            "",
            section_premium,
            "",
            section_rare,
            "",
            section_sales,
            "",
            f"<i>Следующий дайджест через {self.digest_interval_hours}ч</i>",
        ]
        return "\n".join(parts)


# Singleton — 6-hour interval
market_digest = MarketDigestService(digest_interval_hours=6)
