from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from app.db.session import get_session
from app.repositories.storage_repository import StorageRepository
from app.schemas.storage import (
    StorageCreate,
    StorageUpdate,
    Storage as StorageSchema,
    ListStorage,
    StoragePublic,
)
from app.schemas.common import Message
from app.schemas.asset import Asset, AssetItemStorage


class StorageService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session
        self.repo = StorageRepository(session)

    # ── Predefined Storage Locations ──────────────────────────────────────────

    STORAGE_LOCATIONS = {
        "Ledger Nano S": {"name": "Ledger Nano S", "image": "/static/locations/ledger-nano-s.png"},
        "Ledger Nano X": {"name": "Ledger Nano X", "image": "/static/locations/ledger-nano-x.png"},
        "Trezor Model T": {"name": "Trezor Model T", "image": "/static/locations/trezor-model-t.png"},
        "Trezor One": {"name": "Trezor One", "image": "/static/locations/trezor-one.png"},
        "Paper Wallet": {"name": "Paper Wallet", "image": "/static/locations/paper.png"},
        "Other": {"name": "Other", "image": "/static/locations/other.png"},
    }

    # ── Create ────────────────────────────────────────────────────────────────

    def create_storage(self, user_id: int, storage_create: StorageCreate) -> StorageSchema:
        """Create a new storage entry."""
        storage = self.repo.create(user_id, storage_create)
        return self.repo._to_schema(storage)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_storage(self, storage_id: int, user_id: int) -> StorageSchema:
        """Get a single storage by ID."""
        storage = self.repo.get_by_id(storage_id, user_id)
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage not found",
            )
        return self.repo._to_schema(storage)

    def list_storages(self, user_id: int) -> ListStorage:
        """List all storages for a user."""
        return self.repo.list_by_user(user_id)

    def get_storage_locations(self) -> dict:
        """Get predefined storage locations."""
        return self.STORAGE_LOCATIONS

    def get_available_assets(self, user_id: int, query: Optional[str] = None) -> List[Asset]:
        """
        Get available assets for storage (search).
        Returns assets matching the query, used for autocomplete.
        """
        # Get all storages for the user
        storages_result = self.repo.list_by_user(user_id)
        storages = storages_result.items

        # Filter by query if provided
        if query:
            query_upper = query.upper()
            storages = [s for s in storages if query_upper in s.asset.upper()]

        # Group by asset symbol
        asset_map = {}
        for s in storages:
            symbol = s.asset
            if symbol not in asset_map:
                asset_map[symbol] = {
                    "symbol": symbol,
                    "allocations": [],
                    "total_amount": 0,
                    "image": s.image,
                }
            asset_map[symbol]["allocations"].append(
                AssetItemStorage(
                    storage=StoragePublic(
                        id=s.id,
                        asset=s.asset,
                        location=s.location,
                        amount=s.amount,
                        image=s.image,
                    ),
                    amount=s.amount,
                    value=0,  # TODO: Compute with price service
                    price_asset=0,  # TODO: Get from price service
                )
            )
            asset_map[symbol]["total_amount"] += s.amount

        # Convert to Asset objects
        assets = []
        for symbol, data in asset_map.items():
            assets.append(Asset(
                symbol=symbol,
                allocations=data["allocations"],
                amount=data["total_amount"],
                image=data["image"],
                price=0,  # TODO: Get from price service
                value=0,  # TODO: Compute amount * price
            ))

        return assets

    # ── Update ────────────────────────────────────────────────────────────────

    def update_storage(
        self, storage_id: int, user_id: int, storage_update: StorageUpdate
    ) -> StorageSchema:
        """Update a storage entry."""
        storage = self.repo.get_by_id(storage_id, user_id)
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage not found",
            )

        storage = self.repo.update(storage, storage_update)
        return self.repo._to_schema(storage)

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_storage(self, storage_id: int, user_id: int) -> Message:
        """Delete a storage entry."""
        storage = self.repo.get_by_id(storage_id, user_id)
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage not found",
            )

        self.repo.delete(storage)
        return Message(message="Storage deleted successfully")
