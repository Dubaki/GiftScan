"""
Parser registry — lists all active marketplace parsers.

To add a new parser:
1. Create parser class inheriting from BaseParser
2. Add instance to PARSER_REGISTRY below
"""

from app.services.parsers.base import BaseParser, GiftPrice
from app.services.parsers.fragment import FragmentParser
from app.services.parsers.th3ryks_market import Th3ryksMarketParser # New import

# Active parsers — these will be used by the scanner
PARSER_REGISTRY: list[BaseParser] = [
    FragmentParser(),
    Th3ryksMarketParser(market_name="portals"),
    Th3ryksMarketParser(market_name="mrkt"),
    Th3ryksMarketParser(market_name="getgems"),
    Th3ryksMarketParser(market_name="tonnel"),
]

__all__ = ["PARSER_REGISTRY", "BaseParser", "GiftPrice"]
