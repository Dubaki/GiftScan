"""
MRKT marketplace parser (stub).

API: https://api.tgmrkt.io/api/v1
Auth: POST /auth with Telegram initData → bearer token.
Listings: POST /gifts/saling with collectionNames, ordering, count.

TODO: Implement when auth token is available.
"""

import logging
from typing import Optional

from app.services.parsers.base import BaseParser, GiftPrice

logger = logging.getLogger(__name__)


class MRKTParser(BaseParser):
    source_name = "MRKT"
    supports_bulk = False

    async def fetch_gift_price(self, slug: str) -> Optional[GiftPrice]:
        # Requires auth token — not implemented yet
        return None
