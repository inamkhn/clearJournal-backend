from fastapi import Depends
from sqlmodel import Session
from typing import Optional

from app.db.session import get_session
from app.models.users import UserCreate, UserPublic, UserUpdate, Message
from app.repositories.user_repository import UserRepository

class AuthService:
    def __init__(self, session: Session = Depends(get_session)):
        self.user_repo = UserRepository(session)

    def register(self, user: UserCreate) -> UserPublic:
        return self.user_repo.create_user(user)

    def login(self, email: str, password: str) -> Optional[UserPublic]:
        return self.user_repo.authenticate(email, password)

    def verify_email(self, email: str, code: str) -> Message:
        return self.user_repo.verify_email(email, code)

    def resend_verification_code(self, email: str) -> Message:
        return self.user_repo.resend_verification_code(email)

    def initiate_password_reset(self, email: str) -> dict:
        return self.user_repo.initiate_password_reset(email)

    def confirm_password_reset(self, token: str, new_password: str) -> dict:
        return self.user_repo.confirm_password_reset(token, new_password)

    def update_user(self, user_id: int, user_update: UserUpdate) -> UserPublic:
        return self.user_repo.update_user(user_id, user_update)

    def create_access_token(self, data: dict) -> str:
        return self.user_repo.create_access_token(data)
