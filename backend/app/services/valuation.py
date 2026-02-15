import logging
from decimal import Decimal
from typing import Optional, Dict, Any

from app.models.gift import GiftCatalog
from app.models.snapshot import MarketSnapshot

logger = logging.getLogger(__name__)


class GiftValuation:
    """
    Service for calculating rarity and value scores for gifts based on their attributes.
    """

    async def calculate_value_score(
        self,
        gift_slug: str,
        gift_name: str,
        current_price: Decimal,
        serial_number: Optional[int],
        attributes: Optional[Dict[str, Any]]
    ) -> tuple[Decimal, int]: # Return a tuple
        """
        Calculates a value score for a given gift based on its attributes and serial number.
        Returns (score, premium_indicators_count).
        """
        score = Decimal('0.0')
        total_premium_indicators_count = 0

        # 1. Serial Number Valuation
        if serial_number is not None:
            serial_premium, serial_premium_count = self._evaluate_serial_number(serial_number, current_price)
            score += serial_premium
            total_premium_indicators_count += serial_premium_count

        # 2. Attribute Valuation (Rare models, Crafting potential)
        if attributes:
            attribute_premium, attribute_premium_count = self._evaluate_attributes(gift_slug, attributes, current_price)
            score += attribute_premium
            total_premium_indicators_count += attribute_premium_count

        return score, total_premium_indicators_count

    def _evaluate_serial_number(self, serial: int, base_price: Decimal) -> Decimal:
        """
        Evaluates the premium for specific serial numbers.
        User's strategy: "numbers below #1000 or 'beautiful' combinations (#777, #1234, #5555) add 15-30% to the floor price."
        """
        premium_percentage = Decimal('0.0')
        premium_indicators_count = 0

        if serial < 1000:
            premium_percentage += Decimal('0.20')  # 20% premium for low serials
            premium_indicators_count += 1
        elif serial in [777, 1234, 5555, 6969, 420]: # Example beautiful numbers
            premium_percentage += Decimal('0.15') # 15% premium for beautiful numbers
            premium_indicators_count += 1

        # Add logic for other "beautiful" numbers based on common NFT community perception
        # This can be expanded with more patterns or a lookup table

        return base_price * premium_percentage, premium_indicators_count

    def _evaluate_attributes(self, gift_slug: str, attributes: Dict[str, Any], base_price: Decimal) -> Decimal:
        """
        Evaluates the premium for rare attributes (rare models, crafting potential).
        This will require more sophisticated logic, potentially querying historical data
        to determine attribute rarity and impact on price.
        For now, this is a placeholder.
        """
        premium_percentage = Decimal('0.0')
        premium_indicators_count = 0 # Track how many attributes trigger a premium

        # User specified: "Black Backdrop" as a priority
        if attributes.get("Backdrop") == "Black":
            premium_percentage += Decimal('0.50') # Significant premium for black backdrop (e.g., 50%)
            premium_indicators_count += 1
            logger.info(f"Valuation: Detected 'Black Backdrop' for {gift_slug}. Adding significant premium.")


        # Example: "Swiss Watches" specific traits
        if gift_slug.startswith("swiss-watches"):
            if attributes.get("Material") == "Golden":
                premium_percentage += Decimal('0.30')
                premium_indicators_count += 1
            if attributes.get("Gemstone") == "Diamond":
                premium_percentage += Decimal('0.40')
                premium_indicators_count += 1

        # Example: "Backdrop" for crafting potential (other rare backdrops)
        if "Backdrop" in attributes and attributes["Backdrop"] != "Black": # Avoid double counting if black
            if attributes["Backdrop"] in ["Rare Nebula", "Cosmic Dust", "Obsidian", "Midnight"]:
                premium_percentage += Decimal('0.25')
                premium_indicators_count += 1

        # This logic needs to be dynamic and data-driven eventually.
        # It should consider rarity distribution of attributes within a collection.

        return base_price * premium_percentage, premium_indicators_count


# Singleton instance
gift_valuation = GiftValuation()