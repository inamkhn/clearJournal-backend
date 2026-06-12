from fastapi import Depends
from sqlmodel import Session, select
from typing import List, Optional

from app.db.session import get_session
from app.models.exchanges import ExchangeAccount, Exchange
from app.schemas.sync import (
    AccountType,
    SyncResponse,
    SyncStatusResponse,
)
from app.services.sync import sync_status
from app.services.sync.sync_worker import sync_exchange_account


class SyncService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    # ── Trigger sync ────────────────────────────────────────────────────────

    def sync_accounts(
        self,
        user_id: int,
        exchange_account_ids: Optional[List[int]] = None,
        exclude_exchange_account_ids: Optional[List[int]] = None,
        exchange_ids: Optional[List[int]] = None,
        api_key: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> SyncResponse:
        """
        Filter exchange accounts, queue a Celery task for each,
        and write initial "queued" status to Redis.
        """
        accounts = self._filter_accounts(
            user_id=user_id,
            exchange_account_ids=exchange_account_ids,
            exclude_exchange_account_ids=exclude_exchange_account_ids,
            exchange_ids=exchange_ids,
            api_key=api_key,
            is_favorite=is_favorite,
            is_active=is_active,
        )

        queued_count = 0
        for account in accounts:
            # Get exchange name for the worker
            exchange = self.session.exec(
                select(Exchange).where(Exchange.id == account.exchange_id)
            ).first()
            if not exchange:
                continue

            # Write initial "queued" status to Redis
            sync_status.set_status(
                user_id=user_id,
                account_id=account.id,
                account_type=AccountType.exchange,
            )

            # Push Celery task
            sync_exchange_account.delay(
                user_id=user_id,
                account_id=account.id,
                exchange_name=exchange.name,
                api_key=account.api_key,
                api_secret_encrypted=account.api_secret_encrypted,
                passphrase_encrypted=account.passphrase_encrypted,
            )
            queued_count += 1

        return SyncResponse(
            message=f"Sync started for {queued_count} account(s)",
            accounts_queued=queued_count,
        )

    # ── Status ──────────────────────────────────────────────────────────────

    def get_sync_status(self, user_id: int) -> SyncStatusResponse:
        """Read all sync statuses for a user from Redis."""
        return sync_status.get_all_statuses(user_id)

    # ── Cancel ──────────────────────────────────────────────────────────────

    def cancel_sync(
        self, user_id: int, account_id: int, account_type: AccountType
    ) -> bool:
        """Cancel a running sync for a specific account.
        Validates account ownership before cancelling.
        Returns True if cancelled, False if no active sync or account not owned by user.
        """
        # Validate the account belongs to the user (for exchange accounts)
        if account_type == AccountType.exchange:
            account = self.session.exec(
                select(ExchangeAccount).where(
                    ExchangeAccount.id == account_id,
                    ExchangeAccount.user_id == user_id,
                )
            ).first()
            if not account:
                return False

        return sync_status.cancel_sync(user_id, account_id, account_type)

    def cancel_all_syncs(self, user_id: int) -> int:
        """Cancel all running syncs for the user. Returns count cancelled."""
        return sync_status.cancel_all(user_id)

    # ── Private: account filtering ──────────────────────────────────────────

    def _filter_accounts(
        self,
        user_id: int,
        exchange_account_ids: Optional[List[int]] = None,
        exclude_exchange_account_ids: Optional[List[int]] = None,
        exchange_ids: Optional[List[int]] = None,
        api_key: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> List[ExchangeAccount]:
        """Build a filtered query of exchange accounts for the user."""
        statement = select(ExchangeAccount).where(
            ExchangeAccount.user_id == user_id,
        )

        if exchange_account_ids:
            statement = statement.where(
                ExchangeAccount.id.in_(exchange_account_ids)
            )

        if exclude_exchange_account_ids:
            statement = statement.where(
                ~ExchangeAccount.id.in_(exclude_exchange_account_ids)
            )

        if exchange_ids:
            statement = statement.where(
                ExchangeAccount.exchange_id.in_(exchange_ids)
            )

        if api_key is not None:
            statement = statement.where(ExchangeAccount.api_key == api_key)

        if is_favorite is not None:
            statement = statement.where(
                ExchangeAccount.is_favorite == is_favorite
            )

        # NOTE: is_active filter requires ExchangeAccount.is_active column (not yet added to model)
        # if is_active is not None:
        #     statement = statement.where(ExchangeAccount.is_active == is_active)

        return self.session.exec(statement).all()
