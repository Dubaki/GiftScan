"""
Arbitrage profit calculator.

Formula: Profit = (Sell_Price - Buy_Price) - Total_Fees

Handles:
- Currency conversion (Stars → TON)
- Fee calculation (marketplace + gas)
- Net profit estimation
- ROI calculation
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.services.arbitrage.converter import price_converter
from app.services.arbitrage.fees import fee_calculator

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageOpportunity:
    """Represents a profitable arbitrage trade."""

    slug: str  # Gift type
    buy_price: Decimal  # In TON
    buy_source: str
    buy_currency: str
    sell_price: Decimal  # In TON
    sell_source: str
    sell_currency: str

    gross_profit: Decimal  # Before fees
    total_fees: Decimal
    net_profit: Decimal  # After fees
    roi_percent: float  # Return on investment

    # Optional: for serial-specific arbitrage
    serial: Optional[int] = None


class ArbitrageCalculator:
    """
    Calculates arbitrage opportunities with profit estimation.

    Usage:
        calc = ArbitrageCalculator()
        opportunity = await calc.calculate_profit(
            buy_price=100, buy_source="GetGems", buy_currency="TON",
            sell_price=150, sell_source="Fragment", sell_currency="TON",
            slug="bluestar"
        )
    """

    async def calculate_profit(
        self,
        buy_price: Decimal,
        buy_source: str,
        buy_currency: str,
        sell_price: Decimal,
        sell_source: str,
        sell_currency: str,
        slug: str,
        serial: Optional[int] = None,
    ) -> Optional[ArbitrageOpportunity]:
        """
        Calculate net profit for an arbitrage trade.

        Args:
            buy_price: Purchase price
            buy_source: Where to buy
            buy_currency: Buy price currency
            sell_price: Sale price
            sell_source: Where to sell
            sell_currency: Sale price currency
            slug: Gift identifier
            serial: Optional NFT serial number

        Returns:
            ArbitrageOpportunity if profitable, else None
        """
        # Convert all prices to TON
        buy_price_ton = await price_converter.convert_to_ton(
            buy_price, buy_currency
        )
        sell_price_ton = await price_converter.convert_to_ton(
            sell_price, sell_currency
        )

        # Calculate fees
        total_fees = fee_calculator.calculate_total_fees(
            buy_price_ton, sell_price_ton, buy_source, sell_source
        )

        # Calculate profit
        gross_profit = sell_price_ton - buy_price_ton
        net_profit = gross_profit - total_fees

        # Calculate ROI
        if buy_price_ton > 0:
            roi_percent = float((net_profit / buy_price_ton) * 100)
        else:
            roi_percent = 0.0

        # Only return if profitable
        if net_profit <= 0:
            return None

        return ArbitrageOpportunity(
            slug=slug,
            buy_price=buy_price_ton,
            buy_source=buy_source,
            buy_currency=buy_currency,
            sell_price=sell_price_ton,
            sell_source=sell_source,
            sell_currency=sell_currency,
            gross_profit=gross_profit,
            total_fees=total_fees,
            net_profit=net_profit,
            roi_percent=roi_percent,
            serial=serial,
        )

    async def find_best_arbitrage(
        self,
        prices: list[tuple[Decimal, str, str]],  # (price, source, currency)
        slug: str,
        min_profit_ton: Decimal = Decimal("5"),
    ) -> Optional[ArbitrageOpportunity]:
        """
        Find the best arbitrage opportunity from a list of prices.

        Args:
            prices: List of (price, source, currency) tuples
            slug: Gift identifier
            min_profit_ton: Minimum required net profit

        Returns:
            Best profitable opportunity or None
        """
        if len(prices) < 2:
            return None

        best_opportunity = None
        best_net_profit = Decimal("0")

        # Try all buy/sell combinations
        for i, (buy_price, buy_source, buy_currency) in enumerate(prices):
            for sell_price, sell_source, sell_currency in prices[i + 1 :]:
                # Try both directions
                for bp, bs, bc, sp, ss, sc in [
                    (buy_price, buy_source, buy_currency, sell_price, sell_source, sell_currency),
                    (sell_price, sell_source, sell_currency, buy_price, buy_source, buy_currency),
                ]:
                    opp = await self.calculate_profit(
                        buy_price=bp,
                        buy_source=bs,
                        buy_currency=bc,
                        sell_price=sp,
                        sell_source=ss,
                        sell_currency=sc,
                        slug=slug,
                    )

                    if opp and opp.net_profit >= min_profit_ton:
                        if opp.net_profit > best_net_profit:
                            best_net_profit = opp.net_profit
                            best_opportunity = opp

        return best_opportunity


# Singleton instance
arbitrage_calculator = ArbitrageCalculator()
