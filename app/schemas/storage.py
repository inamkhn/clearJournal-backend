from datetime import datetime
from typing import List, Optional
from pydantic import Field
from sqlmodel import SQLModel


# ── Request Schemas ───────────────────────────────────────────────────────────

class StorageCreate(SQLModel):
    asset: str
    location: str
    from_source: str = ""
    amount: float = Field(gt=0, description="Amount must be greater than 0")
    date: Optional[datetime] = None


class StorageUpdate(SQLModel):
    asset: Optional[str] = None
    location: Optional[str] = None
    from_source: Optional[str] = None
    amount: Optional[float] = Field(default=None, gt=0, description="Amount must be greater than 0")
    date: Optional[datetime] = None
    notes: Optional[str] = None


# ── Response Schemas ──────────────────────────────────────────────────────────

class Storage(SQLModel):
    id: int
    asset: str
    location: str
    from_source: str
    amount: float
    date: Optional[datetime] = None
    notes: Optional[str] = None
    user_id: int
    image: str  # Computed from asset symbol
    created_at: datetime
    updated_at: datetime


class ListStorage(SQLModel):
    items: List[Storage]
    total: int


# ── Public Schema (for nested responses) ──────────────────────────────────────

class StoragePublic(SQLModel):
    """Public storage schema for use in nested responses (e.g., asset allocations)."""
    id: int
    asset: str
    location: str
    amount: float
    image: str
