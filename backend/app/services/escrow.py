"""
Escrow service — deal creation and deposit verification.

Flows (from ESCROW_LOGIC.md):
  Sell:  created → waiting_deposit → processing → completed
  Swap:  created → waiting_deposit → processing → completed

Status transitions:
  created          — deal record exists, waiting for initiator deposit
  waiting_deposit  — initiator deposited, waiting for counterparty
  processing       — both sides deposited, executing swap/transfer
  completed        — assets exchanged
  cancelled        — deal aborted
"""

import logging
import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.deal import Deal
from app.schemas.deal import CreateDealRequest

logger = logging.getLogger(__name__)


def _generate_memo() -> str:
    """Short unique memo code for tracking incoming transactions."""
    return f"GS-{uuid.uuid4().hex[:12].upper()}"


async def create_deal(session: AsyncSession, req: CreateDealRequest) -> Deal:
    """
    Create a new 1-to-1 escrow deal.
    Initiator always offers an NFT (gift).
    """
    deal = Deal(
        status="created",
        # Side A
        initiator_tg_id=req.initiator_tg_id,
        initiator_offer_type="NFT",
        initiator_offer_slug=req.offer_gift_slug,
        # Side B
        required_asset_type=req.required_asset_type,
        required_asset_slug=req.required_asset_slug,
        required_token_contract=req.required_token_contract,
        required_amount=req.required_amount,
        # Escrow tracking
        service_wallet_address=settings.SERVICE_WALLET_ADDRESS or None,
        deposit_memo_code=_generate_memo(),
    )

    session.add(deal)
    await session.commit()
    await session.refresh(deal)

    logger.info("Deal created: %s (type=%s)", deal.deal_id, req.required_asset_type)
    return deal


async def get_deal(session: AsyncSession, deal_id: uuid.UUID) -> Deal | None:
    result = await session.execute(select(Deal).where(Deal.deal_id == deal_id))
    return result.scalar_one_or_none()


async def check_deposit(
    session: AsyncSession,
    deal_id: uuid.UUID,
    side: Literal["initiator", "counterparty"],
) -> Deal:
    """
    MOCK — pretend we verified the deposit on-chain.

    In production this will query the TON blockchain for incoming
    transactions matching the deal's deposit_memo_code.

    Status machine:
      - initiator deposits  → status becomes 'waiting_deposit'
      - counterparty deposits → status becomes 'processing'
      - both deposited → status becomes 'completed' (auto-finalize mock)
    """
    deal = await get_deal(session, deal_id)
    if deal is None:
        raise ValueError(f"Deal {deal_id} not found")

    if deal.status in ("completed", "cancelled"):
        raise ValueError(f"Deal {deal_id} is already {deal.status}")

    if side == "initiator":
        deal.is_initiator_deposited = True
        logger.info("Deal %s: initiator deposit confirmed (mock)", deal_id)
    else:
        deal.is_counterparty_deposited = True
        logger.info("Deal %s: counterparty deposit confirmed (mock)", deal_id)

    # Advance status
    if deal.is_initiator_deposited and deal.is_counterparty_deposited:
        deal.status = "completed"
    elif deal.is_initiator_deposited:
        deal.status = "waiting_deposit"
    elif deal.is_counterparty_deposited:
        deal.status = "processing"

    deal.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(deal)
    return deal
