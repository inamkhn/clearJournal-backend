from typing import List, Optional, Set
from fastapi import APIRouter, Body, Depends, Query

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.tag import TagCreate, TagUpdate, TagPublic, Tag
from app.services.tag_service import TagService
from app.utils.pagination import PaginationResult
from app.schemas.common import Message

router = APIRouter(tags=["tags"])


# ── List Tags (Paginated) ─────────────────────────────────────────────────────

@router.get("/", response_model=PaginationResult[TagPublic])
def read_tags(
    trade_id: Optional[int] = Query(None, description="Filter tags used on a specific trade"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    order_by: Optional[str] = Query(
        None,
        description="Sort field",
        enum=["created_at", "updated_at", "name", "is_favorite", "trade_count"],
    ),
    order: Optional[str] = Query(
        None,
        description="Sort direction",
        enum=["asc", "desc"],
    ),
    tag_service: TagService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """List all tags for the current user with pagination and filtering."""
    return tag_service.list_tags(
        user_id=current_user.id,
        trade_id=trade_id,
        page=page,
        page_size=page_size,
        order_by=order_by,
        order=order,
    )


# ── Delete Multiple Tags (must be before /{tag_id} routes) ────────────────────

@router.delete("/", response_model=Message)
def delete_multiple_tags(
    tag_ids: Set[int] = Body(..., description="Set of tag IDs to delete"),
    tag_service: TagService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Delete multiple tags by IDs."""
    return tag_service.delete_multiple_tags(current_user.id, list(tag_ids))


# ── Create Tag ────────────────────────────────────────────────────────────────

@router.post("", response_model=Tag, status_code=201)
def create_tag(
    tag_create: TagCreate,
    tag_service: TagService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Create a new tag."""
    return tag_service.create_tag(current_user.id, tag_create)


# ── Get Single Tag ────────────────────────────────────────────────────────────

@router.get("/{tag_id}", response_model=TagPublic)
def get_tag(
    tag_id: int,
    tag_service: TagService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get a single tag by ID."""
    return tag_service.get_tag(tag_id, current_user.id)


# ── Update Tag ────────────────────────────────────────────────────────────────

@router.patch("/{tag_id}", response_model=TagPublic)
def update_tag(
    tag_id: int,
    tag_update: TagUpdate,
    tag_service: TagService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Update a tag."""
    return tag_service.update_tag(tag_id, current_user.id, tag_update)


# ── Delete Single Tag ─────────────────────────────────────────────────────────

@router.delete("/{tag_id}", response_model=Message)
def delete_tag(
    tag_id: int,
    tag_service: TagService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Delete a single tag."""
    return tag_service.delete_tag(tag_id, current_user.id)
