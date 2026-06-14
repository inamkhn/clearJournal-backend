from typing import List, Optional
from sqlmodel import SQLModel

from app.schemas.trade import TradeRead, TradeItem


# ── List Trades Response ──────────────────────────────────────────────────────

class ListTrades(SQLModel):
    """Response schema for listing trades with computed statistics."""
    items: List[TradeItem]
    total: int
    winning_trades: List[TradeRead] = []
    losing_trades: List[TradeRead] = []
    long_trades: List[TradeRead] = []
    short_trades: List[TradeRead] = []
    win_count: int = 0
    loss_count: int = 0
    avg_trade_duration: float = 0  # seconds
    long_count: int = 0
    short_count: int = 0


# ── Overall Statistics ────────────────────────────────────────────────────────

class TradeStats(SQLModel):
    """Overall trade statistics."""
    total_trades: int = 0
    total_pnl: float = 0
    win_rate: float = 0
    profit_factor: float = 0
    avg_win: float = 0
    avg_loss: float = 0
    largest_win: float = 0
    largest_loss: float = 0
    max_drawdown: float = 0
    avg_trade_duration: float = 0  # seconds
    winning_trades: int = 0
    losing_trades: int = 0
    long_trades: int = 0
    short_trades: int = 0
    long_win_rate: float = 0
    short_win_rate: float = 0
    total_fees: float = 0


# ── Grouped Statistics ────────────────────────────────────────────────────────

class TradeResultsStats(SQLModel):
    """Trade statistics grouped by a key (symbol, date, account, tag, etc.)."""
    group_key: str
    group_label: str
    total_trades: int = 0
    total_pnl: float = 0
    win_rate: float = 0
    profit_factor: float = 0
    avg_win: float = 0
    avg_loss: float = 0
    largest_win: float = 0
    largest_loss: float = 0
    long_trades: int = 0
    long_win_rate: float = 0
    short_trades: int = 0
    short_win_rate: float = 0
    avg_trade_duration: float = 0  # seconds
    total_fees: float = 0


# ── Summary Statistics ────────────────────────────────────────────────────────

class TradeSummaryItem(SQLModel):
    """A single trade summary item."""
    id: int
    symbol: str
    realized_pnl: float
    open_time: str


class TradeSummary(SQLModel):
    """High-level trade summary with best/worst trades."""
    best_trade: Optional[TradeSummaryItem] = None
    worst_trade: Optional[TradeSummaryItem] = None
    most_traded_symbol: Optional[str] = None
    most_profitable_symbol: Optional[str] = None
    total_fees_paid: float = 0
    total_trades: int = 0


# ── Funding Statistics ────────────────────────────────────────────────────────

class FundingStats(SQLModel):
    """Funding fee statistics for futures/perpetual trades."""
    total_funding_paid: float = 0
    total_funding_received: float = 0
    net_funding: float = 0
    avg_funding_rate: float = 0
    funding_count: int = 0
    symbols_with_funding: List[str] = []


# ── MFE/MAE Statistics ───────────────────────────────────────────────────────

class TradeMfeMae(SQLModel):
    """MFE/MAE data for a single trade."""
    trade_id: int
    symbol: str
    side: str
    entry_price: float
    exit_price: Optional[float] = None
    mfe: float = 0  # Maximum Favorable Excursion (best unrealized during trade)
    mae: float = 0  # Maximum Adverse Excursion (worst unrealized during trade)
    mfe_pct: float = 0  # MFE as percentage
    mae_pct: float = 0  # MAE as percentage
    realized_pnl: float = 0
    efficiency: float = 0  # realized_pnl / mfe (how much of the move was captured)


class MfeMaeStats(SQLModel):
    """Aggregated MFE/MAE statistics."""
    items: List[TradeMfeMae] = []
    avg_mfe: float = 0
    avg_mae: float = 0
    avg_mfe_pct: float = 0
    avg_mae_pct: float = 0
    avg_efficiency: float = 0
    best_efficiency: float = 0
    worst_efficiency: float = 0


# ── Metric Statistics ─────────────────────────────────────────────────────────

class TradeMetric(SQLModel):
    """A specific trading metric."""
    metric_name: str
    metric_value: float
    metric_label: str
    description: str = ""
    unit: str = ""  # e.g., "$", "%", "trades"


class TradeMetricsResponse(SQLModel):
    """Response with specific trading metrics."""
    metrics: List[TradeMetric] = []
