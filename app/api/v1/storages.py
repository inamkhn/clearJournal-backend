from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.storage import (
    StorageCreate,
    StorageUpdate,
    Storage as StorageSchema,
    ListStorage,
)
from app.schemas.asset import Asset
from app.schemas.common import Message
from app.services.storage_service import StorageService

router = APIRouter(tags=["storages"])


# ── List Storages ─────────────────────────────────────────────────────────────

@router.get("/", response_model=ListStorage)
def list_storages(
    storage_service: StorageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """List all storages for the current user."""
    return storage_service.list_storages(current_user.id)


# ── Get Storage Locations (no auth) ───────────────────────────────────────────

@router.get("/locations")
def get_storage_locations(
    storage_service: StorageService = Depends(),
):
    """Get predefined storage locations (hardware wallets, etc.)."""
    return storage_service.get_storage_locations()


# ── Get Available Assets ──────────────────────────────────────────────────────

@router.get("/assets", response_model=List[Asset])
def get_available_assets(
    q: Optional[str] = Query(None, description="Search query for asset symbol"),
    storage_service: StorageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get available assets for storage (search/autocomplete)."""
    return storage_service.get_available_assets(current_user.id, q)


# ── Create Storage ────────────────────────────────────────────────────────────

@router.post("/", response_model=StorageSchema)
def create_storage(
    storage_create: StorageCreate,
    storage_service: StorageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Create a new storage entry."""
    return storage_service.create_storage(current_user.id, storage_create)


# ── Get Single Storage ────────────────────────────────────────────────────────

@router.get("/{storage_id}", response_model=StorageSchema)
def get_storage(
    storage_id: int,
    storage_service: StorageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get a single storage by ID."""
    return storage_service.get_storage(storage_id, current_user.id)


# ── Update Storage ────────────────────────────────────────────────────────────

@router.patch("/{storage_id}", response_model=StorageSchema)
def update_storage(
    storage_id: int,
    storage_update: StorageUpdate,
    storage_service: StorageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Update a storage entry."""
    return storage_service.update_storage(storage_id, current_user.id, storage_update)


# ── Delete Storage ────────────────────────────────────────────────────────────

@router.delete("/{storage_id}", response_model=Message)
def delete_storage(
    storage_id: int,
    storage_service: StorageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Delete a storage entry."""
    return storage_service.delete_storage(storage_id, current_user.id)
