from typing import List, Optional, Dict
from collections import defaultdict
from fastapi import Depends
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.trade import Trade, TradeSide, TradeStatus
from app.schemas.trade import PositionComputed, AssetBalance


class TradeService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    # ── Position Computation ──────────────────────────────────────────────────

    def compute_positions(
        self,
        user_id: int,
        exchange_account_ids: Optional[List[int]] = None,
    ) -> List[PositionComputed]:
        """
        Compute open positions from trade history.
        Groups trades by (symbol, exchange_account_id) and calculates net position.
        """
        trades = self._get_trades(user_id, exchange_account_ids)

        # Group trades by (exchange_account_id, symbol)
        grouped: Dict[tuple, List[Trade]] = defaultdict(list)
        for trade in trades:
            key = (trade.exchange_account_id, trade.symbol)
            grouped[key].append(trade)

        positions: List[PositionComputed] = []

        for (account_id, symbol), account_trades in grouped.items():
            position = self._compute_position_from_trades(symbol, account_id, account_trades)
            if position and position.size > 0:
                positions.append(position)

        return positions

    def _compute_position_from_trades(
        self,
        symbol: str,
        exchange_account_id: int,
        trades: List[Trade],
    ) -> Optional[PositionComputed]:
        """
        Compute a single position from a list of trades for one symbol.
        Uses FIFO-like averaging: buys add to position, sells reduce it.
        """
        net_size = 0.0
        total_cost = 0.0
        leverage = None

        for trade in sorted(trades, key=lambda t: t.open_time):
            if trade.leverage:
                leverage = trade.leverage

            if trade.side == TradeSide.Buy:
                # Adding to position
                total_cost += trade.size * trade.open_price
                net_size += trade.size
            elif trade.side == TradeSide.Sell:
                # Reducing/closing position
                if net_size > 0:
                    # Calculate average entry price before reducing
                    avg_price = total_cost / net_size if net_size > 0 else 0
                    total_cost -= trade.size * avg_price
                    net_size -= trade.size

        # If net_size is zero or negative, position is closed
        if net_size <= 0:
            return None

        avg_entry_price = total_cost / net_size if net_size > 0 else 0

        # Determine side based on net position
        side = TradeSide.Buy if net_size > 0 else TradeSide.Sell

        return PositionComputed(
            symbol=symbol,
            side=side,
            size=abs(net_size),
            open_price=avg_entry_price,
            unrealized_pnl=0,  # Will be computed with current price later
            leverage=leverage,
            exchange_account_id=exchange_account_id,
        )

    # ── Asset Balance Computation ─────────────────────────────────────────────

    def compute_balances(
        self,
        user_id: int,
        exchange_account_ids: Optional[List[int]] = None,
    ) -> List[AssetBalance]:
        """
        Compute current asset balances from trade history.
        Returns net holdings per symbol per account.
        """
        trades = self._get_trades(user_id, exchange_account_ids)

        # Group trades by (exchange_account_id, symbol)
        balances: Dict[tuple, Dict] = defaultdict(lambda: {"amount": 0.0, "cost": 0.0})

        for trade in trades:
            key = (trade.exchange_account_id, trade.symbol)

            if trade.side == TradeSide.Buy:
                balances[key]["amount"] += trade.size
                balances[key]["cost"] += trade.size * trade.open_price
            elif trade.side == TradeSide.Sell:
                balances[key]["amount"] -= trade.size
                # Proportionally reduce cost basis
                if balances[key]["amount"] > 0:
                    avg_price = balances[key]["cost"] / (balances[key]["amount"] + trade.size)
                    balances[key]["cost"] -= trade.size * avg_price

        result: List[AssetBalance] = []
        for (account_id, symbol), data in balances.items():
            if data["amount"] > 0:
                avg_price = data["cost"] / data["amount"] if data["amount"] > 0 else 0
                result.append(AssetBalance(
                    symbol=symbol,
                    amount=data["amount"],
                    avg_entry_price=avg_price,
                    exchange_account_id=account_id,
                ))

        return result

    # ── Trade Queries ─────────────────────────────────────────────────────────

    def get_trades(
        self,
        user_id: int,
        exchange_account_ids: Optional[List[int]] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Trade]:
        """Get trades for a user with optional filters."""
        return self._get_trades(user_id, exchange_account_ids, symbol, limit, offset)

    def get_symbols(self, user_id: int) -> List[str]:
        """Get unique symbols traded by a user."""
        statement = (
            select(Trade.symbol)
            .where(Trade.user_id == user_id)
            .distinct()
        )
        return list(self.session.exec(statement).all())

    # ── Private ───────────────────────────────────────────────────────────────

    def _get_trades(
        self,
        user_id: int,
        exchange_account_ids: Optional[List[int]] = None,
        symbol: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Trade]:
        """Fetch trades from database with filters."""
        statement = select(Trade).where(Trade.user_id == user_id)

        if exchange_account_ids:
            statement = statement.where(Trade.exchange_account_id.in_(exchange_account_ids))

        if symbol:
            statement = statement.where(Trade.symbol == symbol)

        statement = statement.order_by(Trade.open_time.desc())

        if limit:
            statement = statement.limit(limit)
        if offset:
            statement = statement.offset(offset)

        return self.session.exec(statement).all()
