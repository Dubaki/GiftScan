"""
Background task that periodically scans gift prices.
Runs inside the FastAPI lifespan as an asyncio task.
"""

import asyncio
import logging

from app.core.config import settings
from app.core.database import async_session
from app.services.scanner import scan_all_gifts

logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 10 * 60  # 10 minutes


async def price_update_loop() -> None:
    """Run scan_all_gifts in an infinite loop with SCAN_INTERVAL_SECONDS pause."""
    logger.info(
        "Price updater started (interval=%ds)", SCAN_INTERVAL_SECONDS
    )
    while True:
        try:
            async with async_session() as session:
                count = await scan_all_gifts(session)
                logger.info("Price update tick: %d snapshots", count)
        except asyncio.CancelledError:
            logger.info("Price updater cancelled")
            return
        except Exception:
            logger.exception("Price updater error")

        await asyncio.sleep(SCAN_INTERVAL_SECONDS)
