"""
Virtual parsers that split TonAPI data by marketplace.

Instead of one "TonAPI" source returning floor price, we create separate parsers
for each marketplace (GetGems, Portals, MRKT, Tonnel) to display all 5 prices in UI.

This allows the frontend to show:
- Fragment (from FragmentParser)
- GetGems (from TonAPIGetGemsParser)
- Portals (from TonAPIPortalsParser)
- MRKT (from TonAPIMRKTParser)
- Tonnel (from TonAPITonnelParser)

IMPORTANT: All parsers share the same TonAPI data fetch via caching to avoid
making 4 separate API calls (rate limit optimization).
"""

import logging
import time
from typing import Optional, List
from decimal import Decimal

from app.services.parsers.base import BaseParser, GiftPrice
from app.services.parsers.tonapi_enhanced import TonAPIEnhancedParser, NFTListing

logger = logging.getLogger(__name__)


# Shared cache for TonAPI listings (all parsers share the same data)
_tonapi_cache: dict = {
    "listings": None,
    "timestamp": 0,
    "ttl": 90,  # Cache for 90 seconds (scan interval is 60s, this adds buffer)
}


async def get_tonapi_listings() -> List[NFTListing]:
    """
    Get TonAPI listings with caching.

    All marketplace parsers call this function to get shared data,
    avoiding multiple API calls per scan cycle.
    """
    current_time = time.time()

    # Check cache
    if (
        _tonapi_cache["listings"] is not None
        and current_time - _tonapi_cache["timestamp"] < _tonapi_cache["ttl"]
    ):
        logger.debug("Using cached TonAPI listings")
        return _tonapi_cache["listings"]

    # Fetch fresh data
    logger.info("Fetching fresh TonAPI listings (cache miss)")
    tonapi = TonAPIEnhancedParser()
    listings = await tonapi._fetch_nft_listings()

    # Update cache
    _tonapi_cache["listings"] = listings
    _tonapi_cache["timestamp"] = current_time

    return listings


class TonAPIMarketplaceParser(BaseParser):
    """
    Base class for marketplace-specific parsers that extract data from TonAPI.

    Each subclass filters TonAPI results for a specific marketplace.
    Uses shared caching to avoid redundant API calls.
    """

    source_name = "TonAPI"  # Override in subclasses
    supports_bulk = True
    marketplace_name = ""  # Override in subclasses (e.g., "GetGems")

    async def fetch_gift_price(self, slug: str) -> Optional[GiftPrice]:
        """Fetch price for a single gift from this marketplace."""
        all_prices = await self.fetch_all_prices()
        return all_prices.get(slug)

    async def fetch_all_prices(self) -> dict[str, GiftPrice]:
        """
        Fetch all prices, filtered for this specific marketplace.

        Uses shared TonAPI cache to avoid redundant API calls.
        """
        # Get all listings from TonAPI (cached)
        listings = await get_tonapi_listings()

        # Filter for this marketplace only (case-insensitive partial match)
        marketplace_listings = [
            listing for listing in listings
            if self.marketplace_name.lower() in listing.marketplace.lower()
        ]

        if not marketplace_listings:
            logger.debug(
                "%s: No listings found",
                self.source_name
            )
            return {}

        # Group by slug, keep lowest price for this marketplace
        results: dict[str, GiftPrice] = {}

        for listing in marketplace_listings:
            slug = listing.gift_slug

            if slug not in results or listing.price_ton < results[slug].price:
                # Set source to marketplace name (not "TonAPI-GetGems")
                gift_price = listing.to_gift_price()
                gift_price.source = self.marketplace_name  # Override source
                results[slug] = gift_price

        logger.info(
            "%s: %d gifts with floor prices",
            self.source_name,
            len(results)
        )

        return results


class GetGemsParser(TonAPIMarketplaceParser):
    """GetGems marketplace parser (via TonAPI)."""
    source_name = "GetGems"
    marketplace_name = "GetGems"


class PortalsParser(TonAPIMarketplaceParser):
    """Portals marketplace parser (via TonAPI)."""
    source_name = "Portals"
    marketplace_name = "Portals"


class MRKTParser(TonAPIMarketplaceParser):
    """MRKT (Marketapp) marketplace parser (via TonAPI)."""
    source_name = "MRKT"
    marketplace_name = "Marketapp"  # Partial match for "Marketapp Marketplace"


class TonnelParser(TonAPIMarketplaceParser):
    """Tonnel marketplace parser (via TonAPI)."""
    source_name = "Tonnel"
    marketplace_name = "Tonnel"
