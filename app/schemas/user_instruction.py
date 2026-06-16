from datetime import datetime
from typing import Optional
from pydantic import field_validator
from sqlmodel import SQLModel


# ── Request Schemas ───────────────────────────────────────────────────────────

class UserInstructionCreate(SQLModel):
    name: str
    content: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Instruction name cannot be empty")
        if len(v) > 100:
            raise ValueError("Name must be 100 characters or less")
        return v

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Instruction content cannot be empty")
        if len(v) > 2000:
            raise ValueError("Content must be 2000 characters or less")
        return v


class UserInstructionUpdate(SQLModel):
    name: Optional[str] = None
    content: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Instruction name cannot be empty")
            if len(v) > 100:
                raise ValueError("Name must be 100 characters or less")
        return v

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Instruction content cannot be empty")
            if len(v) > 2000:
                raise ValueError("Content must be 2000 characters or less")
        return v


# ── Response Schemas ──────────────────────────────────────────────────────────

class UserInstructionRead(SQLModel):
    id: int
    user_id: int
    name: str
    content: str
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
