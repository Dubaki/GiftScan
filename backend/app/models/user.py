from datetime import datetime

from sqlalchemy import BigInteger, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(100))
    wallet_address: Mapped[str | None] = mapped_column(String(100))
    subscription_level: Mapped[str] = mapped_column(
        String(20), default="free", server_default="free"
    )
    sub_expiry_date: Mapped[datetime | None] = mapped_column(DateTime)
