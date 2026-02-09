"""
Arbitrage orchestrator - coordinates TonAPI floor vs Fragment comparison.

Implements new logic from 123.md:
- Compare TonAPI floor (lowest across all marketplaces) with Fragment benchmark
- Calculate profit: Fragment_Price - TonAPI_Floor - (5% + 0.1 TON)
- Send Telegram alerts when profit > MIN_PROFIT_TON
"""

import logging
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass

from app.core.config import settings
from app.services.arbitrage import fee_calculator
from app.services.telegram_notifier import send_arbitrage_notification
from app.services.marketplace_links import generate_purchase_link

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageOpportunityV2:
    """Arbitrage opportunity (TonAPI floor vs Fragment)."""

    gift_name: str
    gift_slug: str
    serial_number: Optional[int]

    # TonAPI data (buy side)
    tonapi_floor_price: Decimal  # Lowest price from TonAPI
    tonapi_marketplace: str  # Source marketplace for floor
    nft_address: str  # NFT contract address

    # Fragment data (sell side)
    fragment_price: Decimal

    # Profit calculation
    gross_profit: Decimal  # Before fees
    total_fees: Decimal
    net_profit: Decimal  # After fees
    roi_percent: float


class ArbitrageOrchestrator:
    """
    Orchestrates arbitrage detection and notification.

    Workflow:
    1. Get TonAPI floor prices (lowest across all marketplaces)
    2. Get Fragment benchmark prices
    3. Calculate profit for each gift
    4. Send Telegram alerts for profitable opportunities
    """

    def __init__(self):
        self.min_profit_ton = Decimal(str(settings.MIN_PROFIT_TON))

    async def analyze_opportunity(
        self,
        gift_name: str,
        gift_slug: str,
        serial_number: Optional[int],
        tonapi_floor_price: Decimal,
        tonapi_marketplace: str,
        nft_address: str,
        fragment_price: Decimal,
    ) -> Optional[ArbitrageOpportunityV2]:
        """
        Analyze a single arbitrage opportunity.

        Args:
            gift_name: Gift name (e.g., "Milk Coffee")
            gift_slug: Normalized slug
            serial_number: NFT serial number
            tonapi_floor_price: Lowest price from TonAPI
            tonapi_marketplace: Marketplace with floor price
            nft_address: NFT contract address
            fragment_price: Fragment benchmark price

        Returns:
            ArbitrageOpportunityV2 if profitable, else None
        """
        # Calculate fees (buy + sell)
        # Buy from TonAPI marketplace: 5% + 0.1 TON
        buy_fees = fee_calculator.calculate_buy_fees(
            tonapi_floor_price, tonapi_marketplace
        )

        # Sell on Fragment: 5% + 0.1 TON
        sell_fees = fee_calculator.calculate_sell_fees(
            fragment_price, "Fragment"
        )

        total_fees = buy_fees + sell_fees

        # Calculate profit
        gross_profit = fragment_price - tonapi_floor_price
        net_profit = gross_profit - total_fees

        # Check if profitable
        if net_profit < self.min_profit_ton:
            return None

        # Calculate ROI
        if tonapi_floor_price > 0:
            roi_percent = float((net_profit / tonapi_floor_price) * 100)
        else:
            roi_percent = 0.0

        return ArbitrageOpportunityV2(
            gift_name=gift_name,
            gift_slug=gift_slug,
            serial_number=serial_number,
            tonapi_floor_price=tonapi_floor_price,
            tonapi_marketplace=tonapi_marketplace,
            nft_address=nft_address,
            fragment_price=fragment_price,
            gross_profit=gross_profit,
            total_fees=total_fees,
            net_profit=net_profit,
            roi_percent=roi_percent,
        )

    async def send_alert(self, opportunity: ArbitrageOpportunityV2):
        """
        Send Telegram alert for arbitrage opportunity.

        Args:
            opportunity: Detected arbitrage opportunity
        """
        # Generate purchase link
        buy_link = generate_purchase_link(
            nft_address=opportunity.nft_address,
            marketplace=opportunity.tonapi_marketplace,
            gift_slug=opportunity.gift_slug,
            serial=opportunity.serial_number,
        )

        # Send notification
        try:
            await send_arbitrage_notification(
                gift_name=opportunity.gift_name,
                serial_number=opportunity.serial_number,
                buy_price_ton=opportunity.tonapi_floor_price,
                buy_marketplace=opportunity.tonapi_marketplace,
                fragment_price_ton=opportunity.fragment_price,
                net_profit_ton=opportunity.net_profit,
                buy_link=buy_link,
            )

            logger.info(
                "Arbitrage alert sent: %s%s | Buy: %.2f TON (%s) → Sell: %.2f TON (Fragment) | Profit: %.2f TON",
                opportunity.gift_name,
                f" #{opportunity.serial_number}" if opportunity.serial_number else "",
                opportunity.tonapi_floor_price,
                opportunity.tonapi_marketplace,
                opportunity.fragment_price,
                opportunity.net_profit,
            )
        except Exception as e:
            logger.error("Failed to send arbitrage alert: %s", e)

    async def process_scan_results(
        self,
        tonapi_prices: dict,  # {slug: GiftPrice}
        fragment_prices: dict,  # {slug: GiftPrice}
    ):
        """
        Process scan results and detect arbitrage opportunities.

        Args:
            tonapi_prices: Floor prices from TonAPI (lowest per gift)
            fragment_prices: Benchmark prices from Fragment
        """
        opportunities_found = 0

        for slug, tonapi_gift_price in tonapi_prices.items():
            # Get corresponding Fragment price
            fragment_gift_price = fragment_prices.get(slug)

            if not fragment_gift_price:
                continue  # No Fragment benchmark available

            # Analyze opportunity
            opportunity = await self.analyze_opportunity(
                gift_name=tonapi_gift_price.raw_name or slug,
                gift_slug=slug,
                serial_number=tonapi_gift_price.serial,
                tonapi_floor_price=tonapi_gift_price.price,
                tonapi_marketplace=tonapi_gift_price.source.replace("TonAPI-", ""),
                nft_address=tonapi_gift_price.nft_address or "",
                fragment_price=fragment_gift_price.price,
            )

            if opportunity:
                # Send alert
                await self.send_alert(opportunity)
                opportunities_found += 1

        if opportunities_found > 0:
            logger.info(
                "Arbitrage scan complete: %d opportunities found (profit > %.1f TON)",
                opportunities_found,
                self.min_profit_ton,
            )
        else:
            logger.debug(
                "Arbitrage scan complete: No opportunities above %.1f TON threshold",
                self.min_profit_ton,
            )


# Singleton instance
arbitrage_orchestrator = ArbitrageOrchestrator()
