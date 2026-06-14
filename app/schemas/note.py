from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel


# ── Request Schemas ───────────────────────────────────────────────────────────

class NoteCreate(SQLModel):
    """Schema for creating a note (used as form data, not JSON)."""
    title: str
    description: str
    url: str
    trade_id: int


class NoteUpdate(SQLModel):
    """Schema for partial update of a note."""
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None


# ── Response Schemas ──────────────────────────────────────────────────────────

class NotePublic(SQLModel):
    """Public note response schema."""
    id: int
    title: str
    description: str
    url: str
    trade_id: int
    created_at: datetime
    updated_at: datetime
