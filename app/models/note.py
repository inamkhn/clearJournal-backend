from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, TIMESTAMP, Column, Text


class NoteBase(SQLModel):
    title: str = Field(max_length=200)
    description: str = Field(sa_column=Column(Text, nullable=False))
    url: str = Field(default="", max_length=500)
    trade_id: int = Field(foreign_key="trades.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)


class Note(NoteBase, table=True):
    __tablename__ = "notes"

    id: Optional[int] = Field(default=None, primary_key=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    # Relationships
    images: List["NoteImage"] = Relationship(
        back_populates="note",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
