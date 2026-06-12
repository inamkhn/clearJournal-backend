from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from fastapi import HTTPException

from app.models.exchanges import Exchange, ExchangeAccount
from app.schemas.exchange import (
    ExchangeAccountCreate,
    ExchangeAccountUpdate,
    ExchangeAccountRead,
    ExchangeAccountPublic,
    ExchangeRead,
)


class ExchangeRepository:
    def __init__(self, session: Session):
        self.session = session

    # ── Exchange (catalog) ──────────────────────────────────────────────────

    def get_active_exchanges(self) -> List[Exchange]:
        statement = select(Exchange).where(Exchange.is_active == True)
        return self.session.exec(statement).all()

    def get_exchange_by_id(self, exchange_id: int) -> Optional[Exchange]:
        statement = select(Exchange).where(Exchange.id == exchange_id)
        return self.session.exec(statement).first()

    # ── ExchangeAccount CRUD ────────────────────────────────────────────────

    def create_exchange_account(
        self,
        user_id: int,
        account_create: ExchangeAccountCreate,
        encrypted_secret: str,
        encrypted_passphrase: Optional[str],
    ) -> ExchangeAccount:
        # Validate exchange exists
        exchange = self.get_exchange_by_id(account_create.exchange_id)
        if not exchange:
            raise HTTPException(status_code=400, detail="Invalid exchange ID")

        # Prevent duplicate API key for the same user + exchange
        statement = select(ExchangeAccount).where(
            ExchangeAccount.user_id == user_id,
            ExchangeAccount.exchange_id == account_create.exchange_id,
            ExchangeAccount.api_key == account_create.api_key,
        )
        existing = self.session.exec(statement).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Exchange account with this API key already exists",
            )

        db_account = ExchangeAccount(
            name=account_create.name,
            api_key=account_create.api_key,
            api_secret_encrypted=encrypted_secret,
            passphrase_encrypted=encrypted_passphrase,
            is_favorite=account_create.is_favorite,
            exchange_id=account_create.exchange_id,
            user_id=user_id,
        )
        self.session.add(db_account)
        self.session.commit()
        self.session.refresh(db_account)
        return db_account

    def get_accounts_by_user(self, user_id: int) -> List[ExchangeAccount]:
        """Return all exchange accounts for a user."""
        statement = select(ExchangeAccount).where(
            ExchangeAccount.user_id == user_id
        )
        return self.session.exec(statement).all()

    def get_favorite_accounts(self, user_id: int) -> List[ExchangeAccount]:
        """Return only favorited exchange accounts for a user, with exchange eagerly loaded."""
        statement = (
            select(ExchangeAccount)
            .options(selectinload(ExchangeAccount.exchange))
            .where(
                ExchangeAccount.user_id == user_id,
                ExchangeAccount.is_favorite == True,
            )
        )
        return self.session.exec(statement).all()

    def get_account_by_id(
        self, user_id: int, account_id: int
    ) -> ExchangeAccount:
        """Return a single account owned by the user, or 404."""
        statement = select(ExchangeAccount).where(
            ExchangeAccount.id == account_id,
            ExchangeAccount.user_id == user_id,
        )
        account = self.session.exec(statement).first()
        if not account:
            raise HTTPException(
                status_code=404, detail="Exchange account not found"
            )
        return account

    def update_account(
        self,
        account: ExchangeAccount,
        update_data: ExchangeAccountUpdate,
        encrypted_secret: Optional[str] = None,
        encrypted_passphrase: Optional[str] = None,
    ) -> ExchangeAccount:
        """Apply partial update to an exchange account."""
        if update_data.name is not None:
            account.name = update_data.name
        if update_data.api_key is not None and update_data.api_key != account.api_key:
            # Prevent changing to an API key already used by another account on the same exchange
            statement = select(ExchangeAccount).where(
                ExchangeAccount.user_id == account.user_id,
                ExchangeAccount.exchange_id == account.exchange_id,
                ExchangeAccount.api_key == update_data.api_key,
                ExchangeAccount.id != account.id,
            )
            duplicate = self.session.exec(statement).first()
            if duplicate:
                raise HTTPException(
                    status_code=400,
                    detail="Another account on this exchange already uses this API key",
                )
            account.api_key = update_data.api_key
        if encrypted_secret is not None:
            account.api_secret_encrypted = encrypted_secret
        if encrypted_passphrase is not None:
            account.passphrase_encrypted = encrypted_passphrase
        if update_data.is_favorite is not None:
            account.is_favorite = update_data.is_favorite

        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)
        return account

    def delete_account(self, account: ExchangeAccount) -> None:
        """Delete an exchange account."""
        self.session.delete(account)
        self.session.commit()

    # ── Mapping helpers ─────────────────────────────────────────────────────

    @staticmethod
    def to_read(account: ExchangeAccount) -> ExchangeAccountRead:
        """Map ORM row → ExchangeAccountRead (no secrets)."""
        return ExchangeAccountRead(
            id=account.id,
            name=account.name,
            api_key=account.api_key,
            is_favorite=account.is_favorite,
            exchange_id=account.exchange_id,
            user_id=account.user_id,
            created_at=account.created_at,
            updated_at=account.updated_at,
            last_sync=account.last_sync,
            error=account.error,
        )

    @staticmethod
    def to_public(account: ExchangeAccount) -> ExchangeAccountPublic:
        """Map ORM row → ExchangeAccountPublic (includes nested Exchange)."""
        exchange = account.exchange
        exchange_read = ExchangeRead(
            id=exchange.id,
            name=exchange.name,
            description=exchange.description,
            configs=exchange.configs,
            is_active=exchange.is_active,
            image_url=exchange.image_url,
            created_at=exchange.created_at,
            updated_at=exchange.updated_at,
        ) if exchange else None

        return ExchangeAccountPublic(
            id=account.id,
            name=account.name,
            api_key=account.api_key,
            is_favorite=account.is_favorite,
            exchange_id=account.exchange_id,
            user_id=account.user_id,
            created_at=account.created_at,
            updated_at=account.updated_at,
            last_sync=account.last_sync,
            error=account.error,
            exchange=exchange_read,
        )
