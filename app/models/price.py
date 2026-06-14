from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Column, TIMESTAMP, Relationship
from decimal import Decimal

if TYPE_CHECKING:
    from app.models.product import Product


class PriceBase(SQLModel):
    product_id: int = Field(foreign_key="products.id", index=True)
    price_amount: Decimal = Field(max_digits=10, decimal_places=2)
    price_currency: str = Field(default="USD", max_length=3)
    product_period_days: int = Field(default=30, ge=0)
    is_active: bool = Field(default=True)
    paddle_price_id: Optional[str] = Field(default=None, max_length=255)
    is_annual: bool = Field(default=False)
    is_monthly: bool = Field(default=False)


class Price(PriceBase, table=True):
    __tablename__ = "prices"

    id: Optional[int] = Field(default=None, primary_key=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Relationships
    product: Optional["Product"] = Relationship(back_populates="prices")
