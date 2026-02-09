"""
Debug script to see what TonAPI is returning and why parsers return 0 prices.
"""

import asyncio
import logging
from app.services.parsers.tonapi_enhanced import TonAPIEnhancedParser
from app.services.parsers.tonapi_marketplace_parsers import (
    GetGemsParser,
    PortalsParser,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_tonapi():
    """Debug TonAPI data."""
    logger.info("=== Debugging TonAPI ===\n")

    # 1. Fetch raw TonAPI data
    tonapi = TonAPIEnhancedParser()
    listings = await tonapi._fetch_nft_listings()

    logger.info(f"Total NFT items: {len(listings)}")
    logger.info(f"Items on sale: {len([l for l in listings if l.price_ton > 0])}\n")

    # 2. Show first 10 items
    logger.info("=== First 10 items: ===")
    for i, listing in enumerate(listings[:10]):
        logger.info(
            f"{i+1}. {listing.gift_name} ({listing.gift_slug}) - "
            f"{listing.price_ton} TON - {listing.marketplace}"
        )

    # 3. Show unique marketplaces
    marketplaces = set(l.marketplace for l in listings)
    logger.info(f"\n=== Unique marketplaces: {marketplaces} ===\n")

    # 4. Test GetGems parser
    logger.info("=== Testing GetGems parser: ===")
    getgems = GetGemsParser()
    getgems_prices = await getgems.fetch_all_prices()
    logger.info(f"GetGems found {len(getgems_prices)} prices")
    for slug, price in list(getgems_prices.items())[:5]:
        logger.info(f"  - {slug}: {price.price} TON")

    # 5. Test Portals parser
    logger.info("\n=== Testing Portals parser: ===")
    portals = PortalsParser()
    portals_prices = await portals.fetch_all_prices()
    logger.info(f"Portals found {len(portals_prices)} prices")
    for slug, price in list(portals_prices.items())[:5]:
        logger.info(f"  - {slug}: {price.price} TON")


if __name__ == "__main__":
    asyncio.run(debug_tonapi())
