"""
Scanner service — fetches prices from all registered parsers and writes market_snapshots.

Supports:
- Multiple parsers via PARSER_REGISTRY
- Bulk parsers (single call for all prices)
- Parallel fetching with per-source and global semaphores
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gift import GiftCatalog
from app.models.snapshot import MarketSnapshot
from app.services.parsers import PARSER_REGISTRY
from app.services.parsers.base import BaseParser, GiftPrice
from app.services.parsers.tonapi_marketplace_parsers import get_tonapi_listings
from app.services.notifications import arbitrage_notifier
from app.services.sales_tracker import sales_tracker, _get_rarity_tier

logger = logging.getLogger(__name__)

# Concurrency settings
GLOBAL_CONCURRENCY = 50  # Max total concurrent requests
PER_SOURCE_CONCURRENCY = {
    "Fragment": 3,  # Be gentle with HTML scraping
    "GetGems": 5,
    "Tonnel": 5,
    "MRKT": 5,
    "Portals": 5,
}

# If sell_price > buy_price × SUSPICIOUS_MULTIPLIER and there are no recent
# sales confirming the price, skip the alert to avoid false positives.
SUSPICIOUS_PRICE_MULTIPLIER = Decimal("2.0")

# Minimum confidence from SalesTracker to trust the fair value estimate.
MIN_CONFIDENCE_FOR_FAIR_VALUE = 0.2


class GiftScanner:
    """Orchestrates price scanning across all registered parsers."""

    def __init__(self):
        self.parsers = PARSER_REGISTRY
        self._global_sem = asyncio.Semaphore(GLOBAL_CONCURRENCY)
        self._source_sems: dict[str, asyncio.Semaphore] = {
            p.source_name: asyncio.Semaphore(
                PER_SOURCE_CONCURRENCY.get(p.source_name, 5)
            )
            for p in self.parsers
        }

    async def run_full_scan(self, session: AsyncSession) -> dict:
        """
        Execute a complete scan across all parsers for all gifts.
        Returns scan statistics.
        """
        scan_start = datetime.utcnow()

        # Get all gift slugs
        result = await session.execute(select(GiftCatalog.slug))
        slugs = list(result.scalars().all())

        if not slugs:
            logger.warning("gifts_catalog is empty — nothing to scan")
            return {"saved": 0, "total_gifts": 0, "duration_sec": 0}

        # Separate bulk vs individual parsers
        bulk_parsers = [p for p in self.parsers if p.supports_bulk]
        individual_parsers = [p for p in self.parsers if not p.supports_bulk]

        # Phase 1: Bulk fetches (one call per parser)
        bulk_results: dict[str, dict[str, GiftPrice]] = {}
        for parser in bulk_parsers:
            try:
                prices = await parser.fetch_all_prices()
                bulk_results[parser.source_name] = prices
                logger.info(
                    "%s bulk fetch: %d prices", parser.source_name, len(prices)
                )
            except Exception as e:
                logger.error("%s bulk fetch failed: %s", parser.source_name, e)
                bulk_results[parser.source_name] = {}

        # Phase 2: Individual fetches with parallelization
        individual_results: dict[str, dict[str, Optional[GiftPrice]]] = {
            p.source_name: {} for p in individual_parsers
        }

        # Create tasks for all (parser, slug) combinations
        tasks = []
        task_info = []  # Track (parser_name, slug) for each task
        for parser in individual_parsers:
            for slug in slugs:
                tasks.append(self._fetch_single(parser, slug))
                task_info.append((parser.source_name, slug))

        # Execute all in parallel (semaphores limit concurrency)
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for (source_name, slug), result in zip(task_info, results):
                if isinstance(result, Exception):
                    logger.debug("%s/%s failed: %s", source_name, slug, result)
                    individual_results[source_name][slug] = None
                else:
                    individual_results[source_name][slug] = result

        # Phase 3: Persist snapshots
        saved = 0
        scanned_at = datetime.utcnow()

        # Save bulk results (skip zero/negative prices — invalid data)
        for source_name, prices in bulk_results.items():
            for slug, gp in prices.items():
                if slug in slugs and gp.price > 0:
                    session.add(
                        MarketSnapshot(
                            gift_slug=slug,
                            source=source_name,
                            price_amount=gp.price,
                            currency=gp.currency,
                            scanned_at=scanned_at,
                            nft_address=gp.nft_address,
                            serial_number=gp.serial,
                            attributes=gp.attributes,
                        )
                    )
                    saved += 1

        # Save individual results (skip zero/negative prices)
        for source_name, slug_prices in individual_results.items():
            for slug, gp in slug_prices.items():
                if gp is not None and gp.price > 0:
                    session.add(
                        MarketSnapshot(
                            gift_slug=slug,
                            source=source_name,
                            price_amount=gp.price,
                            currency=gp.currency,
                            scanned_at=scanned_at,
                            nft_address=gp.nft_address,
                            serial_number=gp.serial,
                            attributes=gp.attributes,
                        )
                    )
                    saved += 1

        if saved:
            await session.commit()

        duration = (datetime.utcnow() - scan_start).total_seconds()
        logger.info(
            "Scan complete: %d snapshots from %d parsers in %.1fs",
            saved,
            len(self.parsers),
            duration,
        )

        # Sync full listings table — detects sold NFTs and maintains inventory
        try:
            all_listings = await get_tonapi_listings()  # returns from cache, no extra API call
            new_sales = await sales_tracker.sync_all_listings(session, all_listings)
            if new_sales:
                logger.info("Detected %d new sales this scan", new_sales)
        except Exception as e:
            logger.error("Listings sync / sales detection failed: %s", e)

        # Detect rare NFTs priced at/near common-tier floor — instant alert
        try:
            from app.services.rare_detector import rare_floor_detector
            rare_alerts = await rare_floor_detector.check_and_alert(session)
            if rare_alerts:
                logger.info("Rare-at-floor: %d alerts fired", len(rare_alerts))
        except Exception as e:
            logger.error("Rare floor detection failed: %s", e)

        # Check for arbitrage / undervalued opportunities
        await self._check_arbitrage_opportunities(session, slugs)

        # Collect stats per source
        source_stats = {}
        for parser in self.parsers:
            name = parser.source_name
            if parser.supports_bulk:
                source_stats[name] = len(bulk_results.get(name, {}))
            else:
                source_stats[name] = sum(
                    1 for v in individual_results.get(name, {}).values() if v
                )

        return {
            "saved": saved,
            "total_gifts": len(slugs),
            "duration_sec": round(duration, 1),
            "sources": source_stats,
        }

    async def _fetch_single(
        self, parser: BaseParser, slug: str
    ) -> Optional[GiftPrice]:
        """Fetch a single price with concurrency control."""
        source_sem = self._source_sems.get(
            parser.source_name, asyncio.Semaphore(5)
        )
        async with self._global_sem:
            async with source_sem:
                try:
                    return await parser.fetch_gift_price(slug)
                except Exception as e:
                    logger.debug(
                        "%s/%s error: %s", parser.source_name, slug, e
                    )
                    return None

    async def _check_arbitrage_opportunities(
        self, session: AsyncSession, slugs: list[str]
    ):
        """
        Check for arbitrage / undervalued opportunities and send Telegram alerts.

        Logic per (gift_slug, rarity_tier) group:

        1. Find cheapest current listing (buy_price).
        2. Get FairValue from SalesTracker (median of recent actual sales).
        3. Determine realistic sell target:
           a. If FairValue exists with confidence ≥ MIN_CONFIDENCE:
              - Use median sale price as sell target.
              - If buy_price < fair_value × 0.7  → UNDERVALUED ALERT.
              - If sell_target > buy_price + min_profit → ARBITRAGE ALERT.
           b. If no FairValue (cold start):
              - Use highest current listing as sell target BUT only if
                the spread is "reasonable" (< SUSPICIOUS_MULTIPLIER × buy_price).
              - Large spreads without sales data are skipped.
        """
        # Get gift names for notifications
        gift_names_stmt = select(GiftCatalog.slug, GiftCatalog.name)
        result = await session.execute(gift_names_stmt)
        gift_names = {row.slug: row.name for row in result.all()}

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

        # Get latest snapshots for all gifts
        snapshots_stmt = (
            select(
                MarketSnapshot.gift_slug,
                MarketSnapshot.source,
                MarketSnapshot.price_amount,
                MarketSnapshot.currency,
                MarketSnapshot.serial_number,
                MarketSnapshot.attributes,
            )
            .join(
                latest_sq,
                and_(
                    MarketSnapshot.gift_slug == latest_sq.c.gift_slug,
                    MarketSnapshot.source == latest_sq.c.source,
                    MarketSnapshot.scanned_at == latest_sq.c.max_at,
                ),
            )
            .where(MarketSnapshot.gift_slug.in_(slugs))
        )

        result = await session.execute(snapshots_stmt)

        # Group by (slug, rarity_tier) — never compare items of different rarity
        gift_prices_by_tier: dict[
            tuple[str, str],
            list[tuple[str, Decimal, Optional[int], Optional[dict]]],
        ] = {}

        for row in result.all():
            serial = getattr(row, "serial_number", None)
            attributes = getattr(row, "attributes", None)
            tier = _get_rarity_tier(serial, attributes)
            key = (row.gift_slug, tier)

            if key not in gift_prices_by_tier:
                gift_prices_by_tier[key] = []

            gift_prices_by_tier[key].append(
                (row.source, row.price_amount, serial, attributes)
            )

        deals_found = 0

        for (slug, tier), prices in gift_prices_by_tier.items():
            if len(prices) < 1:
                continue

            sorted_prices = sorted(prices, key=lambda x: x[1])
            buy_source, buy_price, buy_serial, buy_attributes = sorted_prices[0]
            _, highest_listing, _, _ = sorted_prices[-1]

            if buy_price <= 0:
                continue

            # Look up actual sales data for this gift/tier
            fair_value = await sales_tracker.get_fair_value(
                session, slug, tier
            )

            all_prices_for_slug = {
                source: price for source, price, _, _ in prices
            }

            if fair_value and fair_value.confidence >= MIN_CONFIDENCE_FOR_FAIR_VALUE:
                # ── Path A: we have reliable sales history ────────────────
                sell_target = fair_value.median_price

                # Case A1: undervalued floor — buy_price well below fair value
                if buy_price <= sell_target * Decimal("0.7"):
                    spread_ton = sell_target - buy_price
                    if spread_ton >= arbitrage_notifier.min_spread_ton:
                        arbitrage_notifier.collect_opportunity(
                            slug=slug,
                            name=gift_names.get(slug, slug),
                            buy_source=buy_source,
                            buy_price=buy_price,
                            sell_source="market (avg)",
                            sell_price=sell_target,
                            spread_ton=spread_ton,
                            serial_number=buy_serial,
                            attributes=buy_attributes,
                            all_prices=all_prices_for_slug,
                            fair_value=fair_value,
                            alert_type="undervalued",
                        )
                        deals_found += 1
                        logger.info(
                            "Undervalued [%s/%s]: buy %.1f TON, fair value %.1f TON "
                            "(%d sales, confidence %.2f)",
                            gift_names.get(slug, slug),
                            tier,
                            buy_price,
                            sell_target,
                            fair_value.sales_count,
                            fair_value.confidence,
                        )
                    continue  # don't double-alert same gift

                # Case A2: cross-marketplace arbitrage validated by sales
                if len(prices) >= 2:
                    sell_source, sell_listing, _, _ = sorted_prices[-1]
                    if sell_source == buy_source:
                        continue

                    # Cap sell target at fair value + 10% (don't trust stale listings)
                    realistic_sell = min(
                        sell_listing, sell_target * Decimal("1.1")
                    )
                    spread_ton = realistic_sell - buy_price

                    if spread_ton >= arbitrage_notifier.min_spread_ton:
                        arbitrage_notifier.collect_opportunity(
                            slug=slug,
                            name=gift_names.get(slug, slug),
                            buy_source=buy_source,
                            buy_price=buy_price,
                            sell_source=sell_source,
                            sell_price=realistic_sell,
                            spread_ton=spread_ton,
                            serial_number=buy_serial,
                            attributes=buy_attributes,
                            all_prices=all_prices_for_slug,
                            fair_value=fair_value,
                            alert_type="arbitrage",
                        )
                        deals_found += 1
                        logger.info(
                            "Arbitrage [%s/%s]: buy %.1f @ %s → sell %.1f "
                            "(fair %.1f, %d sales)",
                            gift_names.get(slug, slug),
                            tier,
                            buy_price,
                            buy_source,
                            realistic_sell,
                            sell_target,
                            fair_value.sales_count,
                        )

            else:
                # ── Path B: cold start — no / insufficient sales data ─────
                if len(prices) < 2:
                    continue

                sell_source, sell_price, _, _ = sorted_prices[-1]
                if sell_source == buy_source:
                    continue

                spread_ton = sell_price - buy_price

                # Only alert on conservative (small) spreads without sales data
                price_ratio = sell_price / buy_price
                if price_ratio > SUSPICIOUS_PRICE_MULTIPLIER:
                    logger.debug(
                        "Skipping %s/%s: %.1f × price gap with no sales data "
                        "(buy %.1f, sell %.1f)",
                        slug,
                        tier,
                        float(price_ratio),
                        buy_price,
                        sell_price,
                    )
                    continue

                if spread_ton >= arbitrage_notifier.min_spread_ton:
                    arbitrage_notifier.collect_opportunity(
                        slug=slug,
                        name=gift_names.get(slug, slug),
                        buy_source=buy_source,
                        buy_price=buy_price,
                        sell_source=sell_source,
                        sell_price=sell_price,
                        spread_ton=spread_ton,
                        serial_number=buy_serial,
                        attributes=buy_attributes,
                        all_prices=all_prices_for_slug,
                        fair_value=None,
                        alert_type="arbitrage_unconfirmed",
                    )
                    deals_found += 1
                    logger.info(
                        "Arbitrage [%s/%s] (no sales data): buy %.1f @ %s → sell %.1f @ %s",
                        gift_names.get(slug, slug),
                        tier,
                        buy_price,
                        buy_source,
                        sell_price,
                        sell_source,
                    )

        logger.info(
            "Found %d opportunities (>= %s TON spread)", deals_found, arbitrage_notifier.min_spread_ton
        )

        # Send summary table to Telegram
        await arbitrage_notifier.send_scan_results()


# Backward-compatible function for existing code
async def scan_all_gifts(session: AsyncSession) -> int:
    """
    Scan prices for every gift in the catalog.
    Returns the number of snapshots saved.
    """
    scanner = GiftScanner()
    result = await scanner.run_full_scan(session)
    return result["saved"]
