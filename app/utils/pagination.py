from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel
from sqlmodel import Session, select, func

T = TypeVar("T")


class PaginationResult(BaseModel, Generic[T]):
    """Generic pagination response wrapper."""
    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool
    next_page: Optional[int] = None
    prev_page: Optional[int] = None


def paginate_query(
    session: Session,
    statement,
    page: int = 1,
    page_size: int = 10,
    schema_class=None,
) -> PaginationResult:
    """
    Execute a paginated query and return PaginationResult.

    Args:
        session: SQLModel session
        statement: SQLModel select statement (without limit/offset)
        page: Current page number (1-indexed)
        page_size: Number of items per page
        schema_class: Optional Pydantic model to convert results to
    """
    # Get total count
    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()

    # Calculate offset
    offset = (page - 1) * page_size

    # Apply pagination
    paginated_statement = statement.offset(offset).limit(page_size)
    results = session.exec(paginated_statement).all()

    # Convert to schema if provided
    if schema_class:
        items = [schema_class.model_validate(r) for r in results]
    else:
        items = list(results)

    # Calculate pagination metadata
    has_next = page * page_size < total
    has_prev = page > 1
    next_page = page + 1 if has_next else None
    prev_page = page - 1 if has_prev else None

    return PaginationResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=has_next,
        has_prev=has_prev,
        next_page=next_page,
        prev_page=prev_page,
    )
