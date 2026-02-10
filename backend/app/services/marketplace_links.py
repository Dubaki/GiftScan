"""
Marketplace link generator for NFT purchases.

Generates direct links to buy NFTs on various marketplaces.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MarketplaceLinkGenerator:
    """Generates purchase links for different marketplaces."""

    # Base URLs for marketplaces
    GETGEMS_BASE = "https://getgems.io/nft"
    PORTALS_BASE = "https://portal-market.com/nft"
    TONDIAMONDS_BASE = "https://ton.diamonds/nft"
    TONNEL_BASE = "https://market.tonnel.network"
    FRAGMENT_BASE = "https://fragment.com/gift"

    @classmethod
    def generate_link(
        cls,
        nft_address: str,
        marketplace: str,
        gift_slug: Optional[str] = None,
        serial: Optional[int] = None,
    ) -> str:
        """
        Generate purchase link for an NFT.

        Args:
            nft_address: NFT contract address
            marketplace: Marketplace name (GetGems, Portals, etc.)
            gift_slug: Gift slug (for Fragment)
            serial: Serial number (for Fragment)

        Returns:
            Direct purchase link
        """
        marketplace = marketplace.lower()

        if "getgems" in marketplace:
            return cls._getgems_link(nft_address)
        elif "portals" in marketplace or "portal" in marketplace:
            return cls._portals_link(nft_address)
        elif "tonnel" in marketplace:
            return cls._tonnel_link(nft_address)
        elif "fragment" in marketplace:
            return cls._fragment_link(gift_slug, serial)
        elif "ton" in marketplace or "diamonds" in marketplace:
            return cls._tondiamonds_link(nft_address)
        else:
            # Fallback: try GetGems
            logger.warning(
                "Unknown marketplace '%s', defaulting to GetGems link",
                marketplace,
            )
            return cls._getgems_link(nft_address)

    @classmethod
    def _getgems_link(cls, nft_address: str) -> str:
        """Generate GetGems NFT link."""
        return f"{cls.GETGEMS_BASE}/{nft_address}"

    @classmethod
    def _portals_link(cls, nft_address: str) -> str:
        """Generate Portals NFT link."""
        return f"{cls.PORTALS_BASE}/{nft_address}"

    @classmethod
    def _tonnel_link(cls, nft_address: str) -> str:
        """Generate Tonnel marketplace NFT link."""
        return f"{cls.TONNEL_BASE}/gift/{nft_address}"

    @classmethod
    def _tondiamonds_link(cls, nft_address: str) -> str:
        """Generate TON Diamonds NFT link."""
        return f"{cls.TONDIAMONDS_BASE}/{nft_address}"

    @classmethod
    def _fragment_link(
        cls, gift_slug: Optional[str], serial: Optional[int]
    ) -> str:
        """Generate Fragment gift link."""
        if gift_slug and serial:
            return f"{cls.FRAGMENT_BASE}/{gift_slug}-{serial}"
        elif gift_slug:
            return f"{cls.FRAGMENT_BASE}s/{gift_slug}"
        else:
            return cls.FRAGMENT_BASE

    @classmethod
    def generate_multiple_links(
        cls,
        nft_address: str,
        marketplaces: list[str],
        gift_slug: Optional[str] = None,
        serial: Optional[int] = None,
    ) -> dict[str, str]:
        """
        Generate links for multiple marketplaces.

        Args:
            nft_address: NFT address
            marketplaces: List of marketplace names
            gift_slug: Gift slug
            serial: Serial number

        Returns:
            Dict of {marketplace: link}
        """
        links = {}
        for marketplace in marketplaces:
            link = cls.generate_link(
                nft_address=nft_address,
                marketplace=marketplace,
                gift_slug=gift_slug,
                serial=serial,
            )
            links[marketplace] = link

        return links


# Singleton
link_generator = MarketplaceLinkGenerator()


def generate_purchase_link(
    nft_address: str,
    marketplace: str,
    gift_slug: Optional[str] = None,
    serial: Optional[int] = None,
) -> str:
    """
    Convenience function to generate purchase link.

    Args:
        nft_address: NFT contract address
        marketplace: Marketplace name
        gift_slug: Gift slug (optional)
        serial: Serial number (optional)

    Returns:
        Direct purchase link
    """
    return link_generator.generate_link(
        nft_address=nft_address,
        marketplace=marketplace,
        gift_slug=gift_slug,
        serial=serial,
    )
