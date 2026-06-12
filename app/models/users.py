from datetime import datetime
from sqlmodel import SQLModel, Field, Column, String, TIMESTAMP, Boolean
from typing import Optional

from app.schemas.auth import UserRole


class UserBase(SQLModel):
    full_name: str = Field(default="")
    email: str = Field(unique=True, index=True, nullable=False)
    role: UserRole = Field(default=UserRole.user)
    is_active: bool = Field(default=False)


class User(UserBase, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    password_hash: str = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Email verification and password reset fields
    verification_code: Optional[str] = Field(default=None)
    verification_code_expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP, nullable=True)
    )
    reset_token: Optional[str] = Field(default=None)
    reset_token_expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP, nullable=True)
    )
