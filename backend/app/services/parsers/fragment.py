"""
Fragment.com gift price scraper.

URL pattern: https://fragment.com/gifts/{slug}?sort=price_asc&filter=sale
First listed price (sort ascending) = floor price in TON.
"""

import logging
import re
from decimal import Decimal
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.services.parsers.base import BaseParser, GiftPrice

logger = logging.getLogger(__name__)

BASE_URL = "https://fragment.com/gifts"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Matches comma-formatted numbers like "12,990" or plain "500"
_PRICE_RE = re.compile(r"^[\d,]+(?:\.\d+)?$")


class FragmentParser(BaseParser):
    source_name = "Fragment"
    supports_bulk = False

    async def fetch_gift_price(self, slug: str) -> Optional[GiftPrice]:
        """
        Fetch the floor price (in TON) for a gift collection from Fragment.

        Returns GiftPrice or None if nothing found / error.
        """
        url = f"{BASE_URL}/{slug}?sort=price_asc&filter=sale"
        logger.info("Fetching Fragment price for '%s': %s", slug, url)

        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Fragment request failed for '%s': %s", slug, exc)
            return None

        price = _parse_floor_price(resp.text, slug)
        if price is None:
            return None

        return GiftPrice(
            price=price,
            currency="TON",
            source=self.source_name,
            slug=slug,
        )


def _parse_floor_price(html: str, slug: str) -> Decimal | None:
    """Extract the first (lowest) price from the page HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Strategy 1: look for table rows with gift links + price cells
    for link in soup.find_all("a", href=re.compile(rf"/gift/{slug}-\d+")):
        row = link.find_parent("tr") or link.find_parent("div")
        if row is None:
            continue
        price = _extract_price_from_element(row)
        if price is not None:
            logger.info("Fragment floor for '%s': %s TON", slug, price)
            return price

    # Strategy 2: scan all text nodes matching price pattern near gift links
    for link in soup.find_all("a", href=re.compile(rf"/gift/{slug}-\d+")):
        for sibling in link.find_all_next(string=True, limit=10):
            text = sibling.strip()
            if _PRICE_RE.match(text):
                price = _text_to_decimal(text)
                if price and price > 0:
                    logger.info("Fragment floor for '%s': %s TON (fallback)", slug, price)
                    return price

    # Strategy 3: regex on raw HTML as last resort
    pattern = rf'/gift/{slug}-\d+.*?>([\d,]+(?:\.\d+)?)\s*(?:TON)?<'
    match = re.search(pattern, html, re.DOTALL)
    if match:
        price = _text_to_decimal(match.group(1))
        if price and price > 0:
            logger.info("Fragment floor for '%s': %s TON (regex)", slug, price)
            return price

    logger.warning("Could not parse Fragment price for '%s'", slug)
    return None


def _extract_price_from_element(el) -> Decimal | None:
    """Try to find a price number inside an element."""
    for tag in el.find_all(["td", "span", "div", "b"]):
        text = tag.get_text(strip=True)
        if _PRICE_RE.match(text):
            return _text_to_decimal(text)
    return None


def _text_to_decimal(text: str) -> Decimal | None:
    """Convert '12,990' → Decimal('12990')."""
    try:
        return Decimal(text.replace(",", ""))
    except Exception:
        return None
