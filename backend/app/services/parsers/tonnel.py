"""
Tonnel marketplace parser (stub).

API: https://market.tonnel.network
Auth: Telegram Web App initData required (web-initData header).
Bulk API: filterStatsPretty() returns floor prices for all gifts in one call.

TODO: Implement when auth token is available.
  - POST /api/gifts/filter-stats → grouped floor prices
  - GET /api/gifts?gift_name=...&sort=price_asc → individual listings
"""

import logging
from typing import Optional

from app.services.parsers.base import BaseParser, GiftPrice

logger = logging.getLogger(__name__)


class TonnelParser(BaseParser):
    source_name = "Tonnel"
    supports_bulk = True

    async def fetch_gift_price(self, slug: str) -> Optional[GiftPrice]:
        # Requires auth token — not implemented yet
        return None

    async def fetch_all_prices(self) -> dict[str, GiftPrice]:
        # Requires auth token — not implemented yet
        return {}
