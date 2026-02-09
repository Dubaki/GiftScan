"""
Continuous scanner - runs price scans on schedule.

Fetches prices from all marketplaces every SCAN_INTERVAL_SEC.
Sends Telegram alerts when arbitrage opportunities > MIN_PROFIT_TON are found.
"""

import asyncio
import logging
from datetime import datetime

from app.core.config import settings
from app.core.database import async_session
from app.services.scanner import GiftScanner
from app.services.telegram_notifier import telegram_notifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run continuous scan loop."""
    logger.info("="*60)
    logger.info("🚀 GiftScan Arbitrage Scanner Starting")
    logger.info("="*60)
    logger.info(f"Scan interval: {settings.SCAN_INTERVAL_SEC}s")
    logger.info(f"Min profit threshold: {settings.MIN_PROFIT_TON} TON")
    logger.info(f"Telegram chat ID: {settings.TELEGRAM_CHAT_ID}")
    logger.info("="*60)

    # Test Telegram connection
    logger.info("\nTesting Telegram bot connection...")
    connected = await telegram_notifier.test_connection()
    if not connected:
        logger.warning("⚠️ Telegram bot not connected - notifications disabled")
    else:
        logger.info("✅ Telegram bot connected\n")

    scanner = GiftScanner()
    scan_count = 0

    while True:
        scan_count += 1
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 Starting scan #{scan_count} at {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"{'='*60}")

        try:
            async with async_session() as session:
                result = await scanner.run_full_scan(session)

            logger.info(f"\n✅ Scan #{scan_count} complete:")
            logger.info(f"   - Duration: {result['duration_sec']}s")
            logger.info(f"   - Gifts scanned: {result['total_gifts']}")
            logger.info(f"   - Snapshots saved: {result['saved']}")
            logger.info(f"\n   Prices by source:")
            for source, count in result['sources'].items():
                logger.info(f"     • {source}: {count} prices")

        except Exception as e:
            logger.error(f"❌ Scan #{scan_count} failed: {e}", exc_info=True)

        # Wait for next scan
        logger.info(f"\n⏱️ Waiting {settings.SCAN_INTERVAL_SEC}s until next scan...")
        await asyncio.sleep(settings.SCAN_INTERVAL_SEC)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\n👋 Scanner stopped by user")
