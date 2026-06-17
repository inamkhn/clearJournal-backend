"""Tool executors — bridge between AI tool calls and existing services.

Each method receives the tool arguments (dict) and user_id, calls the
appropriate service, and returns a JSON-serializable result.
"""
import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlmodel import Session

from app.services.trade_service import TradeService
from app.services.asset_service import AssetService

logger = logging.getLogger(__name__)


class ToolExecutors:
    """Dispatches AI tool calls to the correct backend service."""

    def __init__(self, session: Session):
        self.session = session
        self.trade_service = TradeService(session=session)
        self.asset_service = AssetService(session=session, trade_service=self.trade_service)

    # ── Dispatch ──────────────────────────────────────────────────────────────

    async def execute(self, tool_name: str, args: Dict[str, Any], user_id: int) -> Dict:
        """Route a tool call to the correct handler."""
        handlers = {
            "get_overall_stats": self._get_overall_stats,
            "get_symbol_performance": self._get_symbol_performance,
            "get_tag_performance": self._get_tag_performance,
            "get_day_of_week_performance": self._get_day_of_week_performance,
            "get_time_of_day_performance": self._get_time_of_day_performance,
            "get_recent_trades": self._get_recent_trades,
            "get_worst_trades": self._get_worst_trades,
            "get_mfe_mae_analysis": self._get_mfe_mae_analysis,
            "get_funding_fees": self._get_funding_fees,
            "get_winning_vs_losing": self._get_winning_vs_losing,
            "get_open_positions": self._get_open_positions,
            "get_portfolio_assets": self._get_portfolio_assets,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        return await handler(args, user_id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    MAX_DAYS = 365  # 1 year (aligned with guardrails validate_tool_args)

    def _days_to_dates(self, days: Optional[int]) -> tuple:
        """Convert 'last N days' to (start_date, end_date). None = all time."""
        if not days:
            return None, None
        days = min(days, self.MAX_DAYS)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        return start_date, end_date

    # ── 1. Overall stats ─────────────────────────────────────────────────────

    async def _get_overall_stats(self, args: Dict, user_id: int) -> Dict:
        start_date, end_date = self._days_to_dates(args.get("days"))
        stats = self.trade_service.get_stats(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )
        return stats.model_dump() if hasattr(stats, "model_dump") else stats.__dict__

    # ── 2. Per-symbol performance ────────────────────────────────────────────

    async def _get_symbol_performance(self, args: Dict, user_id: int) -> Dict:
        symbol = args.get("symbol")
        start_date, end_date = self._days_to_dates(args.get("days"))

        results = self.trade_service.get_stats_by_group(
            user_id=user_id,
            group_by="symbol",
            symbols=[symbol] if symbol else None,
            start_date=start_date,
            end_date=end_date,
        )
        return {"symbols": [r.model_dump() if hasattr(r, "model_dump") else r.__dict__ for r in results]}

    # ── 3. Per-tag (strategy) performance ────────────────────────────────────

    async def _get_tag_performance(self, args: Dict, user_id: int) -> Dict:
        start_date, end_date = self._days_to_dates(args.get("days"))

        results = self.trade_service.get_stats_by_tags(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )
        return {"tags": [r.model_dump() if hasattr(r, "model_dump") else r.__dict__ for r in results]}

    # ── 4. Day-of-week performance ───────────────────────────────────────────

    async def _get_day_of_week_performance(self, args: Dict, user_id: int) -> Dict:
        start_date, end_date = self._days_to_dates(args.get("days"))

        results = self.trade_service.get_stats_by_group(
            user_id=user_id,
            group_by="day",
            start_date=start_date,
            end_date=end_date,
        )
        return {"days": [r.model_dump() if hasattr(r, "model_dump") else r.__dict__ for r in results]}

    # ── 5. Time-of-day / session performance ─────────────────────────────────

    async def _get_time_of_day_performance(self, args: Dict, user_id: int) -> Dict:
        start_date, end_date = self._days_to_dates(args.get("days"))

        results = self.trade_service.get_stats_by_group(
            user_id=user_id,
            group_by="session",
            start_date=start_date,
            end_date=end_date,
        )
        return {"sessions": [r.model_dump() if hasattr(r, "model_dump") else r.__dict__ for r in results]}

    # ── 6. Recent trades ─────────────────────────────────────────────────────

    async def _get_recent_trades(self, args: Dict, user_id: int) -> Dict:
        limit = min(args.get("limit", 10), 50)
        symbol = args.get("symbol")

        result = self.trade_service.list_trades(
            user_id=user_id,
            order_by="close_time",
            order="desc",
            symbols=[symbol] if symbol else None,
            limit=limit,
        )
        return result.model_dump() if hasattr(result, "model_dump") else result.__dict__

    # ── 7. Worst trades ──────────────────────────────────────────────────────

    async def _get_worst_trades(self, args: Dict, user_id: int) -> Dict:
        limit = min(args.get("limit", 5), 20)
        start_date, end_date = self._days_to_dates(args.get("days"))

        result = self.trade_service.list_trades(
            user_id=user_id,
            order_by="realized_pnl",
            order="asc",
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        return result.model_dump() if hasattr(result, "model_dump") else result.__dict__

    # ── 8. MFE/MAE analysis ──────────────────────────────────────────────────

    async def _get_mfe_mae_analysis(self, args: Dict, user_id: int) -> Dict:
        symbol = args.get("symbol")
        start_date, end_date = self._days_to_dates(args.get("days"))

        result = self.trade_service.get_mfe_mae_stats(
            user_id=user_id,
            symbols=[symbol] if symbol else None,
            start_date=start_date,
            end_date=end_date,
        )
        return result.model_dump() if hasattr(result, "model_dump") else result.__dict__

    # ── 9. Funding fees ──────────────────────────────────────────────────────

    async def _get_funding_fees(self, args: Dict, user_id: int) -> Dict:
        symbol = args.get("symbol")
        start_date, end_date = self._days_to_dates(args.get("days"))

        result = self.trade_service.get_funding_stats(
            user_id=user_id,
            symbols=[symbol] if symbol else None,
            start_date=start_date,
            end_date=end_date,
        )
        return result.model_dump() if hasattr(result, "model_dump") else result.__dict__

    # ── 10. Winning vs Losing characteristics ────────────────────────────────

    async def _get_winning_vs_losing(self, args: Dict, user_id: int) -> Dict:
        start_date, end_date = self._days_to_dates(args.get("days"))

        result = self.trade_service.list_trades(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=1000,
        )

        # Extract winners/losers from the ListTrades response
        data = result.model_dump() if hasattr(result, "model_dump") else result.__dict__
        winners = data.get("winning_trades", [])
        losers = data.get("losing_trades", [])

        def _summarize(trades: List[Dict]) -> Dict:
            if not trades:
                return {"count": 0}
            pnls = [t.get("realized_pnl", 0) for t in trades]
            sizes = [t.get("size", 0) for t in trades]
            durations = [t.get("duration", 0) for t in trades]
            symbols = [t.get("symbol", "") for t in trades]

            top_symbols = Counter(symbols).most_common(5)

            return {
                "count": len(trades),
                "avg_pnl": round(sum(pnls) / len(pnls), 2) if pnls else 0,
                "avg_size": round(sum(sizes) / len(sizes), 4) if sizes else 0,
                "avg_duration_hours": round(sum(durations) / len(durations), 2) if durations else 0,
                "top_symbols": [{"symbol": s, "count": c} for s, c in top_symbols],
            }

        return {
            "winners": _summarize(winners),
            "losers": _summarize(losers),
        }

    # ── 11. Open positions ───────────────────────────────────────────────────

    async def _get_open_positions(self, args: Dict, user_id: int) -> Dict:
        positions = self.asset_service.get_positions(user_id=user_id)
        return {
            "positions": [
                p.model_dump() if hasattr(p, "model_dump") else p.__dict__
                for p in positions
            ]
        }

    # ── 12. Portfolio assets ─────────────────────────────────────────────────

    async def _get_portfolio_assets(self, args: Dict, user_id: int) -> Dict:
        assets = self.asset_service.get_assets(user_id=user_id)
        return {
            "assets": [
                a.model_dump() if hasattr(a, "model_dump") else a.__dict__
                for a in assets
            ]
        }
