from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlmodel import SQLModel

from app.schemas.price import PriceRead


# ── Enums ─────────────────────────────────────────────────────────────────────

class SubscriptionStatusEnum:
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    CANCELED = "CANCELED"
    PAST_DUE = "PAST_DUE"


# ── Checkout ──────────────────────────────────────────────────────────────────

class CheckoutSessionRequest(SQLModel):
    price_id: int
    discount_amount: Optional[float] = None
    coupon_id: Optional[int] = None
    return_url: Optional[str] = None


class CheckoutSessionResponse(SQLModel):
    url: str
    transaction_id: str
    checkout_mode: str


# ── Change Subscription ───────────────────────────────────────────────────────

class ChangeSubscriptionRequest(SQLModel):
    price_id: int


# ── Subscription Read (user-facing) ───────────────────────────────────────────

class SubscriptionRead(SQLModel):
    id: int
    user_id: int
    price_id: Optional[int] = None
    next_price_id: Optional[int] = None
    status: str
    start_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    canceled_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    provider_customer_id: Optional[str] = None
    provider_subscription_id: Optional[str] = None
    provider_payment_method_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    retry_count: int
    last_retry_at: Optional[datetime] = None
    payment_provider: Optional[str] = None
    price: Optional[PriceRead] = None
    account_limit: int = 0


# ── Invoice ───────────────────────────────────────────────────────────────────

class InvoicePublic(SQLModel):
    id: int
    user_id: int
    price_id: int
    price: PriceRead
    charge_id: str
    amount: Decimal
    currency: str
    payment_method: Optional[str] = None
    billing_period_start: Optional[datetime] = None
    billing_period_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    pdf_s3_path: Optional[str] = None
    invoice_url: Optional[str] = None


# ── Admin Subscription ────────────────────────────────────────────────────────

class AdminSubscriptionRead(SQLModel):
    user_id: int
    full_name: str
    email: str
    subscription_id: int
    status: str
    start_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    next_pay_date: Optional[datetime] = None
    cancel_at_period_end: bool
    canceled_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    retry_count: int
    last_retry_at: Optional[datetime] = None
    created_at: datetime
    plan: Optional[str] = None
    price_amount: Optional[Decimal] = None
    price_currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    account_limit: Optional[int] = None


class SubscriptionCounts(SQLModel):
    ACTIVE: int = 0
    TRIAL: int = 0
    INACTIVE: int = 0
    CANCELED: int = 0
    PAST_DUE: int = 0


class AdminSubscriptionResponse(SQLModel):
    counts: SubscriptionCounts
    items: List[AdminSubscriptionRead]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool
    next_page: Optional[int] = None
    prev_page: Optional[int] = None
