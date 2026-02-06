"""
Generic parser for marketplaces accessed via the Th3ryks.dev API.
Each instance of this parser will represent a single market (e.g., 'tg-market', 'portals').
"""

import logging
from decimal import Decimal
from typing import Optional

import httpx

from app.services.parsers.base import BaseParser, GiftPrice

logger = logging.getLogger(__name__)

BASE_URL = "https://api.th3ryks.dev/guard"

# Markets supported by th3ryks.dev API, excluding Fragment which we parse directly
TH3RYKS_MARKETS = [
    "portals",
    "mrkt",
    "getgems",
    "tonnel",
]


class Th3ryksMarketParser(BaseParser):
    supports_bulk = False # This parser fetches price for one gift from one market

    def __init__(self, market_name: str):
        self._market_name = market_name
        self.source_name = market_name.capitalize() # e.g., "Tg-market", "Portals"

    async def fetch_gift_price(self, slug: str) -> Optional[GiftPrice]:
        url = f"{BASE_URL}/{self._market_name}/{slug}"
        logger.info(
            "Fetching price for '%s' from Th3ryks API (market: %s): %s",
            slug,
            self._market_name,
            url,
        )

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            if data and "price" in data and data["price"] is not None:
                price_amount = Decimal(str(data["price"]))
                currency = data.get("currency", "TON")

                return GiftPrice(
                    price=price_amount,
                    currency=currency,
                    source=self.source_name, # Use capitalized market name as source
                    slug=slug,
                )
            else:
                logger.debug(
                    "No price found for '%s' from Th3ryks API (market: %s)",
                    slug,
                    self._market_name,
                )
                return None

        except httpx.HTTPError as exc:
            logger.warning(
                "Th3ryks API request failed for '%s' (market: %s): %s",
                slug,
                self._market_name,
                exc,
            )
            return None
        except Exception as e:
            logger.error(
                "Error parsing Th3ryks API response for '%s' (market: %s): %s",
                slug,
                self._market_name,
                e,
            )
            return None