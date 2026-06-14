from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.product import ProductCreate, ProductUpdate, ProductRead
from app.services.product_service import ProductService

router = APIRouter(tags=["products"])


# ── List Products (Public) ────────────────────────────────────────────────────

@router.get("/", response_model=List[ProductRead])
def get_products(
    product_ids: List[int] = Query(default=[], description="Filter by product IDs"),
    name: Optional[str] = Query(None, description="Filter by product name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    order_by: Optional[str] = Query(
        None,
        description="Sort field",
        enum=["id", "name", "created_at", "updated_at"],
    ),
    order: Optional[str] = Query(
        None,
        description="Sort direction",
        enum=["asc", "desc"],
    ),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    product_service: ProductService = Depends(),
):
    """List all products with optional filters. No auth required."""
    return product_service.list_products(
        product_ids=product_ids or None,
        name=name,
        is_active=is_active,
        order_by=order_by,
        order=order,
        offset=offset,
        page_size=page_size,
    )


# ── Create Product (Admin) ────────────────────────────────────────────────────

@router.post("/", response_model=ProductRead, status_code=201)
def create_product(
    product_create: ProductCreate,
    product_service: ProductService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Create a new product. Requires authentication."""
    return product_service.create_product(product_create)


# ── Update Product (Admin) ────────────────────────────────────────────────────

@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    product_service: ProductService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Update an existing product. Requires authentication."""
    return product_service.update_product(product_id, product_update)


# ── Delete Product (Admin) ────────────────────────────────────────────────────

@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    product_service: ProductService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Delete a product. Requires authentication."""
    product_service.delete_product(product_id)
    return Response(status_code=204)
