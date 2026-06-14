from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship, TIMESTAMP, Column


class NoteImageBase(SQLModel):
    note_id: int = Field(foreign_key="notes.id", index=True)
    s3_key: str = Field(max_length=500)


class NoteImage(NoteImageBase, table=True):
    __tablename__ = "note_images"

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
    note: Optional["Note"] = Relationship(back_populates="images")
