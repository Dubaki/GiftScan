from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB # Import JSONB

from app.models.base import Base


class GiftCatalog(Base):
    __tablename__ = "gifts_catalog"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    image_url: Mapped[str | None] = mapped_column(String(255))
    total_supply: Mapped[int | None] = mapped_column(Integer)
    serial_number: Mapped[int | None] = mapped_column(Integer, nullable=True) # New field
    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # New field for JSONB
