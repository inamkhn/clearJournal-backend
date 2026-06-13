from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, TIMESTAMP, Column


class TagBase(SQLModel):
    name: str = Field(default="", index=True, max_length=100)
    color: str = Field(default="#000000", max_length=7)
    is_favorite: bool = Field(default=False)
    user_id: int = Field(foreign_key="users.id", index=True)


class Tag(TagBase, table=True):
    __tablename__ = "tags"

    id: Optional[int] = Field(default=None, primary_key=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
