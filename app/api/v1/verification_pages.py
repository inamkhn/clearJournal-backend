from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.verification_page import (
    VerificationPageCreate,
    VerificationPageUpdate,
    VerificationPagePublic,
    VerificationPageBalance,
    VerificationPageExchangeAccountHistory,
)
from app.schemas.exchange import ExchangeAccountPublic
from app.schemas.trade_stats import TradeStats, ListTrades
from app.schemas.position import Position
from app.services.verification_page_service import VerificationPageService
from app.services.trade_service import TradeService

router = APIRouter(tags=["verification-pages"])


# ════════════════════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS (require auth)
# ════════════════════════════════════════════════════════════════════════════════

# ── List All Verification Pages ───────────────────────────────────────────────

@router.get("/", response_model=List[VerificationPagePublic])
def get_all_verification_page(
    vp_service: VerificationPageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """List all verification pages for the current user."""
    return vp_service.list_pages(current_user.id)


# ── Create Verification Page ──────────────────────────────────────────────────

@router.post("/", response_model=VerificationPagePublic, status_code=201)
def create_verification_page(
    page_create: VerificationPageCreate,
    vp_service: VerificationPageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Create a new verification page."""
    return vp_service.create_page(current_user.id, page_create)


# ── Get Verification Page ─────────────────────────────────────────────────────

@router.get("/{verification_page_id}", response_model=VerificationPagePublic)
def get_verification_page(
    verification_page_id: int,
    vp_service: VerificationPageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get a single verification page by ID."""
    return vp_service.get_page(verification_page_id, current_user.id)


# ── Update Verification Page ──────────────────────────────────────────────────

@router.patch("/{verification_page_id}", response_model=VerificationPagePublic)
def update_verification_page(
    verification_page_id: int,
    page_update: VerificationPageUpdate,
    vp_service: VerificationPageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Update a verification page."""
    return vp_service.update_page(
        verification_page_id, current_user.id, page_update
    )


# ── Delete Verification Page ──────────────────────────────────────────────────

@router.delete("/{verification_page_id}", status_code=204)
def delete_verification_page(
    verification_page_id: int,
    vp_service: VerificationPageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Delete a verification page."""
    vp_service.delete_page(verification_page_id, current_user.id)
    return Response(status_code=204)


# ── Get Verification Page Exchange Accounts ───────────────────────────────────

@router.get(
    "/{verification_page_id}/exchange-accounts",
    response_model=List[ExchangeAccountPublic],
)
def get_verification_page_exchange_accounts(
    verification_page_id: int,
    vp_service: VerificationPageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get exchange accounts linked to a verification page."""
    return vp_service.get_page_exchange_accounts(
        verification_page_id, current_user.id
    )


# ════════════════════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS (lookup by page_name, no auth)
# ════════════════════════════════════════════════════════════════════════════════

# ── Get Verification Page By Name (Settings) ──────────────────────────────────

@router.get("/{page_name}/settings", response_model=VerificationPagePublic)
def get_verification_page_by_name(
    page_name: str,
    vp_service: VerificationPageService = Depends(),
):
    """Get a verification page's settings by its public name."""
    return vp_service.get_page_by_name(page_name)


# ── Get Trades ────────────────────────────────────────────────────────────────

@router.get("/{page_name}/trades", response_model=ListTrades)
def get_trades(
    page_name: str,
    order_by: Optional[str] = Query(None, description="Order by field"),
    order: Optional[str] = Query(None, description="asc or desc"),
    exchange_account_ids: List[int] = Query(default=[], description="Filter by exchange account IDs"),
    wallet_account_ids: List[int] = Query(default=[], description="Filter by wallet account IDs"),
    wallet_ids: List[int] = Query(default=[], description="Filter by wallet IDs"),
    symbols: List[str] = Query(default=[], description="Filter by symbols"),
    page_size: Optional[int] = Query(None, description="Page size"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    date_source: str = Query("close_time", description="Date source for filtering"),
    side: Optional[str] = Query(None, description="Trade side filter"),
    min_size: Optional[float] = Query(None, description="Min size filter"),
    max_size: Optional[float] = Query(None, description="Max size filter"),
    days: List[str] = Query(default=[], description="Day of week filter"),
    days_group_by: str = Query("close_time", description="Day group by source"),
    min_pnl: Optional[float] = Query(None, description="Min PnL filter"),
    max_pnl: Optional[float] = Query(None, description="Max PnL filter"),
    tag_ids: List[int] = Query(default=[], description="Tag IDs filter"),
    limit: Optional[int] = Query(None, description="Limit"),
    vp_service: VerificationPageService = Depends(),
    trade_service: TradeService = Depends(),
):
    """Get trades for a verification page's exchange accounts."""
    return vp_service.get_page_trades(
        page_name=page_name,
        trade_service=trade_service,
        order_by=order_by,
        order=order,
        exchange_account_ids=exchange_account_ids or None,
        wallet_account_ids=wallet_account_ids or None,
        symbols=symbols or None,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        date_source=date_source,
        side=side,
        min_size=min_size,
        max_size=max_size,
        days=days or None,
        days_group_by=days_group_by,
        min_pnl=min_pnl,
        max_pnl=max_pnl,
        tag_ids=tag_ids or None,
        limit=limit,
    )


# ── Get Symbols ───────────────────────────────────────────────────────────────

@router.get("/{page_name}/trades/symbols", response_model=List[str])
def symbols(
    page_name: str,
    vp_service: VerificationPageService = Depends(),
):
    """Get unique symbols traded on a verification page."""
    return vp_service.get_page_symbols(page_name)


# ── Get Stats ─────────────────────────────────────────────────────────────────

@router.get("/{page_name}/stats", response_model=TradeStats)
def get_stats(
    page_name: str,
    order_by: Optional[str] = Query(None, description="Order by field"),
    order: Optional[str] = Query(None, description="asc or desc"),
    exchange_account_ids: List[int] = Query(default=[], description="Filter by exchange account IDs"),
    wallet_account_ids: List[int] = Query(default=[], description="Filter by wallet account IDs"),
    wallet_ids: List[int] = Query(default=[], description="Filter by wallet IDs"),
    symbols: List[str] = Query(default=[], description="Filter by symbols"),
    page_size: Optional[int] = Query(None, description="Page size"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    date_source: str = Query("close_time", description="Date source for filtering"),
    side: Optional[str] = Query(None, description="Trade side filter"),
    min_size: Optional[float] = Query(None, description="Min size filter"),
    max_size: Optional[float] = Query(None, description="Max size filter"),
    days: List[str] = Query(default=[], description="Day of week filter"),
    days_group_by: str = Query("close_time", description="Day group by source"),
    min_pnl: Optional[float] = Query(None, description="Min PnL filter"),
    max_pnl: Optional[float] = Query(None, description="Max PnL filter"),
    tag_ids: List[int] = Query(default=[], description="Tag IDs filter"),
    limit: Optional[int] = Query(None, description="Limit"),
    vp_service: VerificationPageService = Depends(),
    trade_service: TradeService = Depends(),
):
    """Get trade statistics for a verification page."""
    return vp_service.get_page_stats(
        page_name=page_name,
        trade_service=trade_service,
        order_by=order_by,
        order=order,
        exchange_account_ids=exchange_account_ids or None,
        wallet_account_ids=wallet_account_ids or None,
        symbols=symbols or None,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        date_source=date_source,
        side=side,
        min_size=min_size,
        max_size=max_size,
        days=days or None,
        days_group_by=days_group_by,
        min_pnl=min_pnl,
        max_pnl=max_pnl,
        tag_ids=tag_ids or None,
        limit=limit,
    )


# ── Get Positions ─────────────────────────────────────────────────────────────

@router.get("/{page_name}/positions", response_model=List[Position])
def get_positions(
    page_name: str,
    exchange_account_ids: List[int] = Query(default=[], description="Filter by exchange account IDs"),
    wallet_account_ids: List[int] = Query(default=[], description="Filter by wallet account IDs"),
    wallet_ids: List[int] = Query(default=[], description="Filter by wallet IDs"),
    vp_service: VerificationPageService = Depends(),
):
    """Get open positions for a verification page."""
    return vp_service.get_page_positions(page_name)


# ── Get Exchange Account History ──────────────────────────────────────────────

@router.get(
    "/{page_name}/exchange-account-history",
    response_model=List[VerificationPageExchangeAccountHistory],
)
def get_exchange_account_history(
    page_name: str,
    vp_service: VerificationPageService = Depends(),
):
    """Get exchange account history for a verification page."""
    return vp_service.get_page_exchange_account_history(page_name)


# ── Get Balance ───────────────────────────────────────────────────────────────

@router.get("/{page_name}/balance", response_model=VerificationPageBalance)
def get_balance(
    page_name: str,
    vp_service: VerificationPageService = Depends(),
):
    """Get total balance for a verification page."""
    return vp_service.get_page_balance(page_name)
