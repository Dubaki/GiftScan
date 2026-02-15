"""
Tonnel marketplace direct parser.

Fetches gift floor prices from Tonnel API (gifts2.tonnel.network).
No authentication required for read-only pageGifts endpoint.

Strategy: Price-range segmentation with narrow bands
- Query listings in narrow price bands (e.g., 20-25, 25-30, 30-36, ...)
- Each band sorted ASC → first occurrence of each gift = floor price
- Narrow bands ensure we don't miss gifts buried under cheaper listings
- Paginate within each band until no new gift names appear

Uses curl_cffi to bypass Cloudflare TLS fingerprinting.
"""

import asyncio
import json
import logging
from decimal import Decimal
from typing import Optional

from curl_cffi.requests import AsyncSession

from app.services.parsers.base import BaseParser, GiftPrice
from app.services.normalization import normalize_gift_name

logger = logging.getLogger(__name__)

TONNEL_API_URL = "https://gifts2.tonnel.network/api/pageGifts"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://market.tonnel.network",
    "Referer": "https://market.tonnel.network/",
    "Content-Type": "application/json",
}

# Strategy: focus on 50-300 TON segment (best arbitrage margin zone)
MIN_FLOOR_TON = 50

# Narrow price ranges for the 50-300 TON segment
PRICE_RANGES = [
    (50, 58), (58, 67), (67, 78), (78, 90), (90, 100),
    (100, 120), (120, 150), (150, 200),
    (200, 250), (250, 300),
]

PAGE_SIZE = 30
REQUEST_DELAY = 3.0
MAX_CF_RETRIES = 3
NO_NEW_PAGES = 2  # Stop paginating a range after N pages with no new gift names
MAX_PAGES_PER_RANGE = 10


def _make_range_filter(price_min: float, price_max: float) -> str:
    """Build MongoDB-style filter for listed gifts in a price range."""
    return json.dumps({
        "price": {"$gte": price_min, "$lte": price_max},
        "refunded": {"$ne": True},
        "buyer": {"$exists": False},
        "export_at": {"$exists": True},
        "asset": "TON",
    })


class TonnelDirectParser(BaseParser):
    """
    Tonnel marketplace parser via direct API.

    Price-range segmentation with narrow bands and smart pagination.
    """

    source_name = "Tonnel"
    supports_bulk = True

    async def fetch_gift_price(self, slug: str) -> Optional[GiftPrice]:
        all_prices = await self.fetch_all_prices()
        return all_prices.get(slug)

    async def fetch_all_prices(self) -> dict[str, GiftPrice]:
        logger.info("Tonnel: Fetching floor prices via %d price ranges", len(PRICE_RANGES))

        floors: dict[str, float] = {}  # gift_name -> floor price
        total_requests = 0

        async with AsyncSession(impersonate="chrome120") as session:
            cf_retries = 0

            for price_min, price_max in PRICE_RANGES:
                range_filter = _make_range_filter(price_min, price_max)
                label = f"{price_min}-{price_max}"

                page = 1
                no_new_count = 0

                while page <= MAX_PAGES_PER_RANGE:
                    payload = {
                        "filter": range_filter,
                        "limit": PAGE_SIZE,
                        "page": page,
                        "sort": json.dumps({"price": 1}),  # ASC
                        "ref": 0,
                        "user_auth": "",
                    }

                    try:
                        resp = await session.post(
                            TONNEL_API_URL, json=payload, headers=HEADERS, timeout=15,
                        )
                    except Exception as exc:
                        logger.error("Tonnel range %s page %d: request error: %s", label, page, exc)
                        break

                    total_requests += 1

                    if resp.status_code == 403:
                        cf_retries += 1
                        if cf_retries > MAX_CF_RETRIES:
                            logger.warning("Tonnel: Cloudflare blocked at range %s, stopping", label)
                            break
                        await asyncio.sleep(5 * cf_retries)
                        continue

                    cf_retries = 0

                    if resp.status_code != 200:
                        break

                    try:
                        items = resp.json()
                    except Exception:
                        break

                    if not isinstance(items, list) or not items:
                        break

                    # Extract gift names and floor prices
                    new_names = 0
                    for item in items:
                        name = item.get("name", "")
                        price = item.get("price")
                        if not name or price is None or price <= 0:
                            continue

                        if name not in floors:
                            floors[name] = price
                            new_names += 1
                        elif price < floors[name]:
                            floors[name] = price

                    # Stop paginating this range if no new gifts found
                    if new_names == 0:
                        no_new_count += 1
                        if no_new_count >= NO_NEW_PAGES:
                            break
                    else:
                        no_new_count = 0

                    if len(items) < PAGE_SIZE:
                        break

                    page += 1
                    await asyncio.sleep(REQUEST_DELAY)

                if cf_retries > MAX_CF_RETRIES:
                    break

                await asyncio.sleep(REQUEST_DELAY)

        logger.info("Tonnel: %d requests, found %d gifts across price ranges",
                     total_requests, len(floors))

        # Normalize to canonical slugs, filter >= MIN_FLOOR_TON
        results: dict[str, GiftPrice] = {}
        for gift_name, price_val in floors.items():
            if price_val < MIN_FLOOR_TON:
                continue

            slug = normalize_gift_name(gift_name, source="Tonnel")
            if not slug:
                continue

            price = Decimal(str(price_val))
            if slug not in results or price < results[slug].price:
                results[slug] = GiftPrice(
                    price=price,
                    currency="TON",
                    source=self.source_name,
                    slug=slug,
                    raw_name=gift_name,
                )

        logger.info("Tonnel: %d gifts with floor prices (>= %d TON)", len(results), MIN_FLOOR_TON)
        return results
