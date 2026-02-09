"""
Test new collections to see which gift types we get.
"""

import asyncio
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))

from app.services.parsers.tonapi_enhanced import TonAPIEnhancedParser


async def main():
    print("Testing new 14 collections from GetGems...\n")
    print("=" * 80)

    parser = TonAPIEnhancedParser()
    listings = await parser._fetch_nft_listings()

    print(f"\nTotal listings found: {len(listings)}")
    print(f"Total collections scanned: 14\n")

    # Count by gift type
    gift_counts = Counter()
    for listing in listings:
        gift_counts[listing.gift_name] += 1

    print("=" * 80)
    print("DISCOVERED GIFT TYPES (sorted by volume):\n")
    print(f"{'Gift Type':<30} {'Listings':<10} {'Example Price':<15}")
    print("-" * 80)

    # Get example prices
    gift_examples = {}
    for listing in listings:
        if listing.gift_name not in gift_examples:
            gift_examples[listing.gift_name] = listing.price_ton

    for gift_name, count in gift_counts.most_common():
        example_price = gift_examples.get(gift_name, 0)
        print(f"{gift_name:<30} {count:<10} {example_price:.1f} TON")

    print("\n" + "=" * 80)
    print(f"SUMMARY: Found {len(gift_counts)} unique gift types")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
