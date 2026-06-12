import logging
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.encryption import decrypt_api_secret
from app.db.session import get_session
from app.models.exchanges import ExchangeAccount
from app.schemas.sync import AccountType, SyncStatus
from app.services.sync import sync_status

from sqlmodel import Session, select

logger = logging.getLogger(__name__)

# Sync pipeline steps (used for progress tracking)
STEPS = [
    (1, "Connecting to exchange"),
    (2, "Fetching trades"),
    (3, "Processing and storing trades"),
    (4, "Complete"),
]


@celery_app.task(
    name="app.services.sync.sync_worker.sync_exchange_account",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def sync_exchange_account(
    self,
    user_id: int,
    account_id: int,
    exchange_name: str,
    api_key: str,
    api_secret_encrypted: str,
    passphrase_encrypted: str = None,
) -> dict:
    """
    Celery task: fetch trades from a single exchange account and store them.

    The worker:
    1. Updates Redis status at each step
    2. Checks for cancellation before each step
    3. Decrypts API keys, calls the exchange client
    4. Writes trades to the database
    """
    account_type = AccountType.exchange

    def _update(step_num: int, status: SyncStatus = SyncStatus.in_progress, **kwargs):
        _, label = STEPS[step_num - 1]
        # Only pass known parameters to set_status to avoid TypeError
        sync_status.set_status(
            user_id=user_id,
            account_id=account_id,
            account_type=account_type,
            status=status,
            state=kwargs.get("state", label.lower().replace(" ", "_")),
            step=step_num,
            total_steps=len(STEPS),
            step_label=label,
            message=kwargs.get("message"),
            error=kwargs.get("error"),
            error_type=kwargs.get("error_type"),
        )

    def _check_cancelled():
        if sync_status.is_cancelled(user_id, account_id, account_type):
            logger.info(
                "Sync cancelled for user=%s account=%s", user_id, account_id
            )
            return True
        return False

    try:
        # ── Step 1: Connect ──────────────────────────────────────────────
        if _check_cancelled():
            return {"status": "cancelled"}
        _update(1)

        api_secret = decrypt_api_secret(api_secret_encrypted) if api_secret_encrypted else ""
        passphrase = (
            decrypt_api_secret(passphrase_encrypted)
            if passphrase_encrypted
            else None
        )

        # TODO: Replace with real exchange client factory once implemented
        # from app.services.exchange_clients.factory import ExchangeClientFactory
        # client = ExchangeClientFactory.create(exchange_name, api_key, api_secret, passphrase)

        # ── Step 2: Fetch trades ─────────────────────────────────────────
        if _check_cancelled():
            return {"status": "cancelled"}
        _update(2)

        # TODO: Replace with real client.fetch_trades()
        # raw_trades = client.fetch_trades()
        raw_trades = []  # placeholder
        logger.info(
            "Fetched %d raw trades from %s for account %s",
            len(raw_trades),
            exchange_name,
            account_id,
        )

        # ── Step 3: Process & store ──────────────────────────────────────
        if _check_cancelled():
            return {"status": "cancelled"}
        _update(3)

        # TODO: Replace with real trade processing
        # from app.services.trade_service import process_and_store_trades
        # trade_count = process_and_store_trades(user_id, account_id, raw_trades)
        trade_count = 0  # placeholder

        # Update last_sync timestamp on the exchange_accounts table
        _update_last_sync(account_id)

        # ── Step 4: Complete ─────────────────────────────────────────────
        _update(4, status=SyncStatus.completed, state="done")
        sync_status.mark_completed(
            user_id=user_id,
            account_id=account_id,
            account_type=account_type,
            message=f"Synced {trade_count} trades",
            trade_count=trade_count,
        )

        logger.info(
            "Sync completed for user=%s account=%s trades=%d",
            user_id,
            account_id,
            trade_count,
        )
        return {"status": "completed", "trade_count": trade_count}

    except Exception as exc:
        logger.exception(
            "Sync failed for user=%s account=%s: %s", user_id, account_id, exc
        )

        # Retry on transient errors (network, rate limit)
        if self.request.retries < self.max_retries:
            sync_status.set_status(
                user_id=user_id,
                account_id=account_id,
                account_type=account_type,
                status=SyncStatus.in_progress,
                state="retrying",
                message=f"Retrying ({self.request.retries + 1}/{self.max_retries})...",
            )
            raise self.retry(exc=exc)

        # Final failure
        error_type = _classify_error(exc)
        sync_status.mark_failed(
            user_id=user_id,
            account_id=account_id,
            account_type=account_type,
            error=str(exc),
            error_type=error_type,
        )
        _update_error_on_account(account_id, str(exc))
        return {"status": "failed", "error": str(exc)}


# ── DB helpers (runs inside Celery worker) ────────────────────────────────────

def _update_last_sync(account_id: int) -> None:
    """Set last_sync = now on the exchange_accounts row."""
    session_gen = get_session()
    session = next(session_gen)
    try:
        account = session.exec(
            select(ExchangeAccount).where(ExchangeAccount.id == account_id)
        ).first()
        if account:
            account.last_sync = datetime.utcnow()
            account.error = None
            session.add(account)
            session.commit()
    finally:
        session.close()


def _update_error_on_account(account_id: int, error: str) -> None:
    """Persist the error message on the exchange_accounts row."""
    session_gen = get_session()
    session = next(session_gen)
    try:
        account = session.exec(
            select(ExchangeAccount).where(ExchangeAccount.id == account_id)
        ).first()
        if account:
            account.error = error
            session.add(account)
            session.commit()
    finally:
        session.close()


def _classify_error(exc: Exception) -> str:
    """Best-effort classification of an exception into an error_type string."""
    msg = str(exc).lower()
    if "401" in msg or "unauthorized" in msg or "invalid api" in msg:
        return "auth"
    if "429" in msg or "rate limit" in msg:
        return "rate_limit"
    if "timeout" in msg or "connection" in msg:
        return "network"
    return "unknown"
