from datetime import datetime
from typing import Optional, Dict, List
from pydantic import field_validator
from sqlmodel import SQLModel


# ── Request Schemas ───────────────────────────────────────────────────────────

class MessageCreate(SQLModel):
    conversation_id: int
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message content cannot be empty")
        if len(v) > 2000:
            raise ValueError("Message too long. Max 2000 characters.")
        return v


# ── Response Schemas ──────────────────────────────────────────────────────────

class MessageRead(SQLModel):
    id: int
    conversation_id: int
    user_id: int
    content: str
    sender_type: str
    response: Optional[Dict] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    model_used: Optional[str] = None
    response_time_ms: Optional[int] = None
    tool_calls: Optional[List[Dict]] = None
    created_at: datetime
