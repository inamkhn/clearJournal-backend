from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, TIMESTAMP, Column, Text


class StorageBase(SQLModel):
    asset: str = Field(index=True, max_length=20)
    location: str = Field(max_length=100)
    from_source: str = Field(default="", max_length=200)
    amount: float = Field(gt=0)
    date: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP, nullable=True)
    )
    notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    user_id: int = Field(foreign_key="users.id", index=True)


class Storage(StorageBase, table=True):
    __tablename__ = "storages"

    id: Optional[int] = Field(default=None, primary_key=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
