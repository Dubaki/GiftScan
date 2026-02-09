"""
Test scanner with automatic Telegram notifications.
Runs ONE scan cycle and sends notifications for arbitrage opportunities.
"""

import asyncio
import logging
from app.core.database import async_session
from app.services.scanner import GiftScanner
from app.services.telegram_notifier import telegram_notifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run single scan with notifications."""
    logger.info("="*60)
    logger.info("Testing Scanner with Telegram Notifications")
    logger.info("="*60)

    # Test Telegram connection
    logger.info("\n1. Testing Telegram bot...")
    connected = await telegram_notifier.test_connection()
    if not connected:
        logger.error("Telegram bot not connected!")
        return

    logger.info("✓ Telegram bot connected\n")

    # Run scan
    logger.info("2. Running price scan...")
    scanner = GiftScanner()

    async with async_session() as session:
        result = await scanner.run_full_scan(session)

    logger.info("\n" + "="*60)
    logger.info("SCAN COMPLETE")
    logger.info("="*60)
    logger.info(f"Duration: {result['duration_sec']}s")
    logger.info(f"Gifts scanned: {result['total_gifts']}")
    logger.info(f"Snapshots saved: {result['saved']}")
    logger.info("\nPrices by source:")
    for source, count in result['sources'].items():
        logger.info(f"  • {source}: {count} prices")

    logger.info("\n✓ Check your Telegram for arbitrage alerts!")


if __name__ == "__main__":
    asyncio.run(main())
