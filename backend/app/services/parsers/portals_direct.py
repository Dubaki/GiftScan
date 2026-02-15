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
        Bulk-fetch gift floor prices from Portals, including attribute-specific floors.
        Uses a direct POST request to /api/gifts/filterFloors for granular data.
        """
        auth_token = await get_portals_auth_token()
        if not auth_token:
            logger.warning("Portals: No auth token, skipping scan")
            return {}

        results: dict[str, GiftPrice] = {}
        portals_collection_names = ["Swiss Watches", "Loot Bags", "Scared Cats", "Precious Peaches"] # Example names

        headers = {
            "Authorization": f"tma {auth_token}",
            "Accept": "application/json",
        }

        async with AsyncSession(impersonate="chrome120") as session:
            for collection_name in portals_collection_names:
                logger.info(f"Portals: Fetching attribute floors for '{collection_name}'")
                
                json_payload = {"gift_name": collection_name}
                
                async with self.rate_limiter.acquire("portals"):
                    try:
                        resp = await session.post(
                            f"{PORTALS_API_URL}/gifts/filterFloors",
                            headers=headers,
                            json=json_payload,
                            timeout=15,
                        )

                        if resp.status_code == 401 or resp.status_code == 403:
                            logger.warning("Portals: Auth token rejected (HTTP %d), invalidating", resp.status_code)
                            invalidate_portals_token()
                            continue

                        resp.raise_for_status()
                        floors_data = resp.json()

                        # Process models
                        for model_name, details in floors_data.get("models", {}).items():
                            price_val = details.get("floor")
                            if price_val is None: continue
                            price = Decimal(str(price_val))
                            if price <= 0: continue

                            slug = normalize_gift_name(f"{collection_name} {model_name}", source=self.source_name)
                            if not slug: continue
                            
                            results[slug] = GiftPrice(
                                price=price,
                                currency="TON",
                                source=self.source_name,
                                slug=slug,
                                raw_name=f"{collection_name} {model_name}",
                                attributes={"model": model_name} # Store attribute
                            )

                        # Process backdrops
                        for backdrop_name, details in floors_data.get("backdrops", {}).items():
                            price_val = details.get("floor")
                            if price_val is None: continue
                            price = Decimal(str(price_val))
                            if price <= 0: continue

                            slug = normalize_gift_name(f"{collection_name} {backdrop_name}", source=self.source_name)
                            if not slug: continue
                            
                            results[slug] = GiftPrice(
                                price=price,
                                currency="TON",
                                source=self.source_name,
                                slug=slug,
                                raw_name=f"{collection_name} {backdrop_name}",
                                attributes={"backdrop": backdrop_name} # Store attribute
                            )

                        # Process symbols (if applicable)
                        for symbol_name, details in floors_data.get("symbols", {}).items():
                            price_val = details.get("floor")
                            if price_val is None: continue
                            price = Decimal(str(price_val))
                            if price <= 0: continue

                            slug = normalize_gift_name(f"{collection_name} {symbol_name}", source=self.source_name)
                            if not slug: continue
                            
                            results[slug] = GiftPrice(
                                price=price,
                                currency="TON",
                                source=self.source_name,
                                slug=slug,
                                raw_name=f"{collection_name} {symbol_name}",
                                attributes={"symbol": symbol_name} # Store attribute
                            )

                    except Exception as exc:
                        logger.error(f"Portals: Error fetching attribute floors for '{collection_name}': {exc}")

        logger.info("Portals: %d gifts with floor prices (including attributes)", len(results))
        return results
