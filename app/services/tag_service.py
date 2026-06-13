from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from app.db.session import get_session
from app.repositories.tag_repository import TagRepository
from app.schemas.tag import TagCreate, TagUpdate, TagPublic, Tag as TagSchema
from app.utils.pagination import PaginationResult
from app.schemas.common import Message


class TagService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session
        self.repo = TagRepository(session)

    # ── Create ────────────────────────────────────────────────────────────────

    def create_tag(self, user_id: int, tag_create: TagCreate) -> TagSchema:
        """Create a new tag with duplicate name validation."""
        # Check for duplicate name
        existing = self.repo.get_by_name(tag_create.name, user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tag with name '{tag_create.name}' already exists",
            )

        tag = self.repo.create(user_id, tag_create)

        return TagSchema(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            is_favorite=tag.is_favorite,
            user_id=tag.user_id,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        )

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_tag(self, tag_id: int, user_id: int) -> TagPublic:
        """Get a single tag by ID."""
        tag = self.repo.get_by_id(tag_id, user_id)
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found",
            )

        count_trades = self.repo.get_trade_count(tag.id)

        return TagPublic(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            is_favorite=tag.is_favorite,
            count_trades=count_trades,
        )

    def list_tags(
        self,
        user_id: int,
        trade_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
        order_by: Optional[str] = None,
        order: Optional[str] = None,
    ) -> PaginationResult[TagPublic]:
        """List tags with pagination."""
        return self.repo.list_tags(
            user_id=user_id,
            trade_id=trade_id,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order=order,
        )

    # ── Update ────────────────────────────────────────────────────────────────

    def update_tag(self, tag_id: int, user_id: int, tag_update: TagUpdate) -> TagPublic:
        """Update a tag."""
        tag = self.repo.get_by_id(tag_id, user_id)
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found",
            )

        # Check for duplicate name if name is being updated
        if tag_update.name is not None and tag_update.name != tag.name:
            existing = self.repo.get_by_name(tag_update.name, user_id, exclude_id=tag_id)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tag with name '{tag_update.name}' already exists",
                )

        tag = self.repo.update(tag, tag_update)
        count_trades = self.repo.get_trade_count(tag.id)

        return TagPublic(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            is_favorite=tag.is_favorite,
            count_trades=count_trades,
        )

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_tag(self, tag_id: int, user_id: int) -> Message:
        """Delete a single tag."""
        tag = self.repo.get_by_id(tag_id, user_id)
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found",
            )

        self.repo.delete(tag)
        return Message(message="Tag deleted successfully")

    def delete_multiple_tags(self, user_id: int, tag_ids: List[int]) -> Message:
        """Delete multiple tags by IDs."""
        if not tag_ids:
            return Message(message="No tags to delete")

        count = self.repo.delete_multiple(tag_ids, user_id)
        return Message(message=f"{count} tag(s) deleted successfully")
