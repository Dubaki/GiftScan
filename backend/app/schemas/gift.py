"""
Gift response schemas for multi-marketplace price display.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class MarketplacePrice(BaseModel):
    """Price from a single marketplace."""

    source: str
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    updated_at: Optional[datetime] = None


class PriceSummary(BaseModel):
    """Best/worst price summary."""

    source: str
    price: Decimal
    currency: str = "TON"


class GiftOut(BaseModel):
    """Gift with prices from all marketplaces."""

    slug: str
    name: str
    image_url: Optional[str] = None
    total_supply: Optional[int] = None

    # Multi-source prices
    prices: list[MarketplacePrice] = Field(default_factory=list)

    # Computed fields
    best_price: Optional[PriceSummary] = None
    worst_price: Optional[PriceSummary] = None
    spread_ton: Optional[Decimal] = None
    spread_pct: Optional[float] = None
    arbitrage_signal: bool = False

    model_config = {"from_attributes": True}


class GiftListMeta(BaseModel):
    """Metadata for gift list response."""

    total: int
    scan_timestamp: Optional[datetime] = None
    sources: list[str] = Field(default_factory=list)


class GiftListResponse(BaseModel):
    """Full response for gift list endpoint."""

    gifts: list[GiftOut]
    meta: GiftListMeta


# Legacy schema for backward compatibility
class GiftOutLegacy(BaseModel):
    """Legacy single-price schema (deprecated)."""

    slug: str
    name: str
    image_url: Optional[str] = None
    total_supply: Optional[int] = None
    floor_price: Optional[Decimal] = None
    currency: Optional[str] = None

    model_config = {"from_attributes": True}
