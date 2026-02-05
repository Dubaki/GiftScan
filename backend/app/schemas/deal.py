import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, model_validator


class CreateDealRequest(BaseModel):
    """
    Two scenarios from ESCROW_LOGIC.md:

    Sell (NFT → Crypto):
        initiator_tg_id, offer_gift_slug, required_asset_type="TON"|"JETTON",
        required_amount, required_token_contract (for JETTON)

    Swap (NFT → NFT):
        initiator_tg_id, offer_gift_slug, required_asset_type="NFT",
        required_asset_slug
    """

    initiator_tg_id: int
    offer_gift_slug: str

    required_asset_type: Literal["NFT", "TON", "JETTON"]

    # Sell fields
    required_amount: Decimal | None = None
    required_token_contract: str | None = None

    # Swap field
    required_asset_slug: str | None = None

    @model_validator(mode="after")
    def check_fields_by_type(self):
        if self.required_asset_type in ("TON", "JETTON"):
            if self.required_amount is None or self.required_amount <= 0:
                raise ValueError("required_amount must be > 0 for sell deals")
            if self.required_asset_type == "JETTON" and not self.required_token_contract:
                raise ValueError(
                    "required_token_contract is required for JETTON deals"
                )
        elif self.required_asset_type == "NFT":
            if not self.required_asset_slug:
                raise ValueError("required_asset_slug is required for swap deals")
        return self


class DealResponse(BaseModel):
    deal_id: uuid.UUID
    status: str
    created_at: datetime

    initiator_tg_id: int
    offer_gift_slug: str | None

    required_asset_type: str
    required_asset_slug: str | None = None
    required_amount: Decimal | None = None

    deposit_memo_code: str | None = None

    is_initiator_deposited: bool
    is_counterparty_deposited: bool

    model_config = {"from_attributes": True}


class DepositCheckResponse(BaseModel):
    deal_id: uuid.UUID
    side: str  # "initiator" | "counterparty"
    deposited: bool
    new_status: str
