"""
Map gift types to their collection addresses by querying TonAPI.
"""

import asyncio
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

import aiohttp
from app.services.parsers.tonapi_enhanced import TonAPIEnhancedParser, GIFT_COLLECTIONS
from app.services.rate_limiting import get_rate_limiter
from app.core.config import settings


async def main():
    print("\n" + "=" * 80)
    print("MAPPING GIFT TYPES TO COLLECTION ADDRESSES")
    print("=" * 80 + "\n")

    parser = TonAPIEnhancedParser()
    rate_limiter = get_rate_limiter("tonapi", max_requests=1, window_sec=1.0)

    # Map: collection_address -> list of gift names
    collection_to_gifts = defaultdict(set)

    print(f"Checking {len(GIFT_COLLECTIONS)} collections...\n")

    for i, collection_addr in enumerate(GIFT_COLLECTIONS, 1):
        print(f"[{i}/{len(GIFT_COLLECTIONS)}] Checking {collection_addr[:10]}...")

        url = f"https://tonapi.io/v2/nfts/collections/{collection_addr}/items"
        headers = {
            "Authorization": f"Bearer {settings.TONAPI_KEY}",
            "Content-Type": "application/json",
        }
        params = {"limit": 100, "offset": 0}  # Just need a few to identify

        async with rate_limiter.acquire("tonapi"):
            try:
                timeout = aiohttp.ClientTimeout(total=10.0)
                async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                    async with session.get(url, params=params) as resp:
                        resp.raise_for_status()
                        data = await resp.json()

                nft_items = data.get("nft_items", [])

                # Parse items to find gift types
                for item in nft_items:
                    listing = parser._parse_nft_item(item)
                    if listing:
                        collection_to_gifts[collection_addr].add(listing.gift_slug)

                gifts_in_collection = collection_to_gifts[collection_addr]
                if gifts_in_collection:
                    print(f"  → Found: {', '.join(sorted(gifts_in_collection))}")
                else:
                    print(f"  → No gifts found")

            except Exception as e:
                print(f"  → Error: {e}")

    # Print mapping
    print("\n" + "=" * 80)
    print("COLLECTION TO GIFT MAPPING:")
    print("=" * 80 + "\n")

    print("# Add this to notifications.py slug_to_collection mapping:\n")
    print("slug_to_collection = {")

    for collection_addr, gift_slugs in sorted(collection_to_gifts.items(), key=lambda x: -len(x[1])):
        gift_list = sorted(gift_slugs)
        print(f"    # Collection {collection_addr[:10]}... ({len(gift_list)} gifts)")
        for slug in gift_list:
            print(f'    "{slug}": "{collection_addr}",')
        print()

    print("}")

    print("\n" + "=" * 80)
    print(f"Total collections mapped: {len(collection_to_gifts)}")
    print(f"Total unique gifts: {sum(len(gifts) for gifts in collection_to_gifts.values())}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
