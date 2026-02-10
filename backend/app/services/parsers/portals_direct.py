"""
Portals marketplace direct parser.

Fetches gift floor prices from Portals API (portal-market.com).
Requires TMA authorization token (auto-generated via Telethon or manual).

Uses curl_cffi to bypass Cloudflare TLS fingerprinting.
"""

import logging
from decimal import Decimal
from typing import Optional

from curl_cffi.requests import AsyncSession

from app.services.parsers.base import BaseParser, GiftPrice
from app.services.normalization import normalize_gift_name
from app.services.rate_limiting import get_rate_limiter
from app.services.tma_auth import get_portals_auth_token, invalidate_portals_token

logger = logging.getLogger(__name__)

PORTALS_API_URL = "https://portal-market.com/api"


class PortalsDirectParser(BaseParser):
    """
    Portals marketplace parser via direct API.

    Calls GET /api/collections/floors which returns floor prices
    for all gift collections in a single response.
    """

    source_name = "Portals"
    supports_bulk = True

    def __init__(self):
        self.rate_limiter = get_rate_limiter("portals", max_requests=5, window_sec=1.0)

    async def fetch_gift_price(self, slug: str) -> Optional[GiftPrice]:
        all_prices = await self.fetch_all_prices()
        return all_prices.get(slug)

    async def fetch_all_prices(self) -> dict[str, GiftPrice]:
        """
        Bulk-fetch all gift floor prices from Portals.

        GET /api/collections/floors
        Response: {"floorPrices": {"plushpepe": 2.5, "toybear": 14.84, ...}}

        Collection short names are normalized to canonical slugs.
        """
        auth_token = await get_portals_auth_token()
        if not auth_token:
            logger.warning("Portals: No auth token, skipping scan")
            return {}

        logger.info("Portals: Fetching floor prices via direct API")

        headers = {
            "Authorization": f"tma {auth_token}",
            "Accept": "application/json",
        }

        async with self.rate_limiter.acquire("portals"):
            try:
                async with AsyncSession(impersonate="chrome120") as session:
                    resp = await session.get(
                        f"{PORTALS_API_URL}/collections/floors",
                        headers=headers,
                        timeout=15,
                    )

                    # Handle auth expiry — invalidate token and skip this cycle
                    if resp.status_code == 401 or resp.status_code == 403:
                        logger.warning("Portals: Auth token rejected (HTTP %d), invalidating", resp.status_code)
                        invalidate_portals_token()
                        return {}

                    resp.raise_for_status()
                    data = resp.json()
            except Exception as exc:
                logger.error("Portals: API request failed: %s", exc)
                return {}

        floor_prices = data.get("floorPrices")
        if not floor_prices or not isinstance(floor_prices, dict):
            logger.warning("Portals: No floorPrices in response")
            return {}

        results: dict[str, GiftPrice] = {}

        for short_name, price_val in floor_prices.items():
            if price_val is None:
                continue

            try:
                price = Decimal(str(price_val))
            except Exception:
                continue

            if price <= 0:
                continue

            # Normalize the Portals short name to canonical slug
            slug = normalize_gift_name(short_name, source="Portals")
            if not slug:
                continue

            results[slug] = GiftPrice(
                price=price,
                currency="TON",
                source=self.source_name,
                slug=slug,
                raw_name=short_name,
            )

        logger.info("Portals: %d gifts with floor prices", len(results))
        return results
