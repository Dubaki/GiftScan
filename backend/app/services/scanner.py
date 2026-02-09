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
from app.services.notifications import arbitrage_notifier

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

        # Save bulk results
        for source_name, prices in bulk_results.items():
            for slug, gp in prices.items():
                if slug in slugs:  # Only save known gifts
                    session.add(
                        MarketSnapshot(
                            gift_slug=slug,
                            source=source_name,
                            price_amount=gp.price,
                            currency=gp.currency,
                            scanned_at=scanned_at, # Use the already set scanned_at
                        )
                    )
                    saved += 1

        # Save individual results
        for source_name, slug_prices in individual_results.items():
            for slug, gp in slug_prices.items():
                if gp is not None:
                    session.add(
                        MarketSnapshot(
                            gift_slug=slug,
                            source=source_name,
                            price_amount=gp.price,
                            currency=gp.currency,
                            scanned_at=scanned_at,
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

        # Check for arbitrage opportunities and send Telegram notifications
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
        Check for arbitrage opportunities and send Telegram notifications.

        Analyzes latest prices for each gift and alerts when spread > 1.5 TON.
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

        # Group prices by gift
        gift_prices: dict[str, list[tuple[str, Decimal]]] = {slug: [] for slug in slugs}
        for row in result.all():
            gift_prices[row.gift_slug].append((row.source, row.price_amount))

        # Check each gift for arbitrage
        alerts_sent = 0
        for slug, prices in gift_prices.items():
            if len(prices) < 2:
                continue  # Need at least 2 prices to compare

            # Find min and max prices
            sorted_prices = sorted(prices, key=lambda x: x[1])
            buy_source, buy_price = sorted_prices[0]
            sell_source, sell_price = sorted_prices[-1]

            # Skip if buy price is 0 (invalid data)
            if buy_price <= 0:
                logger.debug(f"Skipping {slug}: invalid buy price ({buy_price} TON)")
                continue

            spread_ton = sell_price - buy_price

            # Send alert if spread > threshold (from notifier settings)
            if spread_ton >= arbitrage_notifier.min_spread_ton:
                try:
                    await arbitrage_notifier.alert_opportunity(
                        slug=slug,
                        name=gift_names.get(slug, slug),
                        buy_source=buy_source,
                        buy_price=buy_price,
                        sell_source=sell_source,
                        sell_price=sell_price,
                        spread_ton=spread_ton,
                    )
                    alerts_sent += 1
                except Exception as e:
                    logger.error(f"Failed to send alert for {slug}: {e}")

        if alerts_sent > 0:
            logger.info(f"📱 Sent {alerts_sent} Telegram arbitrage alerts")


# Backward-compatible function for existing code
async def scan_all_gifts(session: AsyncSession) -> int:
    """
    Scan prices for every gift in the catalog.
    Returns the number of snapshots saved.
    """
    scanner = GiftScanner()
    result = await scanner.run_full_scan(session)
    return result["saved"]
