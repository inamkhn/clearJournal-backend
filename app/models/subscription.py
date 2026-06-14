import enum
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column, TIMESTAMP


class SubscriptionStatus(str, enum.Enum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    CANCELED = "CANCELED"
    PAST_DUE = "PAST_DUE"


class SubscriptionBase(SQLModel):
    user_id: int = Field(foreign_key="users.id", index=True)
    price_id: Optional[int] = Field(default=None, foreign_key="prices.id", index=True)
    next_price_id: Optional[int] = Field(default=None, foreign_key="prices.id")
    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE)
    start_date: Optional[datetime] = Field(default=None)
    trial_end_date: Optional[datetime] = Field(default=None)
    current_period_start: Optional[datetime] = Field(default=None)
    current_period_end: Optional[datetime] = Field(default=None)
    cancel_at_period_end: bool = Field(default=False)
    canceled_at: Optional[datetime] = Field(default=None)
    ended_at: Optional[datetime] = Field(default=None)
    provider_customer_id: Optional[str] = Field(default=None, max_length=255)
    provider_subscription_id: Optional[str] = Field(default=None, max_length=255)
    provider_payment_method_id: Optional[str] = Field(default=None, max_length=255)
    discount_id: Optional[int] = Field(default=None)
    retry_count: int = Field(default=0, ge=0)
    last_retry_at: Optional[datetime] = Field(default=None)
    payment_provider: Optional[str] = Field(default=None, max_length=50)


class Subscription(SubscriptionBase, table=True):
    __tablename__ = "subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
