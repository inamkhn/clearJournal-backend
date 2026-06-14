"""Admin API endpoints — subscription management."""
from typing import Optional, List

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_admin_user
from app.models.users import User
from app.schemas.billing import AdminSubscriptionResponse
from app.services.billing_service import BillingService

router = APIRouter(tags=["admin"])


@router.get("/subscriptions", response_model=AdminSubscriptionResponse)
def list_subscriptions(
    search: Optional[str] = Query(None, description="Search by user name or email"),
    status: List[str] = Query(default=[], description="Filter by subscription status"),
    order_by: Optional[str] = Query(
        None,
        description="Sort field",
        enum=["id", "status", "created_at", "current_period_start", "current_period_end", "canceled_at", "ended_at"],
    ),
    order: str = Query("asc", description="Sort order", enum=["asc", "desc"]),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    billing_service: BillingService = Depends(),
    current_user: User = Depends(get_admin_user),
):
    """List all subscriptions with user info (admin only)."""
    return billing_service.list_admin_subscriptions(
        search=search,
        status_filter=status,
        order_by=order_by,
        order=order,
        page=page,
        page_size=page_size,
    )
