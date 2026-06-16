from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column, TIMESTAMP


class UserAgentInstructionBase(SQLModel):
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=100)
    content: str = Field(max_length=2000)
    version: int = Field(default=1, ge=1)
    is_active: bool = Field(default=False)


class UserAgentInstruction(UserAgentInstructionBase, table=True):
    __tablename__ = "user_agent_instructions"

    id: Optional[int] = Field(default=None, primary_key=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
