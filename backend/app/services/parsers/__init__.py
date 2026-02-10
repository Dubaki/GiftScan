"""
Parser registry — Multi-marketplace architecture.

Active parsers (5 marketplaces):
- Fragment: Official Telegram marketplace (HTML scraping)
- GetGems: Via TonAPI (Getgems Sales)
- MRKT: Via TonAPI (Marketapp Marketplace)
- Portals: Direct API (portals-market.com)
- Tonnel: Direct API (gifts2.tonnel.network)
"""

import logging

from app.services.parsers.base import BaseParser, GiftPrice
from app.services.parsers.fragment import FragmentParser
from app.services.parsers.tonapi_marketplace_parsers import (
    GetGemsParser,
    MRKTParser,
)
from app.services.parsers.portals_direct import PortalsDirectParser
from app.services.parsers.tonnel_direct import TonnelDirectParser

logger = logging.getLogger(__name__)

# Active parsers — 5 marketplaces
PARSER_REGISTRY: list[BaseParser] = [
    FragmentParser(),          # Fragment (official Telegram marketplace)
    GetGemsParser(),           # GetGems via TonAPI
    MRKTParser(),              # MRKT (Marketapp) via TonAPI
    PortalsDirectParser(),     # Portals via direct API
    TonnelDirectParser(),      # Tonnel via direct API
]

logger.info("Parser registry initialized: 5 marketplaces (Fragment, GetGems, MRKT, Portals, Tonnel)")

__all__ = ["PARSER_REGISTRY", "BaseParser", "GiftPrice"]
