from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SubscriptionRead(BaseModel):
    id: int
    user_id: int
    price_id: int
    next_price_id: Optional[int] = None
    status: str
    start_date: datetime
    trial_end_date: Optional[datetime] = None
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    canceled_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    provider_customer_id: Optional[str] = None
    provider_subscription_id: Optional[str] = None
    provider_payment_method_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    payment_provider: Optional[str] = None
    account_limit: int = 5
