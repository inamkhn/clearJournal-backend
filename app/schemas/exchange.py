from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel


# ── Exchange Schemas ──────────────────────────────────────────────────────────

class ExchangeRead(SQLModel):
    id: int
    name: str
    description: str
    configs: Dict[str, Any]
    is_active: bool
    image_url: str
    created_at: datetime
    updated_at: datetime


# ── ExchangeAccount Schemas ────────────────────────────────────────────────────

class ExchangeAccountCreate(SQLModel):
    name: str = ""
    is_favorite: bool = False
    api_key: str = ""
    api_secret: str = ""
    passphrase: str = ""
    exchange_id: int


class ExchangeAccountRead(SQLModel):
    id: int
    name: str
    api_key: str
    is_favorite: bool
    exchange_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    last_sync: Optional[datetime] = None
    error: Optional[str] = None


class ExchangeAccountPublic(ExchangeAccountRead):
    exchange: ExchangeRead


class ExchangeAccountUpdate(SQLModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    is_favorite: Optional[bool] = None
