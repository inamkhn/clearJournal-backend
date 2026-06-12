from typing import List, Optional, Literal, Union, Annotated
from pydantic import Field, Discriminator
from sqlmodel import SQLModel

from app.schemas.exchange import ExchangeAccountPublic
from app.schemas.wallet_account import WalletAccountRead
from app.schemas.storage import StorageRead


# ── Allocation Items (where an asset is held) ─────────────────────────────────

class AssetItemExchange(SQLModel):
    type: Literal["exchange"] = "exchange"
    amount: float = 0
    value: float = 0
    exchange_account: ExchangeAccountPublic
    price_asset: float  # read-only


class AssetItemStorage(SQLModel):
    type: Literal["storage"] = "storage"
    storage: StorageRead
    value: float = 0
    price_asset: float = 0
    amount: float  # read-only


class AssetItemWallet(SQLModel):
    type: Literal["wallet"] = "wallet"
    amount: float = 0
    value: float = 0
    price_asset: float = 0
    wallet: WalletAccountRead


# Union type for allocations
AssetAllocation = Annotated[
    Union[AssetItemExchange, AssetItemStorage, AssetItemWallet],
    Discriminator(discriminator="type"),
]


# ── Asset (consolidated view of one crypto across all accounts) ───────────────

class Asset(SQLModel):
    type: Literal["asset"] = "asset"
    symbol: str
    allocations: List[AssetAllocation] = Field(default_factory=list)
    amount: float  # total quantity across all accounts (read-only)
    image: str  # icon URL (read-only)
    price: float  # current market price (read-only)
    value: float  # amount × price (read-only)


# ── Warning (for accounts with issues) ────────────────────────────────────────

class WarningModel(SQLModel):
    type: Literal["warning"] = "warning"
    warning: str
    account_id: Optional[int] = None
    exchange: Optional[str] = None
    wallet_id: Optional[int] = None
    wallet: Optional[str] = None


# Union type for the assets endpoint response
AssetOrWarning = Annotated[
    Union[Asset, WarningModel],
    Discriminator(discriminator="type"),
]
