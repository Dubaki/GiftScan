"""
GetGems marketplace parser (stub).

GetGems has a GraphQL API at https://api.getgems.io/graphql, but it's protected
by WAF and blocks external requests. Official alternatives:
- https://getgems.io/public-api (requires browser/JS)
- https://tonapi.io (recommended)

TODO: Implement via TonAPI or browser automation when needed.
  - TonAPI: GET /v2/nfts/collections/{collection_address} for floor prices
  - Need to map gift slugs to TON collection addresses
"""

import logging
from typing import Optional
from decimal import Decimal # Import Decimal

from app.services.parsers.base import BaseParser, GiftPrice

logger = logging.getLogger(__name__)


class GetGemsParser(BaseParser):
    source_name = "GetGems"
    supports_bulk = False

    async def fetch_gift_price(self, slug: str) -> Optional[GiftPrice]:
        # Generate a mock price based on the slug's hash for some variety
        # This is a temporary implementation to demonstrate multi-source
        # functionality without live API integration.
        try:
            # Simple hash to get a pseudo-random, but consistent, number
            mock_base_price = Decimal(abs(hash(slug)) % 1000 + 500) / 100
            mock_price = mock_base_price + Decimal("0.05") # Add a small offset

            logger.info("Generating mock GetGems price for '%s': %s TON", slug, mock_price)

            return GiftPrice(
                price=mock_price,
                currency="TON",
                source=self.source_name,
                slug=slug,
            )
        except Exception as e:
            logger.error("Error generating mock price for GetGems '%s': %s", slug, e)
            return None
