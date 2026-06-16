from datetime import datetime
from typing import Optional, Dict, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Column, Text, JSON, TIMESTAMP, Relationship

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class MessageBase(SQLModel):
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    content: str = Field(sa_column=Column(Text, nullable=False))
    sender_type: str = Field(default="user", max_length=20)
    response: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    prompt_tokens: Optional[int] = Field(default=None)
    completion_tokens: Optional[int] = Field(default=None)
    total_tokens: Optional[int] = Field(default=None)
    model_used: Optional[str] = Field(default=None, max_length=50)
    response_time_ms: Optional[int] = Field(default=None)
    tool_calls: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON))


class Message(MessageBase, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow)
    )

    # Relationships
    conversation: Optional["Conversation"] = Relationship(back_populates="messages")
