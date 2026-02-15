from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB # Import JSONB

from app.models.base import Base


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    gift_slug: Mapped[str] = mapped_column(
        String(100), ForeignKey("gifts_catalog.slug")
    )
    source: Mapped[str] = mapped_column(String(50))  # Fragment, GetGems, ...
    price_amount: Mapped[Decimal] = mapped_column(Numeric)
    currency: Mapped[str] = mapped_column(String(10))  # TON, USDT
    serial_number: Mapped[int | None] = mapped_column(Integer, nullable=True) # New field
    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # New field for JSONB
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )

    __table_args__ = (
        Index("ix_snapshots_slug_time", "gift_slug", "scanned_at"),
    )
