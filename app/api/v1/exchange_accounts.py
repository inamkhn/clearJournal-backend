from fastapi import APIRouter, Depends, status
from typing import List, Optional

from app.api import deps
from app.models.users import User
from app.schemas.exchange import (
    ExchangeAccountCreate,
    ExchangeAccountRead,
    ExchangeAccountPublic,
    ExchangeAccountUpdate,
)
from app.schemas.sync import (
    SyncCancelRequest,
    SyncResponse,
    SyncStatusResponse,
)
from app.schemas.asset import AssetOrWarning
from app.schemas.position import Position
from app.services.exchange.exchange_service import ExchangeService
from app.services.sync.sync_service import SyncService
from app.services.asset_service import AssetService

router = APIRouter()


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/", response_model=ExchangeAccountRead, status_code=status.HTTP_201_CREATED)
def create_exchange_account(
    account_create: ExchangeAccountCreate,
    current_user: User = Depends(deps.get_current_user),
    exchange_service: ExchangeService = Depends(),
):
    """
    Connect a new exchange account by providing API keys.
    The api_secret and passphrase are Fernet-encrypted before storage.
    """
    return exchange_service.create_exchange_account(current_user.id, account_create)


# ── List all ──────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[ExchangeAccountRead])
def list_exchange_accounts(
    current_user: User = Depends(deps.get_current_user),
    exchange_service: ExchangeService = Depends(),
):
    """
    Return all exchange accounts owned by the current user.
    Secrets are never exposed in the response.
    """
    return exchange_service.list_accounts(current_user.id)


# ── Favorites ─────────────────────────────────────────────────────────────────

@router.get("/favorites", response_model=List[ExchangeAccountPublic])
def list_favorite_exchange_accounts(
    current_user: User = Depends(deps.get_current_user),
    exchange_service: ExchangeService = Depends(),
):
    """
    Return only favorited exchange accounts, including the nested Exchange object.
    """
    return exchange_service.list_favorite_accounts(current_user.id)


# ── Assets & Positions ───────────────────────────────────────────────────────

@router.get("/assets", response_model=List[AssetOrWarning])
def get_assets(
    current_user: User = Depends(deps.get_current_user),
    asset_service: AssetService = Depends(),
):
    """
    Return a consolidated view of all crypto assets across all user accounts.
    Each item is either an Asset (with allocations showing where it's held)
    or a WarningModel (for accounts with sync errors).
    """
    return asset_service.get_assets(current_user.id)


@router.get("/positions", response_model=List[Position])
def get_positions(
    exchange_account_ids: Optional[List[int]] = None,
    wallet_account_ids: Optional[List[int]] = None,
    wallet_ids: Optional[List[int]] = None,
    current_user: User = Depends(deps.get_current_user),
    asset_service: AssetService = Depends(),
):
    """
    Return all open trading positions across exchange and wallet accounts.
    Can be filtered by specific account IDs.
    """
    return asset_service.get_positions(
        user_id=current_user.id,
        exchange_account_ids=exchange_account_ids,
        wallet_account_ids=wallet_account_ids,
        wallet_ids=wallet_ids,
    )


# ── Sync ──────────────────────────────────────────────────────────────────────

@router.post("/sync", response_model=SyncResponse)
def sync_exchange_accounts(
    exchange_account_ids: Optional[List[int]] = None,
    exclude_exchange_account_ids: Optional[List[int]] = None,
    exchange_ids: Optional[List[int]] = None,
    api_key: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(deps.get_current_user),
    sync_service: SyncService = Depends(),
):
    """
    Trigger a background sync to pull trades from connected exchange accounts.
    Accounts can be filtered via query parameters.
    Returns the number of accounts queued for syncing.
    """
    return sync_service.sync_accounts(
        user_id=current_user.id,
        exchange_account_ids=exchange_account_ids,
        exclude_exchange_account_ids=exclude_exchange_account_ids,
        exchange_ids=exchange_ids,
        api_key=api_key,
        is_favorite=is_favorite,
        is_active=is_active,
    )


@router.get("/sync/status", response_model=SyncStatusResponse)
def get_sync_status(
    current_user: User = Depends(deps.get_current_user),
    sync_service: SyncService = Depends(),
):
    """
    Return the real-time sync status of all accounts for the current user.
    Reads from Redis, updated by Celery workers at each step.
    """
    return sync_service.get_sync_status(current_user.id)


@router.post("/sync/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_sync(
    request: SyncCancelRequest,
    current_user: User = Depends(deps.get_current_user),
    sync_service: SyncService = Depends(),
):
    """
    Cancel a running sync for a specific exchange or wallet account.
    The Celery worker checks Redis before each step and will stop gracefully.
    """
    sync_service.cancel_sync(
        user_id=current_user.id,
        account_id=request.account_id,
        account_type=request.account_type,
    )


@router.post("/sync/cancel-all", status_code=status.HTTP_204_NO_CONTENT)
def cancel_all_syncs(
    current_user: User = Depends(deps.get_current_user),
    sync_service: SyncService = Depends(),
):
    """
    Cancel all running sync jobs for the current user.
    """
    sync_service.cancel_all_syncs(current_user.id)


# ── Retrieve single ───────────────────────────────────────────────────────────

@router.get("/{exchange_account_id}", response_model=ExchangeAccountRead)
def get_exchange_account(
    exchange_account_id: int,
    current_user: User = Depends(deps.get_current_user),
    exchange_service: ExchangeService = Depends(),
):
    """
    Return a single exchange account by ID. Returns 404 if not found or not owned by user.
    """
    return exchange_service.get_account(current_user.id, exchange_account_id)


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch("/{exchange_account_id}", response_model=ExchangeAccountRead)
def update_exchange_account(
    exchange_account_id: int,
    update_data: ExchangeAccountUpdate,
    current_user: User = Depends(deps.get_current_user),
    exchange_service: ExchangeService = Depends(),
):
    """
    Partial update of an exchange account.
    If api_secret or passphrase are provided, they are re-encrypted before storage.
    """
    return exchange_service.update_account(
        current_user.id, exchange_account_id, update_data
    )


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{exchange_account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exchange_account(
    exchange_account_id: int,
    current_user: User = Depends(deps.get_current_user),
    exchange_service: ExchangeService = Depends(),
):
    """
    Disconnect and delete an exchange account and its stored encrypted API keys.
    """
    exchange_service.delete_account(current_user.id, exchange_account_id)
