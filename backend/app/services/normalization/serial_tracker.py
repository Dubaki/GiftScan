"""
NFT serial number tracking for deep arbitrage opportunities.

Tracks individual NFT items by serial number (#777, #1234, etc.)
to identify when the same numbered item is priced differently
across marketplaces.
"""

import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SerialListing:
    """Individual NFT listing with serial number."""

    slug: str  # Gift type (e.g., "bluestar")
    serial: int  # Serial number (e.g., 777)
    price: Decimal
    currency: str
    source: str  # Marketplace
    nft_address: Optional[str] = None  # TON address for verification


class SerialTracker:
    """
    Tracks NFT items by serial number for cross-marketplace arbitrage.

    Example:
        If "Blue Star #777" is listed at 100 TON on GetGems
        and 80 TON on Fragment, that's a priority arbitrage signal.
    """

    def __init__(self):
        # {slug: {serial: [SerialListing, ...]}}
        self._listings: dict[str, dict[int, list[SerialListing]]] = {}

    def add_listing(self, listing: SerialListing):
        """Add a serial-specific listing to the tracker."""
        if listing.slug not in self._listings:
            self._listings[listing.slug] = {}

        if listing.serial not in self._listings[listing.slug]:
            self._listings[listing.slug][listing.serial] = []

        self._listings[listing.slug][listing.serial].append(listing)

    def find_arbitrage(
        self, min_spread_ton: Decimal = Decimal("10")
    ) -> list[dict]:
        """
        Find serial-specific arbitrage opportunities.

        Args:
            min_spread_ton: Minimum price difference in TON

        Returns:
            List of arbitrage opportunities with buy/sell sources
        """
        opportunities = []

        for slug, serials in self._listings.items():
            for serial, listings in serials.items():
                if len(listings) < 2:
                    continue  # Need at least 2 sources to compare

                # Sort by price (all should be in TON for comparison)
                sorted_listings = sorted(
                    listings, key=lambda x: x.price
                )

                lowest = sorted_listings[0]
                highest = sorted_listings[-1]

                spread = highest.price - lowest.price

                if spread >= min_spread_ton:
                    opportunities.append({
                        "slug": slug,
                        "serial": serial,
                        "buy_price": float(lowest.price),
                        "buy_source": lowest.source,
                        "sell_price": float(highest.price),
                        "sell_source": highest.source,
                        "spread_ton": float(spread),
                        "spread_pct": float(
                            (spread / lowest.price * 100) if lowest.price > 0 else 0
                        ),
                    })

        # Sort by spread descending
        opportunities.sort(key=lambda x: x["spread_ton"], reverse=True)

        return opportunities

    def get_serial_listings(self, slug: str, serial: int) -> list[SerialListing]:
        """Get all listings for a specific serial number."""
        return self._listings.get(slug, {}).get(serial, [])

    def clear(self):
        """Clear all tracked listings (call before new scan)."""
        self._listings.clear()

    @staticmethod
    def extract_serial(raw_name: str) -> Optional[int]:
        """
        Extract serial number from gift name.

        Examples:
            "Blue Star #777" → 777
            "Lollipop (#1234)" → 1234
            "Cake" → None
        """
        # Look for #digits or (#digits)
        match = re.search(r"#?(\d{1,6})", raw_name)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None


# Singleton instance
serial_tracker = SerialTracker()
