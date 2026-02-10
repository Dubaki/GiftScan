"""
Tonnel marketplace direct parser.

Fetches gift floor prices from Tonnel API (gifts2.tonnel.network).
No authentication required for read-only pageGifts endpoint.

Strategy: Paginate listings sorted by price ASC and DESC to discover
all gift names and their floor prices efficiently.

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

# MongoDB-style filter for listed gifts
_LISTED_FILTER = json.dumps({
    "price": {"$exists": True},
    "refunded": {"$ne": True},
    "buyer": {"$exists": False},
    "export_at": {"$exists": True},
    "asset": "TON",
})

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://market.tonnel.network",
    "Referer": "https://market.tonnel.network/",
    "Content-Type": "application/json",
}

# Max pages per direction (ASC / DESC)
MAX_PAGES = 30
PAGE_SIZE = 30
# Delay between requests to avoid Cloudflare rate limiting
REQUEST_DELAY = 1.0
# Stop if no new gifts found for this many consecutive pages
NO_NEW_THRESHOLD = 3


class TonnelDirectParser(BaseParser):
    """
    Tonnel marketplace parser via direct API.

    Uses pageGifts endpoint with bidirectional pagination:
    - ASC: cheapest listings first (floor prices for common gifts)
    - DESC: most expensive first (discovers rare/expensive gifts)

    This covers all gift collections without requiring authentication.
    """

    source_name = "Tonnel"
    supports_bulk = True

    async def fetch_gift_price(self, slug: str) -> Optional[GiftPrice]:
        all_prices = await self.fetch_all_prices()
        return all_prices.get(slug)

    async def fetch_all_prices(self) -> dict[str, GiftPrice]:
        """
        Bulk-fetch all gift floor prices from Tonnel.

        Paginates through listings sorted by price ASC (cheap gifts)
        then DESC (expensive gifts) to discover all unique gift names
        and their floor prices.
        """
        logger.info("Tonnel: Fetching floor prices via pageGifts API")

        # {gift_name: lowest_price} — raw names before normalization
        raw_floors: dict[str, float] = {}

        async with AsyncSession(impersonate="chrome120") as session:
            # Pass 1: price ASC — gets floor prices for common/cheap gifts
            await self._paginate(session, sort_dir=1, raw_floors=raw_floors, label="ASC")
            # Pass 2: price DESC — discovers expensive/rare gifts
            await self._paginate(session, sort_dir=-1, raw_floors=raw_floors, label="DESC")

        # Normalize to canonical slugs
        results: dict[str, GiftPrice] = {}

        for gift_name, price_val in raw_floors.items():
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

        logger.info("Tonnel: %d gifts with floor prices", len(results))
        return results

    async def _paginate(
        self,
        session: AsyncSession,
        sort_dir: int,
        raw_floors: dict[str, float],
        label: str,
    ):
        """Paginate through Tonnel listings in one direction."""
        no_new_count = 0
        page = 1
        cf_retries = 0
        max_cf_retries = 3  # Max consecutive 403 retries per page

        while page <= MAX_PAGES:
            payload = {
                "filter": _LISTED_FILTER,
                "limit": PAGE_SIZE,
                "page": page,
                "sort": json.dumps({"price": sort_dir}),
                "ref": 0,
                "user_auth": "",
            }

            try:
                resp = await session.post(
                    TONNEL_API_URL,
                    json=payload,
                    headers=HEADERS,
                    timeout=15,
                )
            except Exception as exc:
                logger.error("Tonnel %s page %d: request error: %s", label, page, exc)
                break

            if resp.status_code == 403:
                cf_retries += 1
                if cf_retries > max_cf_retries:
                    logger.warning(
                        "Tonnel %s page %d: Cloudflare blocked after %d retries, stopping",
                        label, page, max_cf_retries,
                    )
                    break
                delay = 3 * cf_retries
                logger.debug(
                    "Tonnel %s page %d: Cloudflare 403, retry %d/%d in %ds",
                    label, page, cf_retries, max_cf_retries, delay,
                )
                await asyncio.sleep(delay)
                continue  # Retry same page

            # Reset CF retry counter on success
            cf_retries = 0

            if resp.status_code != 200:
                logger.warning("Tonnel %s page %d: HTTP %d", label, page, resp.status_code)
                break

            try:
                items = resp.json()
            except Exception:
                logger.warning("Tonnel %s page %d: JSON parse error", label, page)
                break

            if not isinstance(items, list) or not items:
                break

            new_gifts = 0
            for item in items:
                name = item.get("name", "")
                price = item.get("price")
                if not name or price is None or price <= 0:
                    continue

                if name not in raw_floors:
                    raw_floors[name] = price
                    new_gifts += 1
                elif price < raw_floors[name]:
                    raw_floors[name] = price

            if new_gifts == 0:
                no_new_count += 1
                if no_new_count >= NO_NEW_THRESHOLD:
                    logger.debug(
                        "Tonnel %s: no new gifts for %d pages, stopping at page %d",
                        label, NO_NEW_THRESHOLD, page,
                    )
                    break
            else:
                no_new_count = 0

            if len(items) < PAGE_SIZE:
                break

            page += 1
            await asyncio.sleep(REQUEST_DELAY)
