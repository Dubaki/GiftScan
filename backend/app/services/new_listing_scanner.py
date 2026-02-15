"""
New Listing Scanner service.

Periodically polls TonAPI for new NFT listings for sale within configured collections.
Uses Redis to track already seen listings to avoid duplicate notifications.
When a new listing is found, it's passed to the arbitrage orchestrator for valuation.
"""

import asyncio
import logging
import time
import json
from decimal import Decimal
from typing import Set, Dict, Optional, List

import aiohttp

from app.core.config import settings
from app.services.parsers.tonapi_enhanced import TonAPIEnhancedParser, NFTListing, GIFT_COLLECTIONS
from app.services.rate_limiting import get_rate_limiter, retry_with_backoff
from app.services.cache import redis_client
from app.services.arbitrage_orchestrator import arbitrage_orchestrator
from app.models.gift import GiftCatalog
from app.models.snapshot import MarketSnapshot

logger = logging.getLogger(__name__)

TONAPI_LISTING_CACHE_KEY = "new_listing_scanner:seen_listings"
TONAPI_LISTING_TTL = 3600 * 24 # Keep seen listings in cache for 24 hours (to handle delisted/relisted)

class NewListingScanner:
    """
    Scans TonAPI for new NFT listings and processes them.
    """

    def __init__(self):
        self.tonapi_parser = TonAPIEnhancedParser()
        # Initialize seen_listings from Redis
        self.seen_listings: Set[str] = self._load_seen_listings_from_cache()

    def _load_seen_listings_from_cache(self) -> Set[str]:
        """Loads seen listings from Redis cache."""
        try:
            cached_data = redis_client.get(TONAPI_LISTING_CACHE_KEY)
            if cached_data:
                return set(json.loads(cached_data))
        except Exception as e:
            logger.error(f"Failed to load seen listings from Redis: {e}")
        return set()

    def _save_seen_listings_to_cache(self) -> None:
        """Saves current seen listings to Redis cache."""
        try:
            # Only save active listings to prevent cache from growing indefinitely with old/delisted items
            # This will be updated with actual active listings after each scan
            # For now, we save everything seen in the current scan
            redis_client.setex(TONAPI_LISTING_CACHE_KEY, TONAPI_LISTING_TTL, json.dumps(list(self.seen_listings)))
        except Exception as e:
            logger.error(f"Failed to save seen listings to Redis: {e}")

    async def run_scan(self) -> None:
        """
        Executes a scan for new listings.
        """
        logger.info("New Listing Scanner: Starting scan for new NFT listings...")
        
        current_active_listings: Set[str] = set()
        listings: List[NFTListing] = []

        # Fetch all listings from TonAPI (using the enhanced parser's bulk fetch)
        # We need to adapt this, as TonAPIEnhancedParser.fetch_all_prices returns GiftPrice
        # We need the raw NFTListing objects for their full metadata
        # So we'll call its internal _fetch_nft_listings
        try:
            listings = await self.tonapi_parser._fetch_nft_listings()
        except Exception as e:
            logger.error(f"New Listing Scanner: Failed to fetch listings from TonAPI: {e}")
            return

        for listing in listings:
            # Use a unique identifier for the listing (e.g., collection_address:nft_address)
            # NFTListing doesn't directly have collection_address, so we'll use gift_slug:nft_address
            listing_id = f"{listing.gift_slug}:{listing.nft_address}"
            current_active_listings.add(listing_id)

            if listing_id not in self.seen_listings:
                logger.warning(f"NEW LISTING DETECTED: {listing.gift_name} ({listing.gift_slug}) - {listing.price_ton} TON on {listing.marketplace}")
                
                # Pass this new listing to the arbitrage orchestrator for valuation
                # Arbitrage orchestrator expects specific parameters, not raw NFTListing
                try:
                    # We need to map NFTListing to the parameters expected by analyze_opportunity
                    # For TonAPI, the buy_source will be derived from listing.marketplace
                    opportunity = await arbitrage_orchestrator.analyze_opportunity(
                        gift_name=listing.gift_name,
                        gift_slug=listing.gift_slug,
                        serial_number=listing.serial_number,
                        tonapi_floor_price=listing.price_ton,
                        tonapi_marketplace=listing.marketplace, # Use marketplace from listing
                        nft_address=listing.nft_address,
                        fragment_price=Decimal('0.0'), # Fragment price is unknown for *new* listing
                        attributes=listing.attributes,
                    )

                    if opportunity:
                        # Send alert for the new listing if it's considered profitable by arbitrage orchestrator
                        await arbitrage_orchestrator.send_alert(opportunity)
                except Exception as e:
                    logger.error(f"New Listing Scanner: Error processing new listing {listing_id}: {e}")

                self.seen_listings.add(listing_id)
        
        # Update seen listings: remove old listings that are no longer active, add new ones
        # This keeps the cache clean and prevents it from growing indefinitely
        self.seen_listings = current_active_listings

        # Save the updated set of seen listings to Redis
        self._save_seen_listings_to_cache()

        logger.info(f"New Listing Scanner: Scan completed. Processed {len(listings)} listings. Found {len(self.seen_listings)} active listings.")

# Singleton instance
new_listing_scanner = NewListingScanner()
