"""
Currency converter for TON, USDT, Stars, and USD.

Fetches exchange rates and converts between currencies.
"""

import logging
from decimal import Decimal
from typing import Optional
import time

import aiohttp

logger = logging.getLogger(__name__)


class PriceConverter:
    """
    Handles currency conversions for arbitrage calculations.

    Supported: TON ↔ USD ↔ Stars
    """

    def __init__(self):
        self._rates: dict[str, Decimal] = {}
        self._last_update: float = 0
        self._cache_ttl: float = 300  # 5 minutes

    async def get_ton_usd_rate(self) -> Decimal:
        """
        Fetch TON/USD exchange rate from CoinGecko API.

        Returns:
            Current TON price in USD
        """
        await self._update_rates_if_needed()
        return self._rates.get("TON/USD", Decimal("5.0"))  # Fallback default

    async def get_stars_ton_rate(self) -> Decimal:
        """
        Get Telegram Stars/TON rate.

        As specified in 123.md: 1 Star = 0.013 TON (fixed rate).
        Can be updated to parse from fragment.com/stars if needed.
        """
        # Fixed rate from 123.md: 1 Star = 0.013 TON
        return Decimal("0.013")

    async def convert_to_ton(
        self, amount: Decimal, from_currency: str
    ) -> Decimal:
        """
        Convert any currency to TON.

        Args:
            amount: Amount to convert
            from_currency: Source currency (TON, USD, Stars, USDT)

        Returns:
            Amount in TON
        """
        if from_currency == "TON":
            return amount

        if from_currency in ("USD", "USDT"):
            ton_usd = await self.get_ton_usd_rate()
            return amount / ton_usd if ton_usd > 0 else Decimal("0")

        if from_currency == "Stars":
            # Stars → TON (direct conversion: 1 Star = 0.013 TON)
            stars_ton = await self.get_stars_ton_rate()
            return amount * stars_ton

        logger.warning("Unknown currency: %s, returning 0", from_currency)
        return Decimal("0")

    async def convert_from_ton(
        self, amount_ton: Decimal, to_currency: str
    ) -> Decimal:
        """
        Convert TON to any currency.

        Args:
            amount_ton: Amount in TON
            to_currency: Target currency (TON, USD, Stars, USDT)

        Returns:
            Converted amount
        """
        if to_currency == "TON":
            return amount_ton

        if to_currency in ("USD", "USDT"):
            ton_usd = await self.get_ton_usd_rate()
            return amount_ton * ton_usd

        if to_currency == "Stars":
            # TON → Stars (direct conversion: 1 Star = 0.013 TON)
            stars_ton = await self.get_stars_ton_rate()
            return amount_ton / stars_ton if stars_ton > 0 else Decimal("0")

        logger.warning("Unknown currency: %s, returning 0", to_currency)
        return Decimal("0")

    async def _update_rates_if_needed(self):
        """Update exchange rates if cache expired."""
        now = time.time()
        if now - self._last_update < self._cache_ttl:
            return  # Cache still valid

        try:
            await self._fetch_ton_rate()
            self._last_update = now
        except Exception as e:
            logger.error("Failed to update exchange rates: %s", e)

    async def _fetch_ton_rate(self):
        """Fetch TON/USD rate from TonAPI (as specified in 123.md)."""
        url = "https://tonapi.io/v2/rates"
        params = {
            "tokens": "ton",
            "currencies": "usd",
        }

        try:
            timeout = aiohttp.ClientTimeout(total=10.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            # TonAPI returns: {"rates": {"TON": {"prices": {"USD": 5.23}}}}
            rate = data.get("rates", {}).get("TON", {}).get("prices", {}).get("USD")
            if rate:
                self._rates["TON/USD"] = Decimal(str(rate))
                logger.debug("Updated TON/USD rate from TonAPI: %s", rate)
            else:
                logger.warning("TonAPI: Unexpected response format: %s", data)
        except (aiohttp.ClientError, Exception) as exc:
            logger.warning("TonAPI rates error: %s", exc)


# Singleton instance
price_converter = PriceConverter()
