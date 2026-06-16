from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Column, TIMESTAMP, Relationship

if TYPE_CHECKING:
    from app.models.message import Message


class ConversationBase(SQLModel):
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str = Field(default="", max_length=255)
    openai_conversation_id: Optional[str] = Field(default=None, max_length=255)
    message_count: int = Field(default=0, ge=0)
    last_message_at: Optional[datetime] = Field(default=None)


class Conversation(ConversationBase, table=True):
    __tablename__ = "conversations"

    id: Optional[int] = Field(default=None, primary_key=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Relationships
    messages: List["Message"] = Relationship(back_populates="conversation")
