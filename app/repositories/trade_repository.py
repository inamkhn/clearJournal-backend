from datetime import datetime
from typing import List, Optional
from sqlmodel import Session, select, func
from sqlalchemy import extract
from sqlalchemy.orm import selectinload

from app.models.trade import Trade, TradeTag, TradeSide, TradeStatus
from app.models.exchanges import ExchangeAccount


# Day name to PostgreSQL day-of-week mapping
DAY_MAP = {
    "Sunday": 0,
    "Monday": 1,
    "Tuesday": 2,
    "Wednesday": 3,
    "Thursday": 4,
    "Friday": 5,
    "Saturday": 6,
}


class TradeRepository:
    def __init__(self, session: Session):
        self.session = session

    # ── List Trades (complex filtering) ───────────────────────────────────────

    def list_trades(
        self,
        user_id: int,
        order_by: Optional[str] = None,
        order: Optional[str] = None,
        exchange_account_ids: Optional[List[int]] = None,
        wallet_account_ids: Optional[List[int]] = None,
        symbols: Optional[List[str]] = None,
        page_size: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        date_source: str = "close_time",
        side: Optional[str] = None,
        min_size: Optional[float] = None,
        max_size: Optional[float] = None,
        days: Optional[List[str]] = None,
        days_group_by: str = "close_time",
        min_pnl: Optional[float] = None,
        max_pnl: Optional[float] = None,
        tag_ids: Optional[List[int]] = None,
        limit: Optional[int] = None,
    ) -> List[Trade]:
        """
        List trades with 15+ filters. Returns trades with eager-loaded exchange_account.
        """
        statement = (
            select(Trade)
            .options(selectinload(Trade.exchange_account).selectinload(ExchangeAccount.exchange))
            .where(Trade.user_id == user_id)
        )

        # Account filters (OR'd together)
        account_filters = []
        if exchange_account_ids:
            account_filters.append(Trade.exchange_account_id.in_(exchange_account_ids))
        # Note: wallet_account_ids and wallet_ids would be added when wallet trade model exists

        if account_filters:
            if len(account_filters) == 1:
                statement = statement.where(account_filters[0])
            else:
                from sqlalchemy import or_
                statement = statement.where(or_(*account_filters))

        # Symbol filter
        if symbols:
            statement = statement.where(Trade.symbol.in_(symbols))

        # Date range filter
        date_col = Trade.close_time if date_source == "close_time" else Trade.open_time
        if start_date:
            statement = statement.where(date_col >= start_date)
        if end_date:
            statement = statement.where(date_col <= end_date)

        # Side filter
        if side:
            try:
                side_enum = TradeSide(side)
                statement = statement.where(Trade.side == side_enum)
            except ValueError:
                pass

        # Size range
        if min_size is not None:
            statement = statement.where(Trade.size >= min_size)
        if max_size is not None:
            statement = statement.where(Trade.size <= max_size)

        # P&L range
        if min_pnl is not None:
            statement = statement.where(Trade.realized_pnl >= min_pnl)
        if max_pnl is not None:
            statement = statement.where(Trade.realized_pnl <= max_pnl)

        # Day-of-week filter
        if days:
            day_nums = [DAY_MAP[d] for d in days if d in DAY_MAP]
            if day_nums:
                day_date_col = Trade.close_time if days_group_by == "close_time" else Trade.open_time
                statement = statement.where(
                    extract("dow", day_date_col).in_(day_nums)
                )

        # Tag filter (via trade_tags association)
        if tag_ids:
            statement = statement.where(
                Trade.id.in_(
                    select(TradeTag.trade_id).where(TradeTag.tag_id.in_(tag_ids))
                )
            )

        # Ordering
        order_col_map = {
            "open_time": Trade.open_time,
            "close_time": Trade.close_time,
            "id": Trade.id,
            "size": Trade.size,
            "realized_pnl": Trade.realized_pnl,
        }
        order_col = order_col_map.get(order_by, Trade.close_time)
        if order == "asc":
            statement = statement.order_by(order_col.asc())
        else:
            statement = statement.order_by(order_col.desc())

        # Pagination
        if limit:
            statement = statement.limit(limit)
        elif page_size:
            statement = statement.limit(page_size)

        return self.session.exec(statement).all()

    def count_trades(self, user_id: int) -> int:
        """Count total trades for a user."""
        statement = select(func.count()).select_from(Trade).where(Trade.user_id == user_id)
        return self.session.exec(statement).one()

    # ── Get Single Trade ──────────────────────────────────────────────────────

    def get_by_id(self, trade_id: int, user_id: int) -> Optional[Trade]:
        """Get a single trade with eager-loaded relationships."""
        statement = (
            select(Trade)
            .options(selectinload(Trade.exchange_account).selectinload(ExchangeAccount.exchange))
            .where(Trade.id == trade_id, Trade.user_id == user_id)
        )
        return self.session.exec(statement).first()

    # ── Get Unique Symbols ────────────────────────────────────────────────────

    def get_symbols(self, user_id: int) -> List[str]:
        """Get unique symbols traded by a user."""
        statement = (
            select(Trade.symbol)
            .where(Trade.user_id == user_id)
            .distinct()
            .order_by(Trade.symbol)
        )
        return list(self.session.exec(statement).all())

    # ── Stats Queries ─────────────────────────────────────────────────────────

    def get_best_trade(self, user_id: int) -> Optional[Trade]:
        """Get the trade with highest realized P&L."""
        statement = (
            select(Trade)
            .where(Trade.user_id == user_id, Trade.status == TradeStatus.complete)
            .order_by(Trade.realized_pnl.desc())
            .limit(1)
        )
        return self.session.exec(statement).first()

    def get_worst_trade(self, user_id: int) -> Optional[Trade]:
        """Get the trade with lowest realized P&L."""
        statement = (
            select(Trade)
            .where(Trade.user_id == user_id, Trade.status == TradeStatus.complete)
            .order_by(Trade.realized_pnl.asc())
            .limit(1)
        )
        return self.session.exec(statement).first()

    def get_symbol_stats(self, user_id: int) -> List[tuple]:
        """Get symbol with most trades and most profitable symbol."""
        # Most traded symbol
        most_traded_stmt = (
            select(Trade.symbol, func.count(Trade.id).label("count"))
            .where(Trade.user_id == user_id)
            .group_by(Trade.symbol)
            .order_by(func.count(Trade.id).desc())
            .limit(1)
        )
        most_traded = self.session.exec(most_traded_stmt).first()

        # Most profitable symbol
        most_profitable_stmt = (
            select(Trade.symbol, func.sum(Trade.realized_pnl).label("total_pnl"))
            .where(Trade.user_id == user_id, Trade.status == "complete")
            .group_by(Trade.symbol)
            .order_by(func.sum(Trade.realized_pnl).desc())
            .limit(1)
        )
        most_profitable = self.session.exec(most_profitable_stmt).first()

        return [most_traded, most_profitable]

    def get_total_fees(self, user_id: int) -> float:
        """Get total fees paid by user."""
        statement = (
            select(func.sum(Trade.fees))
            .where(Trade.user_id == user_id)
        )
        result = self.session.exec(statement).one()
        return float(result) if result else 0.0
