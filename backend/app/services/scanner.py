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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gift import GiftCatalog
from app.models.snapshot import MarketSnapshot
from app.services.parsers import PARSER_REGISTRY
from app.services.parsers.base import BaseParser, GiftPrice

logger = logging.getLogger(__name__)

# Concurrency settings
GLOBAL_CONCURRENCY = 20  # Max total concurrent requests
PER_SOURCE_CONCURRENCY = {
    "Fragment": 3,  # Be gentle with HTML scraping
    "GetGems": 5,
    "Tonnel": 1,  # Bulk API
    "MRKT": 5,
    "Portals": 1,  # Bulk API
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
        scan_start = datetime.now(timezone.utc)

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
        scanned_at = datetime.now(timezone.utc)

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
                            scanned_at=scanned_at,
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

        duration = (datetime.now(timezone.utc) - scan_start).total_seconds()
        logger.info(
            "Scan complete: %d snapshots from %d parsers in %.1fs",
            saved,
            len(self.parsers),
            duration,
        )

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


# Backward-compatible function for existing code
async def scan_all_gifts(session: AsyncSession) -> int:
    """
    Scan prices for every gift in the catalog.
    Returns the number of snapshots saved.
    """
    scanner = GiftScanner()
    result = await scanner.run_full_scan(session)
    return result["saved"]
