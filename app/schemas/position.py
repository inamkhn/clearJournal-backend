from typing import Optional
from sqlmodel import SQLModel

from app.schemas.exchange import ExchangeAccountPublic
from app.schemas.wallet_account import WalletAccountPublic


class Position(SQLModel):
    exchange_account: Optional[ExchangeAccountPublic] = None
    wallet_account: Optional[WalletAccountPublic] = None
    symbol: str
    size: float
    side: str  # "long" or "short"
    open_price: float
    unrealized_pnl: float = 0
    leverage: Optional[float] = None  # null for spot, number for futures
