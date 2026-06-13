from typing import List, Optional
from sqlmodel import Session, select, func

from app.models.tag import Tag
from app.models.trade import TradeTag
from app.schemas.tag import TagCreate, TagUpdate, TagPublic
from app.utils.pagination import PaginationResult


class TagRepository:
    def __init__(self, session: Session):
        self.session = session

    # ── Create ────────────────────────────────────────────────────────────────

    def create(self, user_id: int, tag_create: TagCreate) -> Tag:
        """Create a new tag."""
        tag = Tag(
            name=tag_create.name,
            color=tag_create.color,
            is_favorite=tag_create.is_favorite,
            user_id=user_id,
        )
        self.session.add(tag)
        self.session.commit()
        self.session.refresh(tag)
        return tag

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_by_id(self, tag_id: int, user_id: int) -> Optional[Tag]:
        """Get a single tag by ID, ensuring it belongs to the user."""
        statement = select(Tag).where(
            Tag.id == tag_id,
            Tag.user_id == user_id,
        )
        return self.session.exec(statement).first()

    def get_by_name(self, name: str, user_id: int, exclude_id: Optional[int] = None) -> Optional[Tag]:
        """Check if a tag with this name already exists for the user."""
        statement = select(Tag).where(
            Tag.name == name,
            Tag.user_id == user_id,
        )
        if exclude_id:
            statement = statement.where(Tag.id != exclude_id)
        return self.session.exec(statement).first()

    def list_tags(
        self,
        user_id: int,
        trade_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
        order_by: Optional[str] = None,
        order: Optional[str] = None,
    ) -> PaginationResult[TagPublic]:
        """
        List tags with pagination and optional trade_count aggregation.
        """
        # Base query with trade count subquery
        trade_count_subquery = (
            select(
                TradeTag.tag_id,
                func.count(TradeTag.trade_id).label("count")
            )
            .group_by(TradeTag.tag_id)
            .subquery()
        )

        # Main query with LEFT JOIN to get counts
        statement = (
            select(
                Tag,
                func.coalesce(trade_count_subquery.c.count, 0).label("count_trades"),
            )
            .outerjoin(
                trade_count_subquery,
                Tag.id == trade_count_subquery.c.tag_id,
            )
            .where(Tag.user_id == user_id)
        )

        # Filter by trade_id if provided
        if trade_id:
            statement = statement.where(
                Tag.id.in_(
                    select(TradeTag.tag_id).where(TradeTag.trade_id == trade_id)
                )
            )

        # Apply ordering
        if order_by == "trade_count":
            # For subquery columns, use them directly (col() doesn't work on subquery columns)
            if order == "asc":
                statement = statement.order_by(trade_count_subquery.c.count.asc())
            else:
                statement = statement.order_by(trade_count_subquery.c.count.desc())
        else:
            # For model columns, use col() wrapper
            if order_by == "name":
                order_col = Tag.name
            elif order_by == "is_favorite":
                order_col = Tag.is_favorite
            elif order_by == "updated_at":
                order_col = Tag.updated_at
            else:  # default: created_at
                order_col = Tag.created_at

            if order == "asc":
                statement = statement.order_by(order_col.asc())
            else:
                statement = statement.order_by(order_col.desc())

        # Get total count
        count_statement = select(func.count()).select_from(
            select(Tag.id).where(Tag.user_id == user_id).subquery()
        )
        if trade_id:
            count_statement = select(func.count()).select_from(
                select(Tag.id)
                .where(Tag.user_id == user_id)
                .where(Tag.id.in_(select(TradeTag.tag_id).where(TradeTag.trade_id == trade_id)))
                .subquery()
            )
        total = self.session.exec(count_statement).one()

        # Apply pagination
        offset = (page - 1) * page_size
        paginated_statement = statement.offset(offset).limit(page_size)
        results = self.session.exec(paginated_statement).all()

        # Convert to TagPublic
        items = [
            TagPublic(
                id=tag.id,
                name=tag.name,
                color=tag.color,
                is_favorite=tag.is_favorite,
                count_trades=count_trades,
            )
            for tag, count_trades in results
        ]

        # Calculate pagination metadata
        has_next = page * page_size < total
        has_prev = page > 1

        return PaginationResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next,
            has_prev=has_prev,
            next_page=page + 1 if has_next else None,
            prev_page=page - 1 if has_prev else None,
        )

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, tag: Tag, tag_update: TagUpdate) -> Tag:
        """Update a tag."""
        update_data = tag_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tag, key, value)
        self.session.add(tag)
        self.session.commit()
        self.session.refresh(tag)
        return tag

    # ── Delete ────────────────────────────────────────────────────────────────

    def _delete_trade_tag_associations(self, tag_id: int) -> None:
        """Delete all trade_tag associations for a given tag."""
        statement = select(TradeTag).where(TradeTag.tag_id == tag_id)
        associations = self.session.exec(statement).all()
        for assoc in associations:
            self.session.delete(assoc)

    def delete(self, tag: Tag) -> None:
        """Delete a single tag (removes trade_tags associations first)."""
        self._delete_trade_tag_associations(tag.id)
        self.session.delete(tag)
        self.session.commit()

    def delete_multiple(self, tag_ids: List[int], user_id: int) -> int:
        """Delete multiple tags by IDs, returns count deleted."""
        statement = select(Tag).where(
            Tag.id.in_(tag_ids),
            Tag.user_id == user_id,
        )
        tags = self.session.exec(statement).all()
        count = 0
        for tag in tags:
            self._delete_trade_tag_associations(tag.id)
            self.session.delete(tag)
            count += 1
        self.session.commit()
        return count

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_trade_count(self, tag_id: int) -> int:
        """Get the number of trades associated with a tag."""
        statement = select(func.count()).select_from(TradeTag).where(
            TradeTag.tag_id == tag_id
        )
        return self.session.exec(statement).one()
