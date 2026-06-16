from datetime import datetime
from typing import Optional
from pydantic import field_validator
from sqlmodel import SQLModel


# ── Request Schemas ───────────────────────────────────────────────────────────

class ConversationCreate(SQLModel):
    title: Optional[str] = ""

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: Optional[str]) -> str:
        if v is not None:
            v = v.strip()
        return v or ""


class ConversationUpdate(SQLModel):
    title: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Title cannot be empty")
        return v


# ── Response Schemas ──────────────────────────────────────────────────────────

class ConversationRead(SQLModel):
    id: int
    user_id: int
    title: str
    openai_conversation_id: Optional[str] = None
    message_count: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
