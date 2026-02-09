"""Check if scanner is collecting prices for gifts."""

import asyncio
from datetime import datetime, timedelta
from app.core.database import async_session
from app.models.snapshot import MarketSnapshot
from sqlalchemy import select, func


async def main():
    async with async_session() as session:
        # Count total price records
        result = await session.execute(select(func.count()).select_from(MarketSnapshot))
        total = result.scalar()
        print(f"Total market snapshots: {total}\n")

        # Get recent prices (last 5 minutes)
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)
        result = await session.execute(
            select(
                MarketSnapshot.gift_slug,
                MarketSnapshot.source,
                MarketSnapshot.price_amount,
                MarketSnapshot.scanned_at
            )
            .where(MarketSnapshot.scanned_at >= five_min_ago)
            .order_by(MarketSnapshot.gift_slug, MarketSnapshot.source)
        )
        recent = result.all()

        if recent:
            print(f"Recent prices (last 5 min): {len(recent)}")
            current_slug = None
            for slug, source, price, scanned_at in recent:
                if slug != current_slug:
                    print(f"\n{slug}:")
                    current_slug = slug
                print(f"  - {source}: {price} TON (at {scanned_at.strftime('%H:%M:%S')})")
        else:
            print("No recent prices found (scanner might not be running)")

        # Show sample of all prices by source
        print("\n" + "="*60)
        print("Price count by source:")
        result = await session.execute(
            select(MarketSnapshot.source, func.count())
            .group_by(MarketSnapshot.source)
            .order_by(MarketSnapshot.source)
        )
        for source, count in result.all():
            print(f"  - {source}: {count} prices")


if __name__ == "__main__":
    asyncio.run(main())
