from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlmodel import SQLModel, Field, Relationship, TIMESTAMP, Column
from sqlalchemy import JSON


# ── Exchange (master list of supported exchanges) ─────────────────────────────

class ExchangeBase(SQLModel):
    name: str = Field(default="")
    description: str = Field(default="")
    configs: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    is_active: bool = Field(default=True)
    image_url: str = ""


class Exchange(ExchangeBase, table=True):
    __tablename__ = "exchanges"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    accounts: List["ExchangeAccount"] = Relationship(back_populates="exchange")


# ── ExchangeAccount (user's connected exchange API keys) ──────────────────────

class ExchangeAccountBase(SQLModel):
    name: str = Field(default="")
    api_key: str = Field(default="")
    is_favorite: bool = Field(default=False)
    exchange_id: int = Field(foreign_key="exchanges.id")
    user_id: int = Field(foreign_key="users.id")


class ExchangeAccount(ExchangeAccountBase, table=True):
    __tablename__ = "exchange_accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    api_secret_encrypted: str = Field(default="")
    passphrase_encrypted: Optional[str] = Field(default=None)

    last_sync: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP, nullable=True)
    )
    error: Optional[str] = Field(default=None)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    exchange: Optional[Exchange] = Relationship(back_populates="accounts")
