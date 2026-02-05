import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.deal import CreateDealRequest, DealResponse, DepositCheckResponse
from app.services.escrow import check_deposit, create_deal, get_deal

router = APIRouter(prefix="/deals", tags=["deals"])


@router.post("/create", response_model=DealResponse, status_code=201)
async def create_deal_endpoint(
    body: CreateDealRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new 1-to-1 escrow deal.

    Sell example:  { initiator_tg_id: 123, offer_gift_slug: "plushpepe",
                     required_asset_type: "TON", required_amount: 100 }

    Swap example:  { initiator_tg_id: 123, offer_gift_slug: "plushpepe",
                     required_asset_type: "NFT", required_asset_slug: "swisswatch" }
    """
    deal = await create_deal(session, body)
    return DealResponse.model_validate(deal)


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal_endpoint(
    deal_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get deal details by ID (the shareable deal link)."""
    deal = await get_deal(session, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")
    return DealResponse.model_validate(deal)


@router.post("/{deal_id}/check-deposit", response_model=DepositCheckResponse)
async def check_deposit_endpoint(
    deal_id: uuid.UUID,
    side: Literal["initiator", "counterparty"] = "initiator",
    session: AsyncSession = Depends(get_session),
):
    """
    MOCK: Simulate deposit verification.

    Marks the deposit flag as True and advances the deal status.
    Will be replaced with real TON blockchain monitoring later.
    """
    try:
        deal = await check_deposit(session, deal_id, side)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    deposited = (
        deal.is_initiator_deposited
        if side == "initiator"
        else deal.is_counterparty_deposited
    )
    return DepositCheckResponse(
        deal_id=deal.deal_id,
        side=side,
        deposited=deposited,
        new_status=deal.status,
    )
