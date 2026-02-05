from decimal import Decimal

from pydantic import BaseModel


class GiftOut(BaseModel):
    slug: str
    name: str
    image_url: str | None = None
    total_supply: int | None = None
    floor_price: Decimal | None = None
    currency: str | None = None

    model_config = {"from_attributes": True}
