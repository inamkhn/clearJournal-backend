from sqlmodel import Session, select
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from typing import Optional
from app.core.exceptions import (
    UserAlreadyExistsException, 
    UserNotFoundException, 
    InvalidTokenException, 
    InvalidCredentialsException
)
import secrets

from app.core.config import settings
from app.models.users import User
from app.schemas.auth import UserCreate, UserPublic, UserUpdate, Message

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def map_to_public(self, user: User) -> UserPublic:
        return UserPublic(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            is_admin=user.role == "admin",
            is_subscription_active=False,
            is_upgrade_allowed=True,
            is_cancellation_allowed=False,
            is_reactivation_allowed=False,
            is_resubscription_allowed=False,
            is_trial_allowed=True
        )

    def create_user(self, user_create: UserCreate) -> UserPublic:
        statement = select(User).where(User.email == user_create.email)
        existing_user = self.session.exec(statement).first()
        if existing_user:
            raise UserAlreadyExistsException("Email already registered")
            
        verification_code = secrets.token_hex(3)
        verification_expires = datetime.utcnow() + timedelta(hours=24)
        
        db_user = User(
            full_name=user_create.full_name,
            email=user_create.email,
            password_hash=get_password_hash(user_create.password),
            role=user_create.role,
            is_active=False,
            verification_code=verification_code,
            verification_code_expires_at=verification_expires
        )
        self.session.add(db_user)
        self.session.commit()
        self.session.refresh(db_user)
        # TODO: Trigger email sending here
        return self.map_to_public(db_user)

    def authenticate(self, email: str, password: str) -> Optional[UserPublic]:
        statement = select(User).where(User.email == email)
        user = self.session.exec(statement).first()
        if not user or not verify_password(password, user.password_hash):
            return None
        return self.map_to_public(user)

    def verify_email(self, email: str, code: str) -> Message:
        statement = select(User).where(User.email == email)
        user = self.session.exec(statement).first()
        if not user:
            raise UserNotFoundException("User not found")
            
        if not user.verification_code or user.verification_code != code:
            raise InvalidTokenException("Invalid verification code")
            
        if user.verification_code_expires_at and user.verification_code_expires_at < datetime.utcnow():
            raise InvalidTokenException("Verification code expired")
            
        user.is_active = True
        user.verification_code = None
        user.verification_code_expires_at = None
        self.session.commit()
        return Message(message="Email verified successfully")

    def resend_verification_code(self, email: str) -> Message:
        statement = select(User).where(User.email == email)
        user = self.session.exec(statement).first()
        if not user:
            raise UserNotFoundException("User not found")
            
        user.verification_code = secrets.token_hex(3)
        user.verification_code_expires_at = datetime.utcnow() + timedelta(hours=24)
        self.session.commit()
        # TODO: Trigger email sending here
        return Message(message="Verification code resent successfully")

    def initiate_password_reset(self, email: str) -> dict:
        statement = select(User).where(User.email == email)
        user = self.session.exec(statement).first()
        if not user:
            raise UserNotFoundException("User not found")
            
        user.reset_token = secrets.token_urlsafe(32)
        user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=1)
        self.session.commit()
        # TODO: Trigger email sending here
        return {"status": "success", "message": "Password reset email sent"}

    def confirm_password_reset(self, token: str, new_password: str) -> dict:
        statement = select(User).where(User.reset_token == token)
        user = self.session.exec(statement).first()
        if not user:
            raise InvalidTokenException("Invalid or expired reset token")
            
        if user.reset_token_expires_at and user.reset_token_expires_at < datetime.utcnow():
            raise InvalidTokenException("Reset token expired")
            
        user.password_hash = get_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expires_at = None
        self.session.commit()
        return {"status": "success", "message": "Password reset confirmed"}

    def update_user(self, user_id: int, user_update: UserUpdate) -> UserPublic:
        statement = select(User).where(User.id == user_id)
        user = self.session.exec(statement).first()
        if not user:
            raise UserNotFoundException("User not found")
            
        if user_update.full_name is not None:
            user.full_name = user_update.full_name
            
        if user_update.new_password is not None:
            if not user_update.current_password or not verify_password(user_update.current_password, user.password_hash):
                raise InvalidCredentialsException("Invalid current password")
            user.password_hash = get_password_hash(user_update.new_password)
            
        self.session.commit()
        self.session.refresh(user)
        return self.map_to_public(user)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
        return encoded_jwt
