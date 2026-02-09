"""
Discover new gift types from TonAPI that aren't in our catalog yet.
"""

import asyncio
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.core.database import async_session
from app.models.gift import GiftCatalog
from app.services.parsers.tonapi_enhanced import TonAPIEnhancedParser


async def main():
    print("\n" + "=" * 80)
    print("DISCOVERING NEW GIFT TYPES FROM TONAPI")
    print("=" * 80 + "\n")

    # Get existing gifts from catalog
    async with async_session() as session:
        result = await session.execute(select(GiftCatalog.slug, GiftCatalog.name))
        existing_gifts = {row.slug: row.name for row in result}

    print(f"Existing gifts in catalog: {len(existing_gifts)}\n")

    # Fetch from TonAPI
    parser = TonAPIEnhancedParser()
    print("Fetching from TonAPI (14 collections)...\n")
    listings = await parser._fetch_nft_listings()

    print(f"Total listings found: {len(listings)}")
    print(f"On sale: {sum(1 for l in listings if l.price_ton > 0)}\n")

    # Count by gift name
    gift_counts = Counter()
    gift_slugs = {}
    gift_examples = {}

    for listing in listings:
        gift_counts[listing.gift_name] += 1
        gift_slugs[listing.gift_name] = listing.gift_slug

        if listing.gift_name not in gift_examples and listing.price_ton > 0:
            gift_examples[listing.gift_name] = listing.price_ton

    print("=" * 80)
    print("ALL GIFT TYPES FOUND (sorted by volume):\n")
    print(f"{'Gift Name':<30} {'Slug':<20} {'Listings':<10} {'In Catalog?':<15} {'Price Example'}")
    print("-" * 80)

    new_gifts = []

    for gift_name, count in gift_counts.most_common():
        slug = gift_slugs[gift_name]
        in_catalog = "YES" if slug in existing_gifts else "NO (NEW!)"
        example_price = gift_examples.get(gift_name, 0)
        price_str = f"{example_price:.1f} TON" if example_price > 0 else "N/A"

        print(f"{gift_name:<30} {slug:<20} {count:<10} {in_catalog:<15} {price_str}")

        if slug not in existing_gifts:
            new_gifts.append((gift_name, slug, count))

    print("\n" + "=" * 80)
    print(f"SUMMARY:")
    print(f"  Total gift types found: {len(gift_counts)}")
    print(f"  Already in catalog: {sum(1 for slug in gift_slugs.values() if slug in existing_gifts)}")
    print(f"  NEW types to add: {len(new_gifts)}")
    print("=" * 80)

    if new_gifts:
        print("\nNEW GIFT TYPES TO ADD TO CATALOG:\n")
        for gift_name, slug, count in sorted(new_gifts, key=lambda x: x[2], reverse=True):
            print(f"  - {gift_name:30} ({slug:20}) - {count:4} listings")

    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
