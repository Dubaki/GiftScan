"""
Gift name normalization and mapping system.

Ensures that "Lollipop" on Fragment, "Lollipop NFT" on Portals,
and "Blue Star Gift" on GetGems all map to canonical slugs for comparison.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class GiftMapper:
    """
    Centralizes gift name normalization across all marketplaces.

    Handles:
    - Case normalization
    - Removal of common suffixes (NFT, Gift, etc.)
    - Special character handling
    - Manual overrides for edge cases
    """

    # Manual mapping overrides for problematic names
    MANUAL_OVERRIDES = {
        "bluestardeluxe": "bluestar",
        "redballoonnft": "redballoon",
        "greenclovernftgift": "greenclover",
        # Add more as needed
    }

    # Common patterns to remove
    REMOVE_PATTERNS = [
        r"\s*nft\s*",
        r"\s*gift\s*",
        r"\s*telegram\s*",
        r"#\d+",  # Serial numbers like #1234
        r"\(\d+\)",  # Numbers in parentheses
    ]

    @classmethod
    def normalize(cls, raw_name: str, source: str = "") -> str:
        """
        Normalize a gift name to canonical slug format.

        Args:
            raw_name: Raw gift name from marketplace
            source: Marketplace source (for debugging)

        Returns:
            Canonical slug (lowercase, no spaces, normalized)

        Examples:
            "Lollipop NFT" → "lollipop"
            "Blue Star #777" → "bluestar"
            "Delicious Cake (Gift)" → "deliciouscake"
        """
        if not raw_name:
            return ""

        original = raw_name
        normalized = raw_name.lower().strip()

        # Apply regex patterns
        for pattern in cls.REMOVE_PATTERNS:
            normalized = re.sub(pattern, " ", normalized, flags=re.IGNORECASE)

        # Remove special characters, keep alphanumeric and spaces
        normalized = re.sub(r"[^a-z0-9\s]", "", normalized)

        # Collapse multiple spaces
        normalized = re.sub(r"\s+", "", normalized)

        # Apply manual overrides
        if normalized in cls.MANUAL_OVERRIDES:
            normalized = cls.MANUAL_OVERRIDES[normalized]
            logger.debug(
                "GiftMapper: Applied override '%s' → '%s' (source: %s)",
                original,
                normalized,
                source,
            )

        if not normalized:
            logger.warning(
                "GiftMapper: Normalized to empty string from '%s' (source: %s)",
                original,
                source,
            )

        return normalized

    @classmethod
    def add_override(cls, variant: str, canonical: str):
        """
        Add a manual override for a gift name variant.

        Args:
            variant: The variant name (already normalized)
            canonical: The canonical slug it should map to
        """
        cls.MANUAL_OVERRIDES[variant] = canonical
        logger.info("GiftMapper: Added override '%s' → '%s'", variant, canonical)

    @classmethod
    def get_variants(cls, canonical: str) -> list[str]:
        """
        Get all known variants for a canonical slug.

        Returns:
            List of variant slugs that map to this canonical
        """
        variants = [canonical]
        for variant, target in cls.MANUAL_OVERRIDES.items():
            if target == canonical:
                variants.append(variant)
        return variants


# Singleton instance
gift_mapper = GiftMapper()


def normalize_gift_name(raw_name: str, source: str = "") -> str:
    """Convenience function for normalizing gift names."""
    return gift_mapper.normalize(raw_name, source)
