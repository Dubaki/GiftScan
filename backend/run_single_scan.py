"""Run a single scan cycle to collect fresh prices."""

import asyncio
import logging
from app.core.database import async_session
from app.services.scanner import GiftScanner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Execute one scan cycle."""
    logger.info("Starting single scan cycle...")

    scanner = GiftScanner()

    async with async_session() as session:
        result = await scanner.run_full_scan(session)

    logger.info("\n" + "="*60)
    logger.info("SCAN COMPLETE")
    logger.info("="*60)
    logger.info(f"Total gifts scanned: {result['total_gifts']}")
    logger.info(f"Snapshots saved: {result['saved']}")
    logger.info(f"Duration: {result['duration_sec']}s")
    logger.info("\nPrices by source:")
    for source, count in result['sources'].items():
        logger.info(f"  - {source}: {count} prices")


if __name__ == "__main__":
    asyncio.run(main())
