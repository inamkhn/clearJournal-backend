from typing import List, Optional, Dict
from collections import defaultdict
from fastapi import Depends
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models.exchanges import ExchangeAccount
from app.models.wallet import WalletAccount
from app.schemas.asset import (
    Asset,
    AssetItemExchange,
    AssetItemWallet,
    WarningModel,
    AssetOrWarning,
)
from app.schemas.exchange import ExchangeAccountPublic, ExchangeRead
from app.schemas.wallet_account import WalletAccountPublic
from app.schemas.wallet import WalletRead
from app.schemas.position import Position
from app.schemas.trade import TradeSide
from app.services.trade_service import TradeService


class AssetService:
    def __init__(
        self,
        session: Session = Depends(get_session),
        trade_service: TradeService = Depends(),
    ):
        self.session = session
        self.trade_service = trade_service

    # ── Assets ────────────────────────────────────────────────────────────────

    def get_assets(self, user_id: int) -> List[AssetOrWarning]:
        """
        Return consolidated view of all crypto assets across user's accounts.
        Groups holdings by symbol, includes allocations and warnings for broken accounts.
        """
        # symbol -> list of allocations
        asset_map: Dict[str, List] = defaultdict(list)
        warnings: List[WarningModel] = []

        # 1. Fetch exchange accounts with their exchange info
        exchange_accounts = self._get_exchange_accounts(user_id)
        account_ids = [acc.id for acc in exchange_accounts]

        # Compute balances from trade history
        balances = self.trade_service.compute_balances(user_id, account_ids)

        # Group balances by exchange_account_id
        balances_by_account: Dict[int, List] = defaultdict(list)
        for bal in balances:
            balances_by_account[bal.exchange_account_id].append(bal)

        for account in exchange_accounts:
            # Check for sync errors
            if account.error:
                warnings.append(WarningModel(
                    warning=account.error,
                    account_id=account.id,
                    exchange=account.exchange.name if account.exchange else None,
                ))
                continue

            # Get balances for this account
            account_balances = balances_by_account.get(account.id, [])

            for bal in account_balances:
                # TODO: Get real price from price service
                price = bal.avg_entry_price  # Use entry price as fallback
                value = bal.amount * price

                asset_map[bal.symbol].append(AssetItemExchange(
                    amount=bal.amount,
                    value=value,
                    exchange_account=self._to_exchange_account_public(account),
                    price_asset=price,
                ))

        # 2. Fetch wallet accounts with their wallet info
        wallet_accounts = self._get_wallet_accounts(user_id)
        for account in wallet_accounts:
            if account.error:
                warnings.append(WarningModel(
                    warning=account.error,
                    account_id=account.id,
                    wallet_id=account.wallet_id,
                    wallet=account.wallet.name if account.wallet else None,
                ))
                continue

            # TODO: Replace with real balance fetching from wallet clients
            # Wallet balances require blockchain API integration
            wallet_balances = []  # placeholder

            for bal in wallet_balances:
                price = 0.0  # placeholder
                value = bal["amount"] * price

                asset_map[bal["symbol"]].append(AssetItemWallet(
                    amount=bal["amount"],
                    value=value,
                    price_asset=price,
                    wallet=self._to_wallet_account_read(account),
                ))

        # 3. Convert to Asset objects with totals
        assets: List[Asset] = []
        for symbol, allocations in asset_map.items():
            total_amount = sum(a.amount for a in allocations)
            total_value = sum(a.value for a in allocations)
            # Use the first allocation's price as representative
            price = allocations[0].price_asset if allocations else 0.0

            assets.append(Asset(
                symbol=symbol,
                allocations=allocations,
                amount=total_amount,
                price=price,
                value=total_value,
                image=f"/icons/{symbol.lower()}.png",  # TODO: Real icon lookup
            ))

        # Sort by value descending
        assets.sort(key=lambda a: a.value, reverse=True)

        # Return combined list: assets first, then warnings
        return assets + warnings

    # ── Positions ─────────────────────────────────────────────────────────────

    def get_positions(
        self,
        user_id: int,
        exchange_account_ids: Optional[List[int]] = None,
        wallet_account_ids: Optional[List[int]] = None,
        wallet_ids: Optional[List[int]] = None,
    ) -> List[Position]:
        """
        Return all open positions across exchange and wallet accounts.
        Positions are computed from trade history.
        """
        positions: List[Position] = []

        # 1. Get exchange positions from trade history
        exchange_accounts = self._get_exchange_accounts(user_id, exchange_account_ids)
        account_ids = [acc.id for acc in exchange_accounts]

        # Build lookup for exchange accounts
        accounts_by_id = {acc.id: acc for acc in exchange_accounts}

        # Compute positions from trade history
        computed_positions = self.trade_service.compute_positions(user_id, account_ids)

        for pos in computed_positions:
            account = accounts_by_id.get(pos.exchange_account_id)
            if not account or account.error:
                continue

            positions.append(Position(
                exchange_account=self._to_exchange_account_public(account),
                wallet_account=None,
                symbol=pos.symbol,
                size=pos.size,
                side="long" if pos.side == TradeSide.Buy else "short",
                open_price=pos.open_price,
                unrealized_pnl=pos.unrealized_pnl,  # TODO: Compute with current price
                leverage=pos.leverage,
            ))

        # 2. Get wallet positions (requires blockchain API - placeholder)
        # wallet_accounts = self._get_wallet_accounts(user_id, wallet_account_ids, wallet_ids)
        # TODO: Implement wallet position fetching from blockchain APIs

        # Sort by absolute unrealized_pnl descending
        positions.sort(key=lambda p: abs(p.unrealized_pnl), reverse=True)
        return positions

    # ── Private: Data fetching ────────────────────────────────────────────────

    def _get_exchange_accounts(
        self, user_id: int, account_ids: Optional[List[int]] = None
    ) -> List[ExchangeAccount]:
        """Fetch exchange accounts with eager-loaded exchange relationship."""
        statement = (
            select(ExchangeAccount)
            .options(selectinload(ExchangeAccount.exchange))
            .where(ExchangeAccount.user_id == user_id)
        )
        if account_ids:
            statement = statement.where(ExchangeAccount.id.in_(account_ids))
        return self.session.exec(statement).all()

    def _get_wallet_accounts(
        self,
        user_id: int,
        account_ids: Optional[List[int]] = None,
        wallet_ids: Optional[List[int]] = None,
    ) -> List[WalletAccount]:
        """Fetch wallet accounts with eager-loaded wallet relationship."""
        statement = (
            select(WalletAccount)
            .options(selectinload(WalletAccount.wallet))
            .where(WalletAccount.user_id == user_id)
        )
        if account_ids:
            statement = statement.where(WalletAccount.id.in_(account_ids))
        if wallet_ids:
            statement = statement.where(WalletAccount.wallet_id.in_(wallet_ids))
        return self.session.exec(statement).all()

    # ── Private: Schema conversion ────────────────────────────────────────────

    @staticmethod
    def _to_exchange_account_public(account: ExchangeAccount) -> ExchangeAccountPublic:
        """Convert ExchangeAccount ORM model to ExchangeAccountPublic schema."""
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

    @staticmethod
    def _to_wallet_account_read(account: WalletAccount) -> WalletAccountRead:
        """Convert WalletAccount ORM model to WalletAccountRead schema."""
        wallet_read = None
        if account.wallet:
            wallet_read = WalletRead(
                id=account.wallet.id,
                name=account.wallet.name,
                description=account.wallet.description,
                configs=account.wallet.configs,
                is_active=account.wallet.is_active,
                image_url=account.wallet.image_url,
                created_at=account.wallet.created_at,
                updated_at=account.wallet.updated_at,
            )
        return WalletAccountRead(
            id=account.id,
            wallet_address=account.wallet_address,
            name=account.name,
            is_active=account.is_active,
            is_favorite=account.is_favorite,
            is_verified=account.is_verified,
            user_id=account.user_id,
            wallet_id=account.wallet_id,
            api_wallet_address=account.api_wallet_address,
            last_sync=account.last_sync,
            error=account.error,
            created_at=account.created_at,
            updated_at=account.updated_at,
            wallet=wallet_read,  # Include the wallet info
        )

    @staticmethod
    def _to_wallet_account_public(account: WalletAccount) -> WalletAccountPublic:
        """Convert WalletAccount ORM model to WalletAccountPublic schema."""
        # Reuse _to_wallet_account_read to get wallet info, then extract it
        read_schema = AssetService._to_wallet_account_read(account)
        return WalletAccountPublic(
            id=read_schema.id,
            wallet_address=read_schema.wallet_address,
            name=read_schema.name,
            is_active=read_schema.is_active,
            is_favorite=read_schema.is_favorite,
            is_verified=read_schema.is_verified,
            user_id=read_schema.user_id,
            wallet_id=read_schema.wallet_id,
            api_wallet_address=read_schema.api_wallet_address,
            last_sync=read_schema.last_sync,
            error=read_schema.error,
            created_at=read_schema.created_at,
            updated_at=read_schema.updated_at,
            wallet=read_schema.wallet,
        )
