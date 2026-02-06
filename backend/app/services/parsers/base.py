"""
Base classes and types for marketplace parsers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class GiftPrice:
    """Price result from a single marketplace for a single gift."""

    price: Decimal
    currency: str  # "TON", "USDT"
    source: str  # "Fragment", "GetGems", ...
    slug: str  # canonical gift slug


class BaseParser(ABC):
    """Abstract base for all marketplace parsers."""

    source_name: str = ""
    supports_bulk: bool = False

    @abstractmethod
    async def fetch_gift_price(self, slug: str) -> Optional[GiftPrice]:
        """Fetch floor price for one gift. Return None on failure."""
        ...

    async def fetch_all_prices(self) -> dict[str, GiftPrice]:
        """
        Bulk-fetch all gift floor prices in a single call.
        Override for marketplaces that support it (supports_bulk=True).
        Returns {canonical_slug: GiftPrice}.
        """
        return {}
