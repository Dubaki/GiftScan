"""
Portals marketplace parser (stub).

API: https://portals-market.com
Auth: Telegram Web App initData required (Authorization: "tma <auth>").
Bulk API: giftsFloors() returns floor prices for all gifts in one call.

TODO: Implement when auth token is available.
  - GET /api/gifts/floors → all floor prices
  - GET /api/gifts/filter-floors → per-model/backdrop floors
"""

import logging
from typing import Optional

from app.services.parsers.base import BaseParser, GiftPrice

logger = logging.getLogger(__name__)


class PortalsParser(BaseParser):
    source_name = "Portals"
    supports_bulk = True

    async def fetch_gift_price(self, slug: str) -> Optional[GiftPrice]:
        # Requires auth token — not implemented yet
        return None

    async def fetch_all_prices(self) -> dict[str, GiftPrice]:
        # Requires auth token — not implemented yet
        return {}
