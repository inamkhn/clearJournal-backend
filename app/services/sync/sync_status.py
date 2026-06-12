from datetime import datetime
from typing import List, Optional

from app.core.redis import redis_set, redis_get, redis_keys
from app.schemas.sync import (
    AccountType,
    SyncStatus,
    SyncStatusAccount,
    SyncStatusResponse,
)

# Redis key pattern: sync:{account_type}:{user_id}:{account_id}
# TTL: 1 hour (status auto-expires after sync is done)
SYNC_KEY_TTL = 3600


def _key(account_type: str, user_id: int, account_id: int) -> str:
    return f"sync:{account_type}:{user_id}:{account_id}"


# ── Write helpers (called by worker + service) ───────────────────────────────

def set_status(
    user_id: int,
    account_id: int,
    account_type: AccountType = AccountType.exchange,
    status: SyncStatus = SyncStatus.queued,
    state: Optional[str] = None,
    step: Optional[int] = None,
    total_steps: Optional[int] = None,
    step_label: Optional[str] = None,
    message: Optional[str] = None,
    error: Optional[str] = None,
    error_type: Optional[str] = None,
) -> None:
    """Write or update sync status for a single account in Redis.
    Preserves existing last_sync timestamp if present.
    """
    key = _key(account_type.value, user_id, account_id)
    
    # Preserve existing last_sync from Redis if present
    existing = redis_get(key) or {}
    last_sync = existing.get("last_sync")
    
    data = {
        "account_id": account_id,
        "type": account_type.value,
        "status": status.value,
        "state": state,
        "step": step,
        "total_steps": total_steps,
        "step_label": step_label,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "last_sync": last_sync,  # Preserve existing value
        "error": error,
        "error_type": error_type,
    }
    redis_set(key, data, ttl=SYNC_KEY_TTL)


def mark_completed(
    user_id: int,
    account_id: int,
    account_type: AccountType,
    message: str,
    trade_count: int = 0,
) -> None:
    """Mark a sync as successfully completed. Sets last_sync timestamp."""
    now = datetime.utcnow().isoformat()
    key = _key(account_type.value, user_id, account_id)
    
    # Read existing data to preserve fields, then update
    existing = redis_get(key) or {}
    existing.update({
        "account_id": account_id,
        "type": account_type.value,
        "status": SyncStatus.completed.value,
        "state": "done",
        "step": 4,
        "total_steps": 4,
        "step_label": "Complete",
        "message": message or f"Synced {trade_count} trades",
        "timestamp": now,
        "last_sync": now,  # Set last_sync on completion
        "error": None,
        "error_type": None,
    })
    redis_set(key, existing, ttl=SYNC_KEY_TTL)


def mark_failed(
    user_id: int,
    account_id: int,
    account_type: AccountType,
    error: str,
    error_type: str = "unknown",
) -> None:
    """Mark a sync as failed."""
    set_status(
        user_id=user_id,
        account_id=account_id,
        account_type=account_type,
        status=SyncStatus.failed,
        state="error",
        error=error,
        error_type=error_type,
    )


# ── Read helpers (called by API endpoints) ───────────────────────────────────

def get_status(
    user_id: int, account_id: int, account_type: AccountType = AccountType.exchange
) -> Optional[SyncStatusAccount]:
    """Read the current sync status for one account."""
    data = redis_get(_key(account_type.value, user_id, account_id))
    if data is None:
        return None
    return SyncStatusAccount(**data)


def get_all_statuses(user_id: int) -> SyncStatusResponse:
    """Read sync statuses for all accounts of a user from Redis."""
    pattern = f"sync:*:{user_id}:*"
    keys = redis_keys(pattern)

    accounts: List[SyncStatusAccount] = []
    for key in keys:
        data = redis_get(key)
        if data:
            accounts.append(SyncStatusAccount(**data))

    any_in_progress = any(
        a.status in (SyncStatus.queued.value, SyncStatus.in_progress.value)
        for a in accounts
    )

    return SyncStatusResponse(accounts=accounts, any_in_progress=any_in_progress)


# ── Cancel helpers ────────────────────────────────────────────────────────────

def is_cancelled(
    user_id: int, account_id: int, account_type: AccountType = AccountType.exchange
) -> bool:
    """Check if a sync has been cancelled (used by worker to abort early)."""
    data = redis_get(_key(account_type.value, user_id, account_id))
    if data is None:
        return False
    return data.get("status") == SyncStatus.cancelled.value


def cancel_sync(
    user_id: int, account_id: int, account_type: AccountType = AccountType.exchange
) -> bool:
    """Set the status to cancelled for a specific account.
    Only updates if a sync key already exists. Returns True if cancelled, False if no active sync.
    """
    key = _key(account_type.value, user_id, account_id)
    existing = redis_get(key)
    
    # Only cancel if a sync status exists and is active
    if existing is None:
        return False
    
    if existing.get("status") not in (SyncStatus.queued.value, SyncStatus.in_progress.value):
        return False
    
    existing.update({
        "status": SyncStatus.cancelled.value,
        "state": "cancelled",
        "message": "Cancelled by user",
        "timestamp": datetime.utcnow().isoformat(),
    })
    redis_set(key, existing, ttl=SYNC_KEY_TTL)
    return True


def cancel_all(user_id: int) -> int:
    """Cancel all active syncs for a user. Returns the count cancelled."""
    pattern = f"sync:*:{user_id}:*"
    keys = redis_keys(pattern)
    count = 0
    for key in keys:
        data = redis_get(key)
        if data and data.get("status") in (
            SyncStatus.queued.value,
            SyncStatus.in_progress.value,
        ):
            data["status"] = SyncStatus.cancelled.value
            data["state"] = "cancelled"
            data["message"] = "Cancelled by user"
            data["timestamp"] = datetime.utcnow().isoformat()
            redis_set(key, data, ttl=SYNC_KEY_TTL)
            count += 1
    return count
