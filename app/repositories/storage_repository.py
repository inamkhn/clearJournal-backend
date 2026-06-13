from typing import Optional
from sqlmodel import Session, select

from app.models.storage import Storage
from app.schemas.storage import StorageCreate, StorageUpdate, Storage as StorageSchema, ListStorage


class StorageRepository:
    def __init__(self, session: Session):
        self.session = session

    # ── Create ────────────────────────────────────────────────────────────────

    def create(self, user_id: int, storage_create: StorageCreate) -> Storage:
        """Create a new storage entry."""
        storage = Storage(
            asset=storage_create.asset.upper(),
            location=storage_create.location,
            from_source=storage_create.from_source,
            amount=storage_create.amount,
            date=storage_create.date,
            user_id=user_id,
        )
        self.session.add(storage)
        self.session.commit()
        self.session.refresh(storage)
        return storage

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_by_id(self, storage_id: int, user_id: int) -> Optional[Storage]:
        """Get a single storage by ID, ensuring it belongs to the user."""
        statement = select(Storage).where(
            Storage.id == storage_id,
            Storage.user_id == user_id,
        )
        return self.session.exec(statement).first()

    def list_by_user(self, user_id: int) -> ListStorage:
        """List all storages for a user."""
        statement = select(Storage).where(
            Storage.user_id == user_id,
        ).order_by(Storage.created_at.desc())

        storages = self.session.exec(statement).all()
        items = [self._to_schema(s) for s in storages]

        return ListStorage(items=items, total=len(items))

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, storage: Storage, storage_update: StorageUpdate) -> Storage:
        """Update a storage entry."""
        update_data = storage_update.model_dump(exclude_unset=True)

        # Normalize asset to uppercase if provided
        if "asset" in update_data and update_data["asset"]:
            update_data["asset"] = update_data["asset"].upper()

        for key, value in update_data.items():
            setattr(storage, key, value)

        self.session.add(storage)
        self.session.commit()
        self.session.refresh(storage)
        return storage

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, storage: Storage) -> None:
        """Delete a storage entry."""
        self.session.delete(storage)
        self.session.commit()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _get_asset_image(asset: str) -> str:
        """Get icon URL for an asset. TODO: real icon service."""
        return f"/static/icons/{asset.lower()}.png"

    def _to_schema(self, storage: Storage) -> StorageSchema:
        """Convert Storage model to Storage schema."""
        return StorageSchema(
            id=storage.id,
            asset=storage.asset,
            location=storage.location,
            from_source=storage.from_source,
            amount=storage.amount,
            date=storage.date,
            notes=storage.notes,
            user_id=storage.user_id,
            image=self._get_asset_image(storage.asset),
            created_at=storage.created_at,
            updated_at=storage.updated_at,
        )
