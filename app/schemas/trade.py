from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel


class TradeSide(str, Enum):
    Buy = "Buy"
    Sell = "Sell"
    Unknown = "Unknown"


class TradeStatus(str, Enum):
    complete = "complete"
    incomplete = "incomplete"


class TradeCreate(SQLModel):
    symbol: str
    side: TradeSide
    size: float
    open_time: datetime
    close_time: Optional[datetime] = None
    open_price: float
    close_price: Optional[float] = None
    realized_pnl: float = 0
    status: TradeStatus = TradeStatus.complete
    leverage: Optional[float] = None
    fees: float = 0
    exchange_account_id: int


class TradeRead(SQLModel):
    id: Optional[int] = None
    symbol: str
    side: TradeSide
    size: float
    open_time: datetime
    close_time: Optional[datetime] = None
    open_price: float
    close_price: Optional[float] = None
    realized_pnl: float
    status: TradeStatus
    cumulative_pnl: float
    leverage: Optional[float] = None
    fees: float
    exchange_account_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class TradeUpdate(SQLModel):
    symbol: Optional[str] = None
    side: Optional[TradeSide] = None
    size: Optional[float] = None
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    open_price: Optional[float] = None
    close_price: Optional[float] = None
    realized_pnl: Optional[float] = None
    status: Optional[TradeStatus] = None
    leverage: Optional[float] = None
    fees: Optional[float] = None


# ── Position Computation Schemas ──────────────────────────────────────────────

class PositionComputed(SQLModel):
    """A position computed from trade history."""
    symbol: str
    side: TradeSide
    size: float
    open_price: float
    unrealized_pnl: float = 0
    leverage: Optional[float] = None
    exchange_account_id: int


class AssetBalance(SQLModel):
    """Current balance of an asset computed from trades."""
    symbol: str
    amount: float  # net quantity held
    avg_entry_price: float  # weighted average entry price
    exchange_account_id: int
