import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, Numeric, String, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Deal(Base):
    __tablename__ = "deals"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()", onupdate=datetime.utcnow
    )
    status: Mapped[str] = mapped_column(String(20), default="created")

    # Side A — initiator
    initiator_tg_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.tg_id")
    )
    initiator_offer_type: Mapped[str] = mapped_column(String(10))  # NFT
    initiator_offer_slug: Mapped[str | None] = mapped_column(String(100))
    initiator_wallet: Mapped[str | None] = mapped_column(String(100))

    # Side B — what we want in return
    required_asset_type: Mapped[str] = mapped_column(String(10))  # NFT, TON, JETTON
    required_asset_slug: Mapped[str | None] = mapped_column(String(100))
    required_token_contract: Mapped[str | None] = mapped_column(String(100))
    required_amount: Mapped[Decimal | None] = mapped_column(Numeric)

    # Escrow tracking
    service_wallet_address: Mapped[str | None] = mapped_column(String(100))
    deposit_memo_code: Mapped[str | None] = mapped_column(String(50), unique=True)

    # Deposit flags
    is_initiator_deposited: Mapped[bool] = mapped_column(Boolean, default=False)
    is_counterparty_deposited: Mapped[bool] = mapped_column(Boolean, default=False)
