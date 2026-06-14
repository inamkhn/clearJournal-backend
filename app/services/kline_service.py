from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.kline import Kline, KlineResponse
from app.repositories.trade_repository import TradeRepository


# Interval durations in milliseconds
INTERVAL_MS = {
    "1m": 60 * 1000,
    "3m": 3 * 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "30m": 30 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "2h": 2 * 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "6h": 6 * 60 * 60 * 1000,
    "8h": 8 * 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
    "3d": 3 * 24 * 60 * 60 * 1000,
    "1w": 7 * 24 * 60 * 60 * 1000,
    "1M": 30 * 24 * 60 * 60 * 1000,
}


class KlineService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session
        self.trade_repo = TradeRepository(session)

    def get_trade_klines(
        self,
        trade_id: int,
        user_id: int,
        interval: str = "1h",
        exchange_name: Optional[str] = None,
    ) -> KlineResponse:
        """
        Get kline/candlestick data for a specific trade.
        Fetches data for the trade's symbol during the trade's time window.
        """
        # Get the trade
        trade = self.trade_repo.get_by_id(trade_id, user_id)
        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trade not found",
            )

        # Validate interval
        if interval not in INTERVAL_MS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid interval. Must be one of: {', '.join(INTERVAL_MS.keys())}",
            )

        # Determine time window
        open_time = trade.open_time
        close_time = trade.close_time or datetime.utcnow()

        # Add buffer before and after (10% of trade duration)
        duration_seconds = (close_time - open_time).total_seconds()
        buffer = timedelta(seconds=max(duration_seconds * 0.1, 3600))  # min 1 hour buffer
        start_time = open_time - buffer
        end_time = close_time + buffer

        # Get exchange name from trade's exchange account
        if not exchange_name and trade.exchange_account and trade.exchange_account.exchange:
            exchange_name = trade.exchange_account.exchange.name.lower()

        # Fetch klines (for now, generate mock data - replace with actual exchange API call)
        klines = self._fetch_klines(
            symbol=trade.symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            exchange_name=exchange_name or "binance",
        )

        return KlineResponse(
            symbol=trade.symbol,
            interval=interval,
            klines=klines,
            trade_open_time=trade.open_time,
            trade_close_time=trade.close_time,
            trade_side=trade.side.value if trade.side else None,
            trade_entry_price=trade.open_price,
            trade_exit_price=trade.close_price,
        )

    def _fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        exchange_name: str = "binance",
    ) -> List[Kline]:
        """
        Fetch kline data from exchange API.
        TODO: Integrate with actual exchange client when available.
        For now, returns empty list (frontend should handle this gracefully).
        """
        # This would integrate with exchange clients like:
        # from app.services.exchange_clients.binance_client import BinanceClient
        # client = BinanceClient()
        # raw_klines = client.get_klines(symbol, interval, start_time, end_time)
        # return [self._parse_kline(k) for k in raw_klines]

        # For now, return empty list
        return []

    @staticmethod
    def _parse_kline(raw: list) -> Kline:
        """Parse raw kline data from exchange API."""
        # Binance kline format:
        # [open_time, open, high, low, close, volume, close_time, quote_volume, trades, ...]
        open_time_ms = raw[0]
        close_time_ms = raw[6] if len(raw) > 6 else None

        return Kline(
            timestamp=open_time_ms,
            open_time=datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc),
            open=float(raw[1]),
            high=float(raw[2]),
            low=float(raw[3]),
            close=float(raw[4]),
            volume=float(raw[5]),
            close_time=datetime.fromtimestamp(close_time_ms / 1000, tz=timezone.utc) if close_time_ms else None,
            quote_volume=float(raw[7]) if len(raw) > 7 else 0,
            trades_count=int(raw[8]) if len(raw) > 8 else 0,
        )
