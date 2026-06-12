from fastapi import Depends
from sqlmodel import Session
from typing import List

from app.db.session import get_session
from app.core.encryption import encrypt_api_secret
from app.models.exchanges import Exchange
from app.schemas.exchange import (
    ExchangeRead,
    ExchangeAccountCreate,
    ExchangeAccountRead,
    ExchangeAccountPublic,
    ExchangeAccountUpdate,
)
from app.repositories.exchange_repository import ExchangeRepository


class ExchangeService:
    def __init__(self, session: Session = Depends(get_session)):
        self.exchange_repo = ExchangeRepository(session)

    # ── Exchange catalog ────────────────────────────────────────────────────

    def get_active_exchanges(self) -> List[Exchange]:
        return self.exchange_repo.get_active_exchanges()

    # ── ExchangeAccount CRUD ────────────────────────────────────────────────

    def create_exchange_account(
        self, user_id: int, account_create: ExchangeAccountCreate
    ) -> ExchangeAccountRead:
        encrypted_secret = (
            encrypt_api_secret(account_create.api_secret)
            if account_create.api_secret
            else None
        )
        encrypted_passphrase = (
            encrypt_api_secret(account_create.passphrase)
            if account_create.passphrase
            else None
        )
        db_account = self.exchange_repo.create_exchange_account(
            user_id=user_id,
            account_create=account_create,
            encrypted_secret=encrypted_secret,
            encrypted_passphrase=encrypted_passphrase,
        )
        return self.exchange_repo.to_read(db_account)

    def list_accounts(self, user_id: int) -> List[ExchangeAccountRead]:
        accounts = self.exchange_repo.get_accounts_by_user(user_id)
        return [self.exchange_repo.to_read(a) for a in accounts]

    def list_favorite_accounts(
        self, user_id: int
    ) -> List[ExchangeAccountPublic]:
        accounts = self.exchange_repo.get_favorite_accounts(user_id)
        return [self.exchange_repo.to_public(a) for a in accounts]

    def get_account(
        self, user_id: int, account_id: int
    ) -> ExchangeAccountRead:
        account = self.exchange_repo.get_account_by_id(user_id, account_id)
        return self.exchange_repo.to_read(account)

    def update_account(
        self,
        user_id: int,
        account_id: int,
        update_data: ExchangeAccountUpdate,
    ) -> ExchangeAccountRead:
        account = self.exchange_repo.get_account_by_id(user_id, account_id)

        # Re-encrypt secrets if they are being updated
        encrypted_secret = None
        encrypted_passphrase = None
        if update_data.api_secret is not None:
            encrypted_secret = encrypt_api_secret(update_data.api_secret)
        if update_data.passphrase is not None:
            encrypted_passphrase = encrypt_api_secret(update_data.passphrase)

        updated = self.exchange_repo.update_account(
            account=account,
            update_data=update_data,
            encrypted_secret=encrypted_secret,
            encrypted_passphrase=encrypted_passphrase,
        )
        return self.exchange_repo.to_read(updated)

    def delete_account(self, user_id: int, account_id: int) -> None:
        account = self.exchange_repo.get_account_by_id(user_id, account_id)
        self.exchange_repo.delete_account(account)
