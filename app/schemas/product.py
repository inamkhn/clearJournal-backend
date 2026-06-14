from datetime import datetime
from typing import Optional, List
from pydantic import field_validator
from sqlmodel import SQLModel


# ── Request Schemas ───────────────────────────────────────────────────────────

class ProductCreate(SQLModel):
    name: str
    description: str
    account_limit: int
    is_active: bool

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Product name cannot be empty")
        return v

    @field_validator("account_limit")
    @classmethod
    def account_limit_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Account limit must be non-negative")
        return v


class ProductUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    account_limit: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Product name cannot be empty")
        return v


# ── Response Schemas ──────────────────────────────────────────────────────────

class ProductRead(SQLModel):
    id: int
    name: str
    description: str
    account_limit: int
    descriptive_features: List[str] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime
