from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GiftSale(Base):
    """
    Records actual completed NFT gift sales.

    Populated by SalesTracker which compares consecutive scan results:
    NFT addresses present in scan N but absent in scan N+1 are likely sold.
    """

    __tablename__ = "gift_sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    gift_slug: Mapped[str] = mapped_column(
        String(100), ForeignKey("gifts_catalog.slug"), index=True
    )
    nft_address: Mapped[str] = mapped_column(String(100), index=True)
    serial_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rarity_tier: Mapped[str] = mapped_column(String(20))  # ultra_rare/rare/uncommon/common
    sale_price_ton: Mapped[Decimal] = mapped_column(Numeric)
    marketplace: Mapped[str] = mapped_column(String(50))
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )

    __table_args__ = (
        Index("ix_gift_sales_slug_tier_time", "gift_slug", "rarity_tier", "detected_at"),
    )
