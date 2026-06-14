from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.price import PriceCreate, PriceUpdate, PriceRead
from app.services.price_service import PriceService

router = APIRouter(tags=["prices"])


# ── List Prices (Public) ──────────────────────────────────────────────────────

@router.get("/", response_model=List[PriceRead])
def get_prices(
    price_ids: List[int] = Query(default=[], description="Filter by price IDs"),
    product_ids: List[int] = Query(default=[], description="Filter by product IDs"),
    product_period_days: Optional[int] = Query(None, description="Filter by billing period days"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    order_by: Optional[str] = Query(
        None,
        description="Sort field",
        enum=["id", "product_id", "price_amount", "created_at", "updated_at"],
    ),
    order: Optional[str] = Query(
        None,
        description="Sort direction",
        enum=["asc", "desc"],
    ),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    price_service: PriceService = Depends(),
):
    """List all prices with optional filters. No auth required."""
    return price_service.list_prices(
        price_ids=price_ids or None,
        product_ids=product_ids or None,
        product_period_days=product_period_days,
        is_active=is_active,
        order_by=order_by,
        order=order,
        offset=offset,
        page_size=page_size,
    )


# ── Create Price (Admin) ──────────────────────────────────────────────────────

@router.post("/", response_model=PriceRead, status_code=201)
def create_price(
    price_create: PriceCreate,
    price_service: PriceService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Create a new price. Requires authentication."""
    return price_service.create_price(price_create)


# ── Update Price (Admin) ──────────────────────────────────────────────────────

@router.patch("/{price_id}", response_model=PriceRead)
def update_price(
    price_id: int,
    price_update: PriceUpdate,
    price_service: PriceService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Update an existing price. Requires authentication."""
    return price_service.update_price(price_id, price_update)


# ── Delete Price (Admin) ──────────────────────────────────────────────────────

@router.delete("/{price_id}", status_code=204)
def delete_price(
    price_id: int,
    price_service: PriceService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Delete a price. Requires authentication."""
    price_service.delete_price(price_id)
    return Response(status_code=204)
