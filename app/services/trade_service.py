from datetime import datetime
from typing import List, Optional, Dict
from collections import defaultdict
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.trade import Trade, TradeSide, TradeStatus
from app.models.exchanges import ExchangeAccount
from app.schemas.trade import (
    PositionComputed,
    AssetBalance,
    TradeRead,
    TradeWithoutPNL,
    TradeItem,
)
from app.schemas.exchange import ExchangeAccountPublic, ExchangeRead
from app.schemas.trade_stats import ListTrades, TradeStats, TradeResultsStats, TradeSummary, TradeSummaryItem
from app.repositories.trade_repository import TradeRepository


class TradeService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session
        self.repo = TradeRepository(session)

    # ── List Trades (Phase 1) ─────────────────────────────────────────────────

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
    ) -> ListTrades:
        """List trades with filtering, computed fields, and category splits."""
        trades = self.repo.list_trades(
            user_id=user_id,
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

        # Convert to response schemas
        items: List[TradeItem] = []
        winning_trades: List[TradeRead] = []
        losing_trades: List[TradeRead] = []
        long_trades: List[TradeRead] = []
        short_trades: List[TradeRead] = []
        durations: List[float] = []

        for trade in trades:
            trade_read = self._to_trade_read(trade)
            items.append(trade_read)

            # Compute duration
            if trade_read.duration > 0:
                durations.append(trade_read.duration)

            # Only categorize closed trades
            if isinstance(trade_read, TradeRead):
                if trade_read.realized_pnl > 0:
                    winning_trades.append(trade_read)
                elif trade_read.realized_pnl < 0:
                    losing_trades.append(trade_read)

                if trade_read.side == TradeSide.Buy:
                    long_trades.append(trade_read)
                elif trade_read.side == TradeSide.Sell:
                    short_trades.append(trade_read)

        avg_duration = sum(durations) / len(durations) if durations else 0

        return ListTrades(
            items=items,
            total=len(trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            long_trades=long_trades,
            short_trades=short_trades,
            win_count=len(winning_trades),
            loss_count=len(losing_trades),
            avg_trade_duration=avg_duration,
            long_count=len(long_trades),
            short_count=len(short_trades),
        )

    # ── Get Single Trade ──────────────────────────────────────────────────────

    def get_trade(self, trade_id: int, user_id: int) -> TradeRead:
        """Get a single trade by ID."""
        trade = self.repo.get_by_id(trade_id, user_id)
        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trade not found",
            )
        return self._to_trade_read(trade)

    # ── Get Symbols ───────────────────────────────────────────────────────────

    def get_symbols(self, user_id: int) -> List[str]:
        """Get unique symbols traded by a user."""
        return self.repo.get_symbols(user_id)

    # ── Statistics ────────────────────────────────────────────────────────────

    def get_stats(
        self,
        user_id: int,
        exchange_account_ids: Optional[List[int]] = None,
        symbols: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        date_source: str = "close_time",
        tag_ids: Optional[List[int]] = None,
    ) -> TradeStats:
        """Calculate overall trade statistics."""
        trades = self.repo.list_trades(
            user_id=user_id,
            exchange_account_ids=exchange_account_ids,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            date_source=date_source,
            tag_ids=tag_ids,
            limit=None,
        )

        return self._compute_stats_from_trades(trades)

    def get_stats_by_group(
        self,
        user_id: int,
        group_by: str = "symbol",
        exchange_account_ids: Optional[List[int]] = None,
        symbols: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        date_source: str = "close_time",
        tag_ids: Optional[List[int]] = None,
    ) -> List[TradeResultsStats]:
        """Calculate trade statistics grouped by a key."""
        trades = self.repo.list_trades(
            user_id=user_id,
            exchange_account_ids=exchange_account_ids,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            date_source=date_source,
            tag_ids=tag_ids,
            limit=None,
        )

        # Group trades by key
        grouped: Dict[str, List[Trade]] = defaultdict(list)
        for trade in trades:
            key = self._get_group_key(trade, group_by)
            grouped[key].append(trade)

        # Compute stats for each group
        results = []
        for key, group_trades in grouped.items():
            stats = self._compute_group_stats(key, key, group_trades)
            results.append(stats)

        # Sort by total_pnl descending
        results.sort(key=lambda x: x.total_pnl, reverse=True)
        return results

    def get_stats_by_tags(
        self,
        user_id: int,
        exchange_account_ids: Optional[List[int]] = None,
        symbols: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        date_source: str = "close_time",
    ) -> List[TradeResultsStats]:
        """Calculate trade statistics grouped by tags."""
        trades = self.repo.list_trades(
            user_id=user_id,
            exchange_account_ids=exchange_account_ids,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            date_source=date_source,
            limit=None,
        )

        if not trades:
            return []

        # Get tag info for each trade
        from app.models.trade import TradeTag
        from app.models.tag import Tag

        # Build tag map (single query)
        tag_stmt = select(Tag).where(Tag.user_id == user_id)
        tags = {t.id: t for t in self.session.exec(tag_stmt).all()}

        # Build trade_id -> tag_ids map (single query - no N+1)
        trade_ids = [t.id for t in trades]
        trade_tags_stmt = select(TradeTag).where(TradeTag.trade_id.in_(trade_ids))
        trade_tags = self.session.exec(trade_tags_stmt).all()

        # Build map: trade_id -> list of tag_ids
        trade_to_tags: Dict[int, List[int]] = defaultdict(list)
        for tt in trade_tags:
            trade_to_tags[tt.trade_id].append(tt.tag_id)

        # Group trades by tag
        grouped: Dict[int, List[Trade]] = defaultdict(list)
        untagged_trades = []

        for trade in trades:
            tag_ids_for_trade = trade_to_tags.get(trade.id, [])
            if tag_ids_for_trade:
                for tag_id in tag_ids_for_trade:
                    grouped[tag_id].append(trade)
            else:
                untagged_trades.append(trade)

        results = []
        for tag_id, group_trades in grouped.items():
            tag = tags.get(tag_id)
            label = tag.name if tag else f"Tag {tag_id}"
            stats = self._compute_group_stats(str(tag_id), label, group_trades)
            results.append(stats)

        # Add untagged if any
        if untagged_trades:
            stats = self._compute_group_stats("untagged", "Untagged", untagged_trades)
            results.append(stats)

        results.sort(key=lambda x: x.total_pnl, reverse=True)
        return results

    def get_stats_by_symbols(
        self,
        user_id: int,
        exchange_account_ids: Optional[List[int]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        date_source: str = "close_time",
        tag_ids: Optional[List[int]] = None,
    ) -> List[TradeResultsStats]:
        """Calculate trade statistics grouped by symbol."""
        return self.get_stats_by_group(
            user_id=user_id,
            group_by="symbol",
            exchange_account_ids=exchange_account_ids,
            start_date=start_date,
            end_date=end_date,
            date_source=date_source,
            tag_ids=tag_ids,
        )

    def get_stats_by_trade_types(
        self,
        user_id: int,
        exchange_account_ids: Optional[List[int]] = None,
        symbols: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        date_source: str = "close_time",
        tag_ids: Optional[List[int]] = None,
    ) -> List[TradeResultsStats]:
        """Calculate trade statistics grouped by Buy/Sell."""
        trades = self.repo.list_trades(
            user_id=user_id,
            exchange_account_ids=exchange_account_ids,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            date_source=date_source,
            tag_ids=tag_ids,
            limit=None,
        )

        # Group by side
        buy_trades = [t for t in trades if t.side == TradeSide.Buy]
        sell_trades = [t for t in trades if t.side == TradeSide.Sell]

        results = []
        if buy_trades:
            stats = self._compute_group_stats("Buy", "Long Trades", buy_trades)
            results.append(stats)
        if sell_trades:
            stats = self._compute_group_stats("Sell", "Short Trades", sell_trades)
            results.append(stats)

        return results

    def get_summary(self, user_id: int) -> TradeSummary:
        """Get high-level trade summary."""
        best_trade = self.repo.get_best_trade(user_id)
        worst_trade = self.repo.get_worst_trade(user_id)
        symbol_stats = self.repo.get_symbol_stats(user_id)
        total_fees = self.repo.get_total_fees(user_id)
        total_trades = self.repo.count_trades(user_id)

        best_item = None
        if best_trade:
            best_item = TradeSummaryItem(
                id=best_trade.id,
                symbol=best_trade.symbol,
                realized_pnl=best_trade.realized_pnl,
                open_time=best_trade.open_time.isoformat() if best_trade.open_time else "",
            )

        worst_item = None
        if worst_trade:
            worst_item = TradeSummaryItem(
                id=worst_trade.id,
                symbol=worst_trade.symbol,
                realized_pnl=worst_trade.realized_pnl,
                open_time=worst_trade.open_time.isoformat() if worst_trade.open_time else "",
            )

        most_traded = None
        most_profitable = None
        if symbol_stats and len(symbol_stats) >= 2:
            if symbol_stats[0] and len(symbol_stats[0]) > 0:
                most_traded = symbol_stats[0][0]
            if symbol_stats[1] and len(symbol_stats[1]) > 0:
                most_profitable = symbol_stats[1][0]

        return TradeSummary(
            best_trade=best_item,
            worst_trade=worst_item,
            most_traded_symbol=most_traded,
            most_profitable_symbol=most_profitable,
            total_fees_paid=total_fees,
            total_trades=total_trades,
        )

    # ── Stats Helpers ─────────────────────────────────────────────────────────

    def _compute_stats_from_trades(self, trades: List[Trade]) -> TradeStats:
        """Compute overall statistics from a list of trades."""
        if not trades:
            return TradeStats()

        closed_trades = [t for t in trades if t.status == TradeStatus.complete]
        if not closed_trades:
            return TradeStats(total_trades=len(trades))

        pnls = [t.realized_pnl for t in closed_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        total_pnl = sum(pnls)
        total_wins = sum(wins)
        total_losses = abs(sum(losses))

        win_rate = len(wins) / len(closed_trades) if closed_trades else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float("inf") if total_wins > 0 else 0

        avg_win = total_wins / len(wins) if wins else 0
        avg_loss = total_losses / len(losses) if losses else 0

        # Calculate durations
        durations = []
        for t in closed_trades:
            if t.close_time and t.open_time:
                durations.append((t.close_time - t.open_time).total_seconds())
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Long/short stats
        long_trades = [t for t in closed_trades if t.side == TradeSide.Buy]
        short_trades = [t for t in closed_trades if t.side == TradeSide.Sell]
        long_wins = [t for t in long_trades if t.realized_pnl > 0]
        short_wins = [t for t in short_trades if t.realized_pnl > 0]

        long_win_rate = len(long_wins) / len(long_trades) if long_trades else 0
        short_win_rate = len(short_wins) / len(short_trades) if short_trades else 0

        # Max drawdown
        cumulative = 0
        peak = 0
        max_dd = 0
        for pnl in sorted(pnls):  # Sort to simulate chronological order
            cumulative += pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd

        return TradeStats(
            total_trades=len(trades),
            total_pnl=total_pnl,
            win_rate=win_rate,
            profit_factor=min(profit_factor, 999.99),  # Cap for JSON
            avg_win=avg_win,
            avg_loss=-avg_loss,
            largest_win=max(pnls) if pnls else 0,
            largest_loss=min(pnls) if pnls else 0,
            max_drawdown=-max_dd,
            avg_trade_duration=avg_duration,
            winning_trades=len(wins),
            losing_trades=len(losses),
            long_trades=len(long_trades),
            short_trades=len(short_trades),
            long_win_rate=long_win_rate,
            short_win_rate=short_win_rate,
            total_fees=sum(t.fees for t in trades),
        )

    def _compute_group_stats(
        self, key: str, label: str, trades: List[Trade]
    ) -> TradeResultsStats:
        """Compute statistics for a group of trades."""
        if not trades:
            return TradeResultsStats(group_key=key, group_label=label)

        closed_trades = [t for t in trades if t.status == TradeStatus.complete]
        if not closed_trades:
            return TradeResultsStats(
                group_key=key,
                group_label=label,
                total_trades=len(trades),
            )

        pnls = [t.realized_pnl for t in closed_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        total_pnl = sum(pnls)
        total_wins = sum(wins)
        total_losses = abs(sum(losses))

        win_rate = len(wins) / len(closed_trades) if closed_trades else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float("inf") if total_wins > 0 else 0

        avg_win = total_wins / len(wins) if wins else 0
        avg_loss = total_losses / len(losses) if losses else 0

        # Durations
        durations = []
        for t in closed_trades:
            if t.close_time and t.open_time:
                durations.append((t.close_time - t.open_time).total_seconds())
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Long/short
        long_trades = [t for t in closed_trades if t.side == TradeSide.Buy]
        short_trades = [t for t in closed_trades if t.side == TradeSide.Sell]
        long_wins = [t for t in long_trades if t.realized_pnl > 0]
        short_wins = [t for t in short_trades if t.realized_pnl > 0]

        long_win_rate = len(long_wins) / len(long_trades) if long_trades else 0
        short_win_rate = len(short_wins) / len(short_trades) if short_trades else 0

        return TradeResultsStats(
            group_key=key,
            group_label=label,
            total_trades=len(trades),
            total_pnl=total_pnl,
            win_rate=win_rate,
            profit_factor=min(profit_factor, 999.99),
            avg_win=avg_win,
            avg_loss=-avg_loss,
            largest_win=max(pnls) if pnls else 0,
            largest_loss=min(pnls) if pnls else 0,
            long_trades=len(long_trades),
            long_win_rate=long_win_rate,
            short_trades=len(short_trades),
            short_win_rate=short_win_rate,
            avg_trade_duration=avg_duration,
            total_fees=sum(t.fees for t in trades),
        )

    @staticmethod
    def _get_group_key(trade: Trade, group_by: str) -> str:
        """Get grouping key for a trade."""
        if group_by == "symbol":
            return trade.symbol
        elif group_by == "account":
            return str(trade.exchange_account_id)
        elif group_by == "date":
            if trade.close_time:
                return trade.close_time.strftime("%Y-%m-%d")
            return "unknown"
        elif group_by == "month":
            if trade.close_time:
                return trade.close_time.strftime("%Y-%m")
            return "unknown"
        return "other"

    # ── Schema Conversion ─────────────────────────────────────────────────────

    def _to_trade_read(self, trade: Trade) -> TradeRead:
        """Convert Trade model to TradeRead with computed fields."""
        # Computed: duration
        duration = 0.0
        now = datetime.utcnow()
        if trade.close_time and trade.open_time:
            duration = (trade.close_time - trade.open_time).total_seconds()
        elif trade.open_time:
            duration = (now - trade.open_time).total_seconds()

        # Computed: volume
        volume = trade.size * trade.open_price

        # Computed: symbol_url
        symbol_url = f"/icons/{trade.symbol.lower()}.png"

        # Computed: trade_source
        trade_source = "exchange" if trade.exchange_account_id else "wallet"

        # Build exchange_account public schema
        exchange_account_public = None
        if trade.exchange_account:
            exchange_account_public = self._to_exchange_account_public(trade.exchange_account)

        return TradeRead(
            id=trade.id,
            symbol=trade.symbol,
            side=trade.side,
            size=trade.size,
            open_time=trade.open_time,
            close_time=trade.close_time,
            open_price=trade.open_price,
            close_price=trade.close_price,
            realized_pnl=trade.realized_pnl,
            status=trade.status,
            cumulative_pnl=trade.cumulative_pnl,
            drawdown=trade.drawdown,
            rolling_peak=trade.rolling_peak,
            under_water_period=trade.under_water_period,
            leverage=trade.leverage,
            fees=trade.fees,
            exchange_account=exchange_account_public,
            wallet_account=None,  # TODO: Add when wallet trades exist
            exchange_account_id=trade.exchange_account_id,
            user_id=trade.user_id,
            duration=duration,
            volume=volume,
            symbol_url=symbol_url,
            trade_source=trade_source,
        )

    @staticmethod
    def _to_exchange_account_public(account: ExchangeAccount) -> ExchangeAccountPublic:
        """Convert ExchangeAccount to ExchangeAccountPublic."""
        exchange_read = None
        if account.exchange:
            exchange_read = ExchangeRead(
                id=account.exchange.id,
                name=account.exchange.name,
                description=account.exchange.description,
                configs=account.exchange.configs,
                is_active=account.exchange.is_active,
                image_url=account.exchange.image_url,
                created_at=account.exchange.created_at,
                updated_at=account.exchange.updated_at,
            )
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
                total_cost += trade.size * trade.open_price
                net_size += trade.size
            elif trade.side == TradeSide.Sell:
                if net_size > 0:
                    avg_price = total_cost / net_size if net_size > 0 else 0
                    total_cost -= trade.size * avg_price
                    net_size -= trade.size

        if net_size <= 0:
            return None

        avg_entry_price = total_cost / net_size if net_size > 0 else 0
        side = TradeSide.Buy if net_size > 0 else TradeSide.Sell

        return PositionComputed(
            symbol=symbol,
            side=side,
            size=abs(net_size),
            open_price=avg_entry_price,
            unrealized_pnl=0,
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

        balances: Dict[tuple, Dict] = defaultdict(lambda: {"amount": 0.0, "cost": 0.0})

        for trade in trades:
            key = (trade.exchange_account_id, trade.symbol)

            if trade.side == TradeSide.Buy:
                balances[key]["amount"] += trade.size
                balances[key]["cost"] += trade.size * trade.open_price
            elif trade.side == TradeSide.Sell:
                balances[key]["amount"] -= trade.size
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

    # ── Private ───────────────────────────────────────────────────────────────

    def _get_trades(
        self,
        user_id: int,
        exchange_account_ids: Optional[List[int]] = None,
        symbol: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Trade]:
        """Fetch trades from database with filters (for internal use by compute methods)."""
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
