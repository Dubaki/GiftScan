"""Quick script to check catalog contents."""

import asyncio
from app.core.database import async_session
from app.models.gift import GiftCatalog
from sqlalchemy import select, func


async def main():
    async with async_session() as session:
        # Count total gifts
        result = await session.execute(select(func.count()).select_from(GiftCatalog))
        total = result.scalar()
        print(f"Total gifts in catalog: {total}\n")

        # List all gifts
        result = await session.execute(
            select(GiftCatalog.name, GiftCatalog.slug).order_by(GiftCatalog.name)
        )
        gifts = result.all()

        print("All gifts:")
        for name, slug in gifts:
            print(f"  - {name} ({slug})")


if __name__ == "__main__":
    asyncio.run(main())
