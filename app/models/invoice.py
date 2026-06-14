from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column, TIMESTAMP
from decimal import Decimal


class InvoiceBase(SQLModel):
    user_id: int = Field(foreign_key="users.id", index=True)
    price_id: int = Field(foreign_key="prices.id", index=True)
    charge_id: str = Field(max_length=255)
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)
    payment_method: Optional[str] = Field(default=None, max_length=100)
    billing_period_start: Optional[datetime] = Field(default=None)
    billing_period_end: Optional[datetime] = Field(default=None)
    pdf_s3_path: Optional[str] = Field(default=None, max_length=500)


class Invoice(InvoiceBase, table=True):
    __tablename__ = "invoices"

    id: Optional[int] = Field(default=None, primary_key=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
