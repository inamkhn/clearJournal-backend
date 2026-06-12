from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, TIMESTAMP, Column


class TradeSide(str, Enum):
    Buy = "Buy"
    Sell = "Sell"
    Unknown = "Unknown"


class TradeStatus(str, Enum):
    complete = "complete"
    incomplete = "incomplete"


class TradeBase(SQLModel):
    symbol: str = Field(default="", index=True)
    side: TradeSide = Field(default=TradeSide.Unknown)
    size: float = Field(default=0)
    open_time: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    close_time: Optional[datetime] = Field(
        default=None, sa_column=Column(TIMESTAMP, nullable=True)
    )
    open_price: float = Field(default=0)
    close_price: Optional[float] = Field(default=None)
    realized_pnl: float = Field(default=0)
    status: TradeStatus = Field(default=TradeStatus.complete)
    cumulative_pnl: float = Field(default=0)
    leverage: Optional[float] = Field(default=None)
    fees: float = Field(default=0)
    exchange_account_id: int = Field(foreign_key="exchange_accounts.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)


class Trade(TradeBase, table=True):
    __tablename__ = "trades"

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
    tags: List["TradeTag"] = Relationship(back_populates="trade")


class TradeTag(SQLModel, table=True):
    """Association table between trades and tags."""
    __tablename__ = "trade_tags"

    trade_id: int = Field(foreign_key="trades.id", primary_key=True)
    tag_id: int = Field(foreign_key="tags.id", primary_key=True)
