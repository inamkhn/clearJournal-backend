from enum import Enum
from sqlmodel import SQLModel
from typing import Optional


class UserRole(str, Enum):
    user = "user"
    admin = "admin"


class UserCreate(SQLModel):
    full_name: str = ""
    email: str
    password: str
    role: UserRole = UserRole.user


class UserPublic(SQLModel):
    id: int
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    is_admin: bool = False
    is_subscription_active: bool = False
    is_upgrade_allowed: bool = False
    is_cancellation_allowed: bool = False
    is_reactivation_allowed: bool = False
    is_resubscription_allowed: bool = False
    is_trial_allowed: bool = False


class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


class Message(SQLModel):
    message: str


class Token(SQLModel):
    access_token: str
    token_type: str
