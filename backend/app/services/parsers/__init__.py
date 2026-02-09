"""
Parser registry — Multi-marketplace architecture.

Active parsers (3 marketplaces):
- Fragment: Official Telegram marketplace (HTML scraping)
- GetGems: Via TonAPI (Getgems Sales)
- MRKT: Via TonAPI (Marketapp Marketplace)

Disabled (TonAPI doesn't index):
- Portals: Not supported by TonAPI
- Tonnel: Not supported by TonAPI
"""

import logging

from app.services.parsers.base import BaseParser, GiftPrice
from app.services.parsers.fragment import FragmentParser
from app.services.parsers.tonapi_marketplace_parsers import (
    GetGemsParser,
    MRKTParser,
    # PortalsParser,  # TonAPI doesn't index Portals
    # TonnelParser,   # TonAPI doesn't index Tonnel
)

logger = logging.getLogger(__name__)

# Active parsers — 3 marketplaces (Fragment + GetGems + MRKT)
PARSER_REGISTRY: list[BaseParser] = [
    FragmentParser(),    # Fragment (official Telegram marketplace)
    GetGemsParser(),     # GetGems via TonAPI
    MRKTParser(),        # MRKT (Marketapp) via TonAPI
]

logger.info("Parser registry initialized: 3 marketplaces (Fragment, GetGems, MRKT)")

__all__ = ["PARSER_REGISTRY", "BaseParser", "GiftPrice"]
