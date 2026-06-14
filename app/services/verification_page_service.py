from datetime import datetime
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models.verification_page import VerificationPage, VerificationPageExchangeAccount
from app.models.exchanges import ExchangeAccount, Exchange
from app.models.trade import Trade, TradeStatus
from app.schemas.verification_page import (
    VerificationPageCreate,
    VerificationPageUpdate,
    VerificationPagePublic,
    VerificationPageBalance,
    VerificationPageExchangeAccountHistory,
)
from app.schemas.exchange import ExchangeAccountPublic, ExchangeAccountRead, ExchangeRead
from app.schemas.trade_stats import TradeStats, ListTrades
from app.schemas.position import Position
from app.services.trade_service import TradeService


class VerificationPageService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _to_public(self, page: VerificationPage) -> VerificationPagePublic:
        """Convert model to public schema."""
        return VerificationPagePublic(
            id=page.id,
            page_name=page.page_name,
            is_active=page.is_active,
            show_pnl=page.show_pnl,
            show_balance=page.show_balance,
            show_trade_history=page.show_trade_history,
            show_open_future_positions=page.show_open_future_positions,
            twitter_url=page.twitter_url,
            created_at=page.created_at,
            updated_at=page.updated_at,
        )

    def _get_page_or_404(self, page_id: int, user_id: int) -> VerificationPage:
        """Fetch a verification page, verifying ownership."""
        page = self.session.exec(
            select(VerificationPage).where(
                VerificationPage.id == page_id,
                VerificationPage.user_id == user_id,
            )
        ).first()
        if not page:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verification page not found",
            )
        return page

    def _get_page_by_name(self, page_name: str) -> VerificationPage:
        """Fetch a verification page by page_name (public, no auth check)."""
        page = self.session.exec(
            select(VerificationPage).where(
                VerificationPage.page_name == page_name,
                VerificationPage.is_active == True,
            )
        ).first()
        if not page:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verification page not found or inactive",
            )
        return page

    def _get_page_exchange_account_ids(self, page_id: int) -> List[int]:
        """Get exchange account IDs linked to a verification page."""
        links = self.session.exec(
            select(VerificationPageExchangeAccount).where(
                VerificationPageExchangeAccount.verification_page_id == page_id,
            )
        ).all()
        return [link.exchange_account_id for link in links]

    def _sync_exchange_accounts(
        self, page_id: int, exchange_account_ids: List[int]
    ) -> None:
        """Replace the exchange accounts linked to a page."""
        # Remove existing links
        existing = self.session.exec(
            select(VerificationPageExchangeAccount).where(
                VerificationPageExchangeAccount.verification_page_id == page_id,
            )
        ).all()
        for link in existing:
            self.session.delete(link)

        # Add new links
        for ea_id in exchange_account_ids:
            link = VerificationPageExchangeAccount(
                verification_page_id=page_id,
                exchange_account_id=ea_id,
            )
            self.session.add(link)

        self.session.commit()

    def _account_to_public(self, ea: ExchangeAccount) -> ExchangeAccountPublic:
        """Convert ExchangeAccount to ExchangeAccountPublic."""
        exchange = ea.exchange
        exchange_read = None
        if exchange:
            exchange_read = ExchangeRead(
                id=exchange.id,
                name=exchange.name,
                description=exchange.description,
                configs=exchange.configs,
                is_active=exchange.is_active,
                image_url=exchange.image_url,
                created_at=exchange.created_at,
                updated_at=exchange.updated_at,
            )
        return ExchangeAccountPublic(
            id=ea.id,
            name=ea.name,
            api_key=ea.api_key,
            is_favorite=ea.is_favorite,
            exchange_id=ea.exchange_id,
            user_id=ea.user_id,
            created_at=ea.created_at,
            updated_at=ea.updated_at,
            last_sync=ea.last_sync,
            error=ea.error,
            exchange=exchange_read,
        )

    # ── Admin CRUD ────────────────────────────────────────────────────────────

    def list_pages(self, user_id: int) -> List[VerificationPagePublic]:
        """List all verification pages for a user."""
        pages = self.session.exec(
            select(VerificationPage)
            .where(VerificationPage.user_id == user_id)
            .order_by(VerificationPage.created_at.desc())
        ).all()
        return [self._to_public(p) for p in pages]

    def get_page(self, page_id: int, user_id: int) -> VerificationPagePublic:
        """Get a single verification page."""
        page = self._get_page_or_404(page_id, user_id)
        return self._to_public(page)

    def create_page(
        self, user_id: int, page_create: VerificationPageCreate
    ) -> VerificationPagePublic:
        """Create a new verification page."""
        # Check if page_name is already taken
        existing = self.session.exec(
            select(VerificationPage).where(
                VerificationPage.page_name == page_create.page_name
            )
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Page name already exists",
            )

        page = VerificationPage(
            page_name=page_create.page_name,
            show_pnl=page_create.show_pnl,
            show_balance=page_create.show_balance,
            show_trade_history=page_create.show_trade_history,
            show_open_future_positions=page_create.show_open_future_positions,
            twitter_url=page_create.twitter_url,
            user_id=user_id,
        )
        self.session.add(page)
        self.session.commit()
        self.session.refresh(page)

        # Link exchange accounts
        if page_create.exchange_account_ids:
            self._sync_exchange_accounts(page.id, page_create.exchange_account_ids)

        return self._to_public(page)

    def update_page(
        self,
        page_id: int,
        user_id: int,
        page_update: VerificationPageUpdate,
    ) -> VerificationPagePublic:
        """Update a verification page."""
        page = self._get_page_or_404(page_id, user_id)

        update_data = page_update.model_dump(exclude_unset=True)

        # Handle exchange_account_ids separately
        exchange_account_ids = update_data.pop("exchange_account_ids", None)

        # Check page_name uniqueness if being updated
        if "page_name" in update_data and update_data["page_name"] != page.page_name:
            existing = self.session.exec(
                select(VerificationPage).where(
                    VerificationPage.page_name == update_data["page_name"],
                    VerificationPage.id != page_id,
                )
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Page name already exists",
                )

        for key, value in update_data.items():
            setattr(page, key, value)

        self.session.add(page)
        self.session.commit()
        self.session.refresh(page)

        # Update exchange account links if provided
        if exchange_account_ids is not None:
            self._sync_exchange_accounts(page.id, exchange_account_ids)

        return self._to_public(page)

    def delete_page(self, page_id: int, user_id: int) -> None:
        """Delete a verification page (cascade removes junction records)."""
        page = self._get_page_or_404(page_id, user_id)
        self.session.delete(page)
        self.session.commit()

    def get_page_exchange_accounts(
        self, page_id: int, user_id: int
    ) -> List[ExchangeAccountPublic]:
        """Get exchange accounts linked to a verification page."""
        self._get_page_or_404(page_id, user_id)
        ea_ids = self._get_page_exchange_account_ids(page_id)

        if not ea_ids:
            return []

        accounts = self.session.exec(
            select(ExchangeAccount)
            .options(selectinload(ExchangeAccount.exchange))
            .where(ExchangeAccount.id.in_(ea_ids))
        ).all()

        # Filter out accounts with missing exchange (schema requires exchange)
        return [self._account_to_public(ea) for ea in accounts if ea.exchange]

    # ── Public Endpoints (by page_name) ───────────────────────────────────────

    def get_page_by_name(self, page_name: str) -> VerificationPagePublic:
        """Get a verification page by its public name."""
        page = self._get_page_by_name(page_name)
        return self._to_public(page)

    def get_page_trades(
        self,
        page_name: str,
        trade_service: TradeService,
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
        """Get trades for a verification page's exchange accounts."""
        page = self._get_page_by_name(page_name)
        page_ea_ids = self._get_page_exchange_account_ids(page.id)

        # Intersect user-provided exchange_account_ids with page's accounts
        if exchange_account_ids:
            effective_ea_ids = [
                ea_id for ea_id in exchange_account_ids if ea_id in page_ea_ids
            ]
        else:
            effective_ea_ids = page_ea_ids

        if not effective_ea_ids:
            return ListTrades(items=[], total=0)

        return trade_service.list_trades(
            user_id=page.user_id,
            order_by=order_by,
            order=order,
            exchange_account_ids=effective_ea_ids,
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

    def get_page_symbols(self, page_name: str) -> List[str]:
        """Get unique symbols traded on a verification page's accounts."""
        page = self._get_page_by_name(page_name)
        page_ea_ids = self._get_page_exchange_account_ids(page.id)

        if not page_ea_ids:
            return []

        symbols = self.session.exec(
            select(Trade.symbol)
            .where(
                Trade.user_id == page.user_id,
                Trade.exchange_account_id.in_(page_ea_ids),
            )
            .distinct()
        ).all()

        return list(symbols)

    def get_page_stats(
        self,
        page_name: str,
        trade_service: TradeService,
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
    ) -> TradeStats:
        """Get trade statistics for a verification page's accounts."""
        page = self._get_page_by_name(page_name)
        page_ea_ids = self._get_page_exchange_account_ids(page.id)

        if exchange_account_ids:
            effective_ea_ids = [
                ea_id for ea_id in exchange_account_ids if ea_id in page_ea_ids
            ]
        else:
            effective_ea_ids = page_ea_ids

        if not effective_ea_ids:
            return TradeStats()

        return trade_service.get_stats(
            user_id=page.user_id,
            exchange_account_ids=effective_ea_ids,
            symbols=symbols or None,
            start_date=start_date,
            end_date=end_date,
            date_source=date_source,
            tag_ids=tag_ids or None,
        )

    def get_page_positions(self, page_name: str) -> List[Position]:
        """
        Get open positions for a verification page's exchange accounts.
        TODO: Integrate with exchange clients for live position data.
        """
        page = self._get_page_by_name(page_name)
        page_ea_ids = self._get_page_exchange_account_ids(page.id)

        if not page_ea_ids:
            return []

        # For now, compute from open trades
        open_trades = self.session.exec(
            select(Trade).where(
                Trade.user_id == page.user_id,
                Trade.exchange_account_id.in_(page_ea_ids),
                Trade.status != TradeStatus.complete,
            )
        ).all()

        positions = []
        for t in open_trades:
            positions.append(Position(
                symbol=t.symbol,
                size=t.size,
                side=t.side.value if t.side else "unknown",
                open_price=t.open_price,
                unrealized_pnl=0,  # Would need live price data
                leverage=t.leverage,
            ))

        return positions

    def get_page_balance(self, page_name: str) -> VerificationPageBalance:
        """
        Get total balance across a verification page's exchange accounts.
        TODO: Integrate with exchange clients for live balance data.
        """
        self._get_page_by_name(page_name)
        # Placeholder — would fetch from exchange APIs
        return VerificationPageBalance(balance=0.0)

    def get_page_exchange_account_history(
        self, page_name: str
    ) -> List[VerificationPageExchangeAccountHistory]:
        """Get exchange account history (first trade date/time per account)."""
        page = self._get_page_by_name(page_name)
        page_ea_ids = self._get_page_exchange_account_ids(page.id)

        if not page_ea_ids:
            return []

        # Get exchange accounts with their exchange info
        accounts = self.session.exec(
            select(ExchangeAccount)
            .options(selectinload(ExchangeAccount.exchange))
            .where(ExchangeAccount.id.in_(page_ea_ids))
        ).all()

        # Batch fetch first trade time per account to avoid N+1
        from sqlalchemy import func

        first_trades_stmt = (
            select(
                Trade.exchange_account_id,
                func.min(Trade.open_time).label("first_open_time"),
            )
            .where(Trade.exchange_account_id.in_(page_ea_ids))
            .group_by(Trade.exchange_account_id)
        )
        first_trade_rows = self.session.exec(first_trades_stmt).all()
        first_trade_map = {
            row[0]: row[1] for row in first_trade_rows
        }

        results = []
        for ea in accounts:
            first_time_val = first_trade_map.get(ea.id)
            first_date = first_time_val.date() if first_time_val else None
            first_time = first_time_val.time() if first_time_val else None

            results.append(VerificationPageExchangeAccountHistory(
                exchange_account_id=ea.id,
                exchange_account_name=ea.name,
                exchange_account_image_url=ea.exchange.image_url if ea.exchange else "",
                first_trade_date=first_date,
                first_trade_time=first_time,
            ))

        return results
