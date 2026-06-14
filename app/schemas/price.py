from datetime import datetime
from typing import Optional, Union
from decimal import Decimal
from pydantic import field_validator
from sqlmodel import SQLModel

from app.schemas.product import ProductRead


# ── Request Schemas ───────────────────────────────────────────────────────────

class PriceCreate(SQLModel):
    product_id: int
    price_amount: Union[float, Decimal]
    price_currency: str = "USD"
    product_period_days: int
    is_active: bool = True

    @field_validator("price_amount")
    @classmethod
    def price_amount_positive(cls, v: Union[float, Decimal]) -> Decimal:
        val = Decimal(str(v))
        if val <= 0:
            raise ValueError("Price amount must be greater than zero")
        return val

    @field_validator("price_currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return v.upper()

    @field_validator("product_period_days")
    @classmethod
    def period_days_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Product period days must be non-negative")
        return v


class PriceUpdate(SQLModel):
    price_amount: Optional[Union[float, Decimal]] = None
    price_currency: Optional[str] = None
    product_period_days: Optional[int] = None
    is_active: Optional[bool] = None
    paddle_price_id: Optional[str] = None

    @field_validator("price_amount")
    @classmethod
    def price_amount_positive(cls, v: Optional[Union[float, Decimal]]) -> Optional[Decimal]:
        if v is not None:
            val = Decimal(str(v))
            if val <= 0:
                raise ValueError("Price amount must be greater than zero")
            return val
        return v

    @field_validator("price_currency")
    @classmethod
    def currency_uppercase(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.upper()
        return v


# ── Response Schemas ──────────────────────────────────────────────────────────

class PriceRead(SQLModel):
    id: int
    product_id: int
    price_amount: Decimal
    price_currency: str
    product_period_days: int
    is_active: bool
    paddle_price_id: Optional[str] = None
    is_annual: bool
    is_monthly: bool
    created_at: datetime
    updated_at: datetime
    product: ProductRead
