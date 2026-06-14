from datetime import datetime, date, time
from typing import List, Optional
from pydantic import Field
from sqlmodel import SQLModel


# ── Request Schemas ───────────────────────────────────────────────────────────

class VerificationPageCreate(SQLModel):
    """Schema for creating a verification page."""
    page_name: str = Field(min_length=1, max_length=255)
    show_pnl: bool = False
    show_balance: bool = False
    show_trade_history: bool = False
    show_open_future_positions: bool = False
    twitter_url: str = ""
    exchange_account_ids: List[int] = []


class VerificationPageUpdate(SQLModel):
    """Schema for updating a verification page (all fields optional)."""
    page_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    show_pnl: Optional[bool] = None
    show_balance: Optional[bool] = None
    show_trade_history: Optional[bool] = None
    show_open_future_positions: Optional[bool] = None
    twitter_url: Optional[str] = None
    exchange_account_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None


# ── Response Schemas ──────────────────────────────────────────────────────────

class VerificationPagePublic(SQLModel):
    """Public verification page response schema."""
    id: int
    page_name: str
    is_active: bool
    show_pnl: bool = False
    show_balance: bool = False
    show_trade_history: bool = False
    show_open_future_positions: bool = False
    twitter_url: str = ""
    created_at: datetime
    updated_at: datetime


class VerificationPageBalance(SQLModel):
    """Balance response for a verification page."""
    balance: float


class VerificationPageExchangeAccountHistory(SQLModel):
    """Exchange account history within a verification page."""
    exchange_account_id: int
    exchange_account_name: str
    exchange_account_image_url: str
    first_trade_date: Optional[date] = None
    first_trade_time: Optional[time] = None


class VerificationPageUserMe(SQLModel):
    """User info for a verification page (public endpoint)."""
    full_name: str
    is_active: bool
