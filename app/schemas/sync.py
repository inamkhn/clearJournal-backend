from datetime import datetime
from enum import Enum
from typing import Optional, Any, List
from sqlmodel import SQLModel


# ── Enums ─────────────────────────────────────────────────────────────────────

class AccountType(str, Enum):
    exchange = "exchange"
    wallet = "wallet"


class SyncStatus(str, Enum):
    queued = "queued"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


# ── Request Schemas ───────────────────────────────────────────────────────────

class SyncCancelRequest(SQLModel):
    account_type: AccountType
    account_id: int


# ── Response Schemas ──────────────────────────────────────────────────────────

class SyncResponse(SQLModel):
    message: str
    accounts_queued: int


class SyncStatusAccount(SQLModel):
    account_id: int
    type: AccountType
    status: Optional[str] = None
    state: Optional[str] = None
    step: Optional[int] = None
    total_steps: Optional[int] = None
    step_label: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
    last_sync: Optional[datetime] = None
    error: Optional[Any] = None
    error_type: Optional[str] = None


class SyncStatusResponse(SQLModel):
    accounts: List[SyncStatusAccount]
    any_in_progress: bool
