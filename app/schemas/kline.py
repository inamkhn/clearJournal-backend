from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel


class Kline(SQLModel):
    """Candlestick/kline data point."""
    timestamp: int  # Unix timestamp in milliseconds
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: Optional[datetime] = None
    quote_volume: float = 0
    trades_count: int = 0


class KlineResponse(SQLModel):
    """Response with kline data for a trade."""
    symbol: str
    interval: str
    klines: List[Kline]
    trade_open_time: Optional[datetime] = None
    trade_close_time: Optional[datetime] = None
    trade_side: Optional[str] = None
    trade_entry_price: Optional[float] = None
    trade_exit_price: Optional[float] = None
