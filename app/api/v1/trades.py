from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.trade import TradeRead
from app.schemas.trade_stats import (
    ListTrades,
    TradeStats,
    TradeResultsStats,
    TradeSummary,
    FundingStats,
    MfeMaeStats,
    TradeMetricsResponse,
)
from app.schemas.kline import KlineResponse
from app.services.trade_service import TradeService
from app.services.kline_service import KlineService

router = APIRouter(tags=["Trades"])


# ── GET /trades/symbols (must be before /{trade_id}) ──────────────────────────

@router.get("/symbols", response_model=List[str])
def get_symbols(
    trade_service: TradeService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get unique symbols traded by the user."""
    return trade_service.get_symbols(current_user.id)


# ── Stats Endpoints (must be before /{trade_id}) ──────────────────────────────

@router.get("/stats", response_model=TradeStats)
def get_stats(
    exchange_account_ids: Optional[List[int]] = Query(None, description="Filter by exchange account IDs"),
    symbols: Optional[List[str]] = Query(None, description="Filter by trading symbols"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    date_source: str = Query("close_time", description="Date source for filtering"),
    tag_ids: Optional[List[int]] = Query(None, description="Filter by tag IDs"),
    trade_service: TradeService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get overall trade statistics."""
    return trade_service.get_stats(
        user_id=current_user.id,
        exchange_account_ids=exchange_account_ids,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        date_source=date_source,
        tag_ids=tag_ids,
    )


@router.get("/stats/results", response_model=List[TradeResultsStats])
def get_stats_by_results(
    group_by: str = Query("symbol", description="Group by: symbol, account, date, month"),
    exchange_account_ids: Optional[List[int]] = Query(None, description="Filter by exchange account IDs"),
    symbols: Optional[List[str]] = Query(None, description="Filter by trading symbols"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    date_source: str = Query("close_time", description="Date source for filtering"),
    tag_ids: Optional[List[int]] = Query(None, description="Filter by tag IDs"),
    trade_service: TradeService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get trade statistics grouped by a key (symbol, account, date, month)."""
    return trade_service.get_stats_by_group(
        user_id=current_user.id,
        group_by=group_by,
        exchange_account_ids=exchange_account_ids,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        date_source=date_source,
        tag_ids=tag_ids,
    )


@router.get("/stats/tags", response_model=List[TradeResultsStats])
def get_stats_by_tags(
    exchange_account_ids: Optional[List[int]] = Query(None, description="Filter by exchange account IDs"),
    symbols: Optional[List[str]] = Query(None, description="Filter by trading symbols"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    date_source: str = Query("close_time", description="Date source for filtering"),
    trade_service: TradeService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get trade statistics grouped by tags."""
    return trade_service.get_stats_by_tags(
        user_id=current_user.id,
        exchange_account_ids=exchange_account_ids,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        date_source=date_source,
    )


@router.get("/stats/symbols", response_model=List[TradeResultsStats])
def get_stats_by_symbols(
    exchange_account_ids: Optional[List[int]] = Query(None, description="Filter by exchange account IDs"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    date_source: str = Query("close_time", description="Date source for filtering"),
    tag_ids: Optional[List[int]] = Query(None, description="Filter by tag IDs"),
    trade_service: TradeService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get trade statistics grouped by symbol."""
    return trade_service.get_stats_by_symbols(
        user_id=current_user.id,
        exchange_account_ids=exchange_account_ids,
        start_date=start_date,
        end_date=end_date,
        date_source=date_source,
        tag_ids=tag_ids,
    )


@router.get("/stats/trade-types", response_model=List[TradeResultsStats])
def get_stats_by_trade_types(
    exchange_account_ids: Optional[List[int]] = Query(None, description="Filter by exchange account IDs"),
    symbols: Optional[List[str]] = Query(None, description="Filter by trading symbols"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    date_source: str = Query("close_time", description="Date source for filtering"),
    tag_ids: Optional[List[int]] = Query(None, description="Filter by tag IDs"),
    trade_service: TradeService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get trade statistics grouped by Buy/Sell (long/short)."""
    return trade_service.get_stats_by_trade_types(
        user_id=current_user.id,
        exchange_account_ids=exchange_account_ids,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        date_source=date_source,
        tag_ids=tag_ids,
    )


@router.get("/stats/funding", response_model=FundingStats)
def get_funding_stats(
    exchange_account_ids: Optional[List[int]] = Query(None, description="Filter by exchange account IDs"),
    symbols: Optional[List[str]] = Query(None, description="Filter by trading symbols"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    trade_service: TradeService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get funding fee statistics for futures/perpetual trades."""
    return trade_service.get_funding_stats(
        user_id=current_user.id,
        exchange_account_ids=exchange_account_ids,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/stats/mfe-mae", response_model=MfeMaeStats)
def get_mfe_mae_stats(
    exchange_account_ids: Optional[List[int]] = Query(None, description="Filter by exchange account IDs"),
    symbols: Optional[List[str]] = Query(None, description="Filter by trading symbols"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    trade_service: TradeService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """
    Get Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion (MAE) statistics.
    
    MFE: Maximum unrealized profit during the trade
    MAE: Maximum unrealized loss during the trade
    """
    return trade_service.get_mfe_mae_stats(
        user_id=current_user.id,
        exchange_account_ids=exchange_account_ids,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/stats/metric", response_model=TradeMetricsResponse)
def get_metrics(
    exchange_account_ids: Optional[List[int]] = Query(None, description="Filter by exchange account IDs"),
    symbols: Optional[List[str]] = Query(None, description="Filter by trading symbols"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    trade_service: TradeService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get specific trading metrics (total trades, win rate, expectancy, etc.)."""
    return trade_service.get_metrics(
        user_id=current_user.id,
        exchange_account_ids=exchange_account_ids,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/stats/summary", response_model=TradeSummary)
def get_stats_summary(
    trade_service: TradeService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get high-level trade summary (best/worst trade, most traded symbol, etc.)."""
    return trade_service.get_summary(current_user.id)


# ── GET /trades (list with filters) ───────────────────────────────────────────

@router.get("/", response_model=ListTrades)
def list_trades(
    order_by: Optional[str] = Query(None, description="Sort field (open_time, close_time, id, size, realized_pnl)"),
    order: Optional[str] = Query(None, description="Sort direction (asc, desc)"),
    exchange_account_ids: Optional[List[int]] = Query(None, description="Filter by exchange account IDs"),
    wallet_account_ids: Optional[List[int]] = Query(None, description="Filter by wallet account IDs"),
    symbols: Optional[List[str]] = Query(None, description="Filter by trading symbols"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Page size for pagination"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    date_source: str = Query("close_time", description="Date source for filtering (open_time, close_time)"),
    side: Optional[str] = Query(None, description="Filter by trade side (Buy, Sell)"),
    min_size: Optional[float] = Query(None, ge=0, description="Minimum trade size"),
    max_size: Optional[float] = Query(None, ge=0, description="Maximum trade size"),
    days: Optional[List[str]] = Query(None, description="Filter by day of week"),
    days_group_by: str = Query("close_time", description="Group by date source for days filter"),
    min_pnl: Optional[float] = Query(None, description="Minimum realized P&L"),
    max_pnl: Optional[float] = Query(None, description="Maximum realized P&L"),
    tag_ids: Optional[List[int]] = Query(None, description="Filter by tag IDs"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Hard limit on results"),
    trade_service: TradeService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """
    List trades with 15+ filters. Returns trades with computed fields and category splits.
    """
    return trade_service.list_trades(
        user_id=current_user.id,
        order_by=order_by,
        order=order,
        exchange_account_ids=exchange_account_ids,
        wallet_account_ids=wallet_account_ids,
        symbols=symbols,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        date_source=date_source,
        side=side,
        min_size=min_size,
        max_size=max_size,
        days=days,
        days_group_by=days_group_by,
        min_pnl=min_pnl,
        max_pnl=max_pnl,
        tag_ids=tag_ids,
        limit=limit,
    )


# ── GET /trades/{trade_id} ────────────────────────────────────────────────────

@router.get("/{trade_id}", response_model=TradeRead)
def get_trade(
    trade_id: int,
    trade_service: TradeService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get a single trade by ID with computed fields."""
    return trade_service.get_trade(trade_id, current_user.id)


# ── GET /trades/{trade_id}/klines ─────────────────────────────────────────────

@router.get("/{trade_id}/klines", response_model=KlineResponse)
def get_trade_klines(
    trade_id: int,
    interval: str = Query("1h", description="Kline interval: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M"),
    exchange_name: Optional[str] = Query(None, description="Exchange name (auto-detected from trade if not provided)"),
    kline_service: KlineService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """
    Get candlestick/kline data for a specific trade.
    
    Returns OHLCV data for the trade's symbol during the trade's time window,
    with 10% buffer before and after. Useful for chart visualization.
    """
    return kline_service.get_trade_klines(
        trade_id=trade_id,
        user_id=current_user.id,
        interval=interval,
        exchange_name=exchange_name,
    )
