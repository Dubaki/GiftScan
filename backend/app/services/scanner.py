"""
Scanner service — fetches prices from all sources and writes market_snapshots.
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gift import GiftCatalog
from app.models.snapshot import MarketSnapshot
from app.services.parsers.fragment import fetch_gift_price

logger = logging.getLogger(__name__)


async def scan_all_gifts(session: AsyncSession) -> int:
    """
    Scan prices for every gift in the catalog.
    Returns the number of snapshots saved.
    """
    result = await session.execute(select(GiftCatalog.slug))
    slugs = result.scalars().all()

    if not slugs:
        logger.warning("gifts_catalog is empty — nothing to scan")
        return 0

    saved = 0
    for slug in slugs:
        price = await fetch_gift_price(slug)
        if price is None:
            continue

        snapshot = MarketSnapshot(
            gift_slug=slug,
            source="Fragment",
            price_amount=price,
            currency="TON",
            scanned_at=datetime.utcnow(),
        )
        session.add(snapshot)
        saved += 1

    if saved:
        await session.commit()

    logger.info("Scan complete: %d/%d snapshots saved", saved, len(slugs))
    return saved
