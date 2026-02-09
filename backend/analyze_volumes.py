"""
Analyze gift sales volume across marketplaces.

Shows top 20 gifts by:
- Number of listings on TonAPI
- Price volatility (activity indicator)
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from collections import Counter

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, func
from app.core.database import async_session
from app.models.gift import GiftCatalog
from app.models.snapshot import MarketSnapshot
from app.services.parsers.tonapi_enhanced import TonAPIEnhancedParser


async def analyze_tonapi_volume():
    """Analyze current TonAPI listings to find most active gifts."""
    print("=" * 80)
    print("TonAPI Listings Analysis (Current Market)")
    print("=" * 80)

    parser = TonAPIEnhancedParser()
    listings = await parser._fetch_nft_listings()

    # Count listings per gift
    gift_counts = Counter()
    gift_prices = {}  # Track price ranges

    for listing in listings:
        slug = listing.gift_slug
        gift_counts[slug] += 1

        if slug not in gift_prices:
            gift_prices[slug] = {"min": listing.price_ton, "max": listing.price_ton, "prices": []}

        gift_prices[slug]["prices"].append(listing.price_ton)
        gift_prices[slug]["min"] = min(gift_prices[slug]["min"], listing.price_ton)
        gift_prices[slug]["max"] = max(gift_prices[slug]["max"], listing.price_ton)

    print(f"\nTotal listings on sale: {len(listings)}")
    print(f"Unique gifts: {len(gift_counts)}\n")

    # Sort by volume
    top_gifts = gift_counts.most_common(20)

    print("TOP 20 Gifts by Listing Volume:\n")
    print(f"{'Rank':<6} {'Gift':<20} {'Listings':<10} {'Price Range (TON)':<25} {'Spread':<10}")
    print("-" * 80)

    for rank, (slug, count) in enumerate(top_gifts, 1):
        prices = gift_prices[slug]
        min_price = prices["min"]
        max_price = prices["max"]
        spread = max_price - min_price
        spread_pct = (spread / min_price * 100) if min_price > 0 else 0

        price_range = f"{min_price:.1f} - {max_price:.1f}"
        spread_str = f"{spread:.1f} ({spread_pct:.1f}%)"

        print(f"{rank:<6} {slug:<20} {count:<10} {price_range:<25} {spread_str:<10}")

    return top_gifts


async def analyze_db_activity():
    """Analyze historical database activity."""
    print("\n" + "=" * 80)
    print("Database Activity Analysis (Historical)")
    print("=" * 80)

    async with async_session() as session:
        # Get gift names
        catalog_stmt = select(GiftCatalog.slug, GiftCatalog.name)
        result = await session.execute(catalog_stmt)
        gift_names = {row.slug: row.name for row in result}

        # Count snapshots per gift (activity indicator)
        activity_stmt = (
            select(
                MarketSnapshot.gift_slug,
                func.count(MarketSnapshot.id).label("snapshot_count"),
                func.count(func.distinct(MarketSnapshot.source)).label("marketplace_count"),
                func.avg(MarketSnapshot.price_amount).label("avg_price"),
            )
            .group_by(MarketSnapshot.gift_slug)
            .order_by(func.count(MarketSnapshot.id).desc())
            .limit(20)
        )

        result = await session.execute(activity_stmt)
        rows = result.all()

        print(f"\nTOP 20 Gifts by DB Activity:\n")
        print(f"{'Rank':<6} {'Gift':<20} {'Snapshots':<12} {'Markets':<10} {'Avg Price':<12}")
        print("-" * 80)

        for rank, row in enumerate(rows, 1):
            name = gift_names.get(row.gift_slug, row.gift_slug)
            avg_price = float(row.avg_price) if row.avg_price else 0

            print(f"{rank:<6} {name:<20} {row.snapshot_count:<12} {row.marketplace_count:<10} {avg_price:<12.1f}")


async def main():
    print("\nGiftScan Volume Analysis\n")

    # Analyze current TonAPI listings
    top_gifts = await analyze_tonapi_volume()

    # Analyze historical DB activity
    await analyze_db_activity()

    # Summary
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("\nTop 5 gifts to prioritize for scanning:")
    for rank, (slug, count) in enumerate(top_gifts[:5], 1):
        print(f"  {rank}. {slug:20} ({count} listings)")

    print("\nCurrent scanner already covers all gifts in catalog.")
    print("High-volume gifts are automatically included in scans.")
    print("\nTo add new gift collections, update GIFT_COLLECTIONS in tonapi_enhanced.py")


if __name__ == "__main__":
    asyncio.run(main())
