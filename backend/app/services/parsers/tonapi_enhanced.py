"""
Enhanced TonAPI parser - primary data source for multi-marketplace NFT gift prices.

Collects NFT gifts from all marketplaces (GetGems, Portals, MRKT) via single TonAPI endpoint.
Replaces individual marketplace parsers for stability (no tma tokens needed).
"""

import logging
import re
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass

import aiohttp

from app.core.config import settings
from app.services.parsers.base import BaseParser, GiftPrice
from app.services.rate_limiting import get_rate_limiter, retry_with_backoff
from app.services.normalization import normalize_gift_name

logger = logging.getLogger(__name__)

TONAPI_BASE_URL = "https://tonapi.io/v2"

# All gift collections from GetGems (TOP 20 by volume)
# Source: https://getgems.io/gifts-collection (14 collections)
GIFT_COLLECTIONS = [
    # High volume collections (top performers)
    "EQATuUGdvrjLvTWE5ppVFOVCqU2dlCLUnKTsu0n1JYm9la10",  # Collection 1
    "EQCE80Aln8YfldnQLwWMvOfloLGgmPY0eGDJz9ufG3gRui3D",  # Loot Bags (2.5K volume)
    "EQC1gud6QO8NdJjVrqr7qFBMO0oQsktkvzhmIRoMKo8vxiyL",  # Collection 3
    "EQBI07PXew94YQz7GwN72nPNGF6htSTOJkuU4Kx_bjTZv32U",  # Collection 4
    "EQDIReleOkTxCD4g_XEm8xj0LYNg6-zMsTGAAwCA-vEbkGBu",  # Collection 5
    "EQCNsmpHqRSY_Dxnyh6P0MMO7zcABf8sVvG0wr245pBzO3B3",  # Collection 6
    "EQCrGA9slCoksgD-NyRDjtHySKN0Ts8k6hdueJkUkZZdD4_K",  # Collection 7
    "EQCt2C3yCRNX267B3l6h1QsU6agm4ZgTAb7NpVGiFKlBXOAA",  # Collection 8
    "EQDJsN9OJBhKGZoWZWtkEpzkCfIu16Z9UzTWbYjeLpuHdT5f",  # Collection 9
    "EQDvZ_9Z3tJ9k6eELLtTeuQAz4yOOWyYFZfzqNv2dGJiHvrF",  # Collection 10
    "EQACcQpR2fmdeENWdE2YGQWHVxSTyA8Zq4_k7rk_IaxCRXNe",  # Collection 11
    "EQAlROpjm1k1mW30r61qRx3lYHsZkTKXVSiaHEIhOlnYA4oy",  # Collection 12
    "EQARIAumGWBmKSv2BoMxtunCEFybIn6nimCq_laeqkD-AVSk",  # Collection 13
    "EQDeX0F1GDugNjtxkFRihu9ZyFFumBv2jYF5Al1thx2ADDQs",  # Collection 14
]


@dataclass
class NFTListing:
    """Enhanced NFT listing with marketplace and metadata."""

    gift_name: str  # e.g., "Milk Coffee"
    gift_slug: str  # normalized slug
    serial_number: Optional[int]  # e.g., 1234
    price_ton: Decimal
    marketplace: str  # "GetGems", "Portals", "MRKT", etc.
    nft_address: str
    owner_address: Optional[str] = None

    def to_gift_price(self) -> GiftPrice:
        """Convert to GiftPrice format."""
        return GiftPrice(
            price=self.price_ton,
            currency="TON",
            source=f"TonAPI-{self.marketplace}",
            slug=self.gift_slug,
            serial=self.serial_number,
            nft_address=self.nft_address,
            raw_name=self.gift_name,
        )


class TonAPIEnhancedParser(BaseParser):
    """
    Enhanced TonAPI parser - collects gifts from ALL marketplaces via single endpoint.

    Features:
    - Parses marketplace info from sale data
    - Extracts gift name and serial number
    - Aggregates prices by marketplace
    - Single source of truth for NFT prices
    """

    source_name = "TonAPI"
    supports_bulk = True

    # Marketplace contract addresses (TonAPI returns these)
    MARKETPLACE_CONTRACTS = {
        "EQBYTuYbLf8INxFtD8tQeNk5ZLy-nAX9ahQbG_yl1qQ-GEMS": "GetGems",
        "EQAJ8uWd7EBqsmpSWaRdf_I-8R8-XHwh3gsNKhy-UrdrPcUo": "Portals",
        "EQCjk1hh952vWaE9bRguFkAhDAL5jj3xj9p0uPWrFBq_GEMS": "GetGems",
        # Add more as discovered
    }

    def __init__(self):
        self.rate_limiter = get_rate_limiter(
            "tonapi", max_requests=1, window_sec=1.0  # Free tier: 1 req/sec
        )

    @retry_with_backoff(max_retries=3)
    async def fetch_gift_price(self, slug: str) -> Optional[GiftPrice]:
        """
        Fetch floor price for a single gift from TonAPI.
        Note: Prefer using fetch_all_prices() for efficiency.
        """
        all_prices = await self.fetch_all_prices()
        return all_prices.get(slug)

    @retry_with_backoff(max_retries=3)
    async def fetch_all_prices(self) -> dict[str, GiftPrice]:
        """
        Bulk-fetch all gift NFT listings from TonAPI.
        Returns {canonical_slug: GiftPrice} with LOWEST price per gift.
        """
        logger.info("Fetching all NFT gifts from TonAPI (multi-marketplace)")

        listings = await self._fetch_nft_listings()

        if not listings:
            logger.warning("TonAPI: No listings found")
            return {}

        # Group by slug, keep lowest price
        results: dict[str, GiftPrice] = {}

        for listing in listings:
            slug = listing.gift_slug

            if slug not in results or listing.price_ton < results[slug].price:
                results[slug] = listing.to_gift_price()
                logger.debug(
                    "TonAPI: %s floor updated to %.2f TON from %s",
                    slug,
                    listing.price_ton,
                    listing.marketplace,
                )

        logger.info(
            "TonAPI bulk fetch: %d unique gifts, %d total listings",
            len(results),
            len(listings),
        )
        return results

    async def _fetch_nft_listings(self) -> list[NFTListing]:
        """Fetch all NFT listings from multiple gift collections."""
        headers = self._get_headers()
        all_listings: list[NFTListing] = []
        total_fetched = 0

        # Loop through all gift collections
        for collection_address in GIFT_COLLECTIONS:
            logger.info(f"TonAPI: Fetching collection {collection_address[:10]}...")

            url = f"{TONAPI_BASE_URL}/nfts/collections/{collection_address}/items"
            params = {
                "limit": 1000,
                "offset": 0,
            }

            # Pagination loop for this collection
            while True:
                async with self.rate_limiter.acquire("tonapi"):
                    try:
                        timeout = aiohttp.ClientTimeout(total=20.0)
                        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                            async with session.get(url, params=params) as resp:
                                resp.raise_for_status()
                                data = await resp.json()
                    except (aiohttp.ClientError, Exception) as exc:
                        logger.error("TonAPI request failed for %s: %s", collection_address[:10], exc)
                        break

                nft_items = data.get("nft_items", [])
                if not nft_items:
                    break

                # Process each NFT item
                for item in nft_items:
                    listing = self._parse_nft_item(item)
                    if listing:
                        all_listings.append(listing)

                total_fetched += len(nft_items)

                # Check pagination
                if len(nft_items) < params["limit"]:
                    break

                params["offset"] += params["limit"]

                # Safety limit per collection (500 items for stability with 14 collections)
                if params["offset"] >= 500:
                    logger.info(f"TonAPI: Reached 500 items limit for collection {collection_address[:10]}")
                    break

        logger.info("TonAPI: Fetched %d total items from %d collections, %d on sale",
                   total_fetched, len(GIFT_COLLECTIONS), len(all_listings))
        return all_listings

    def _parse_nft_item(self, item: dict) -> Optional[NFTListing]:
        """Parse a single NFT item into NFTListing."""
        # Check if item is for sale
        sale = item.get("sale")
        if not sale:
            return None

        # Get price
        price_data = sale.get("price")
        if not price_data:
            return None

        price_nano = price_data.get("value")
        if price_nano is None:
            return None

        price_ton = Decimal(str(price_nano)) / Decimal("1000000000")

        # Get NFT address
        nft_address = item.get("address")
        if not nft_address:
            return None

        # Extract metadata
        metadata = item.get("metadata", {})
        raw_name = metadata.get("name", "")

        if not raw_name:
            return None

        # Parse gift name and serial number
        gift_name, serial_number = self._parse_gift_metadata(raw_name)
        gift_slug = normalize_gift_name(gift_name, source=self.source_name)

        if not gift_slug:
            return None

        # Detect marketplace
        marketplace = self._detect_marketplace(sale)

        # Owner address (optional)
        owner = item.get("owner", {}).get("address")

        return NFTListing(
            gift_name=gift_name,
            gift_slug=gift_slug,
            serial_number=serial_number,
            price_ton=price_ton,
            marketplace=marketplace,
            nft_address=nft_address,
            owner_address=owner,
        )

    def _parse_gift_metadata(self, raw_name: str) -> tuple[str, Optional[int]]:
        """
        Extract gift name and serial number from metadata.

        Examples:
            "Milk Coffee #1234" → ("Milk Coffee", 1234)
            "Blue Star (#777)" → ("Blue Star", 777)
            "Lollipop" → ("Lollipop", None)
        """
        # Extract serial number
        serial = None
        match = re.search(r'#(\d+)', raw_name)
        if match:
            serial = int(match.group(1))
            # Remove serial from name
            raw_name = re.sub(r'\s*[#(]\d+\)?', '', raw_name).strip()

        return raw_name, serial

    def _detect_marketplace(self, sale_data: dict) -> str:
        """
        Detect marketplace from sale data.

        TonAPI provides marketplace info in sale.market or sale.address.
        """
        # Try market field first
        market = sale_data.get("market", {})
        if isinstance(market, dict):
            market_name = market.get("name")
            if market_name:
                return market_name

        # Try marketplace address
        marketplace_address = sale_data.get("address")
        if marketplace_address:
            return self.MARKETPLACE_CONTRACTS.get(marketplace_address, "Unknown")

        # Fallback
        return "TonAPI"

    def _get_headers(self) -> dict:
        """Build request headers with API key."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "GiftScan/1.0",
        }

        if settings.TONAPI_KEY:
            headers["Authorization"] = f"Bearer {settings.TONAPI_KEY}"
        else:
            logger.warning("TONAPI_KEY not set — using public rate limits")

        return headers


# Export enhanced parser
__all__ = ["TonAPIEnhancedParser", "NFTListing"]
