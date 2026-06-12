from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel

from app.schemas.wallet import WalletRead


class WalletAccountRead(SQLModel):
    id: int
    wallet_address: str
    name: str
    is_active: bool
    is_favorite: bool
    is_verified: bool
    user_id: int
    wallet_id: Optional[int] = None
    api_wallet_address: Optional[str] = None
    last_sync: Optional[datetime] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    wallet: Optional[WalletRead] = None


class WalletAccountPublic(WalletAccountRead):
    wallet: Optional[WalletRead] = None
