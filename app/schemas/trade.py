from datetime import datetime
from enum import Enum
from typing import Optional, List, Literal, Union, Annotated
from pydantic import Discriminator
from sqlmodel import SQLModel

from app.schemas.exchange import ExchangeAccountPublic
from app.schemas.wallet_account import WalletAccountPublic


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


# ── Trade Response Schemas ────────────────────────────────────────────────────

class TradeRead(SQLModel):
    """Full trade response with computed fields."""
    type: Literal["trade"] = "trade"
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
    cumulative_pnl: float = 0
    drawdown: float = 0
    rolling_peak: float = 0
    under_water_period: float = 0
    leverage: Optional[float] = None
    fees: float = 0
    exchange_account: Optional[ExchangeAccountPublic] = None
    wallet_account: Optional[WalletAccountPublic] = None
    exchange_account_id: Optional[int] = None
    wallet_account_id: Optional[int] = None
    user_id: Optional[int] = None
    # Computed fields (read-only)
    duration: float  # seconds
    volume: float  # size * open_price
    symbol_url: str
    trade_source: Literal["exchange", "wallet"]


class TradeWithoutPNL(SQLModel):
    """Open trade without finalized P&L."""
    type: Literal["trade_open"] = "trade_open"
    id: Optional[int] = None
    symbol: str
    side: TradeSide
    size: float
    open_time: datetime
    open_price: float
    status: TradeStatus
    leverage: Optional[float] = None
    exchange_account: Optional[ExchangeAccountPublic] = None
    wallet_account: Optional[WalletAccountPublic] = None
    exchange_account_id: Optional[int] = None
    wallet_account_id: Optional[int] = None
    # Computed fields
    duration: float  # seconds (time since open)
    volume: float
    symbol_url: str
    trade_source: Literal["exchange", "wallet"]


# Union for list items
TradeItem = Annotated[
    Union[TradeRead, TradeWithoutPNL],
    Discriminator(discriminator="type"),
]


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
