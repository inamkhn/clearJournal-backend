from datetime import datetime
from typing import Optional
from pydantic import field_validator
from sqlmodel import SQLModel
import re


# ── Request Schemas ───────────────────────────────────────────────────────────

class TagCreate(SQLModel):
    name: str = ""
    color: str = "#000000"
    is_favorite: bool = False

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Tag name cannot be empty")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        # Accept #RGB or #RRGGBB format
        if not re.match(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$", v):
            raise ValueError("Color must be a valid hex color (e.g., #FF5733 or #FFF)")
        return v.upper()


class TagUpdate(SQLModel):
    name: Optional[str] = None
    color: Optional[str] = None
    is_favorite: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Tag name cannot be empty")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$", v):
                raise ValueError("Color must be a valid hex color (e.g., #FF5733 or #FFF)")
            return v.upper()
        return v


# ── Response Schemas ──────────────────────────────────────────────────────────

class Tag(SQLModel):
    id: int
    name: str
    color: str
    is_favorite: bool
    user_id: int
    created_at: datetime
    updated_at: datetime


class TagPublic(SQLModel):
    id: int
    name: str
    color: str
    is_favorite: bool
    count_trades: int = 0
