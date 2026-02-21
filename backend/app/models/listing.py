from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GiftListing(Base):
    """
    Tracks every currently-listed NFT from TonAPI.

    One row per nft_address, upserted each scan.
    When an NFT disappears from listings it gets sold_at set and a GiftSale
    row is created.
    """

    __tablename__ = "gift_listings"

    nft_address: Mapped[str] = mapped_column(String(100), primary_key=True)
    gift_slug: Mapped[str] = mapped_column(
        String(100), ForeignKey("gifts_catalog.slug"), index=True
    )
    serial_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rarity_tier: Mapped[str] = mapped_column(String(20))
    price_ton: Mapped[Decimal] = mapped_column(Numeric)
    marketplace: Mapped[str] = mapped_column(String(50))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_gift_listings_sold_at", "sold_at"),
    )
