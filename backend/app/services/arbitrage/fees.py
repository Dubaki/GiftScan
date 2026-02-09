"""
Fee calculation for arbitrage profit estimation.

Includes:
- Marketplace fees (typically 2-3%)
- Royalty fees (typically 2-5%)
- Blockchain gas fees (~0.1 TON)
"""

import logging
from decimal import Decimal

from app.core.config import settings

logger = logging.getLogger(__name__)


class FeeCalculator:
    """Calculates total fees for buying and selling NFTs."""

    # Marketplace-specific fee structures (percent)
    MARKETPLACE_FEES = {
        "Fragment": Decimal("5.0"),  # 5% combined
        "GetGems": Decimal("5.0"),
        "Portals": Decimal("5.0"),
        "TonAPI": Decimal("5.0"),
        "MRKT": Decimal("5.0"),
        "TelegramMarket": Decimal("0"),  # Internal transfers may have different fees
    }

    def __init__(self):
        self.default_fee_percent = Decimal(str(settings.MARKETPLACE_FEE_PERCENT))
        self.gas_fee_ton = Decimal(str(settings.GAS_FEE_TON))

    def calculate_buy_fees(
        self, price: Decimal, source: str = "unknown"
    ) -> Decimal:
        """
        Calculate fees for buying an NFT.

        Args:
            price: Purchase price in TON
            source: Marketplace name

        Returns:
            Total fees in TON (marketplace fee + gas)
        """
        fee_percent = self.MARKETPLACE_FEES.get(
            source, self.default_fee_percent
        )

        marketplace_fee = price * (fee_percent / Decimal("100"))
        total_fee = marketplace_fee + self.gas_fee_ton

        return total_fee

    def calculate_sell_fees(
        self, price: Decimal, source: str = "unknown"
    ) -> Decimal:
        """
        Calculate fees for selling an NFT.

        Args:
            price: Sale price in TON
            source: Marketplace name

        Returns:
            Total fees in TON (marketplace fee + royalty + gas)
        """
        fee_percent = self.MARKETPLACE_FEES.get(
            source, self.default_fee_percent
        )

        marketplace_fee = price * (fee_percent / Decimal("100"))
        total_fee = marketplace_fee + self.gas_fee_ton

        return total_fee

    def calculate_total_fees(
        self,
        buy_price: Decimal,
        sell_price: Decimal,
        buy_source: str,
        sell_source: str,
    ) -> Decimal:
        """
        Calculate total fees for a complete arbitrage trade.

        Args:
            buy_price: Purchase price
            sell_price: Sale price
            buy_source: Where to buy
            sell_source: Where to sell

        Returns:
            Total fees in TON
        """
        buy_fees = self.calculate_buy_fees(buy_price, buy_source)
        sell_fees = self.calculate_sell_fees(sell_price, sell_source)

        return buy_fees + sell_fees

    def get_marketplace_fee_percent(self, source: str) -> Decimal:
        """Get fee percentage for a specific marketplace."""
        return self.MARKETPLACE_FEES.get(source, self.default_fee_percent)


# Singleton instance
fee_calculator = FeeCalculator()
