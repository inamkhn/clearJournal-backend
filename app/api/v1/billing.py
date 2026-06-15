"""Billing API endpoints — checkout, webhooks, subscription lifecycle, invoices."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.billing import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    ChangeSubscriptionRequest,
    SubscriptionRead,
    InvoicePublic,
)
from app.schemas.auth import Message
from app.services.billing_service import BillingService
from app.utils.pagination import PaginationResult

router = APIRouter(tags=["billing"])


# ── 1. POST /billing/checkout ─────────────────────────────────────────────────

@router.post("/checkout", response_model=CheckoutSessionResponse)
def create_checkout(
    request: CheckoutSessionRequest,
    http_request: Request,
    billing_service: BillingService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Create a Tap checkout session for subscription payment."""
    base_url = str(http_request.base_url).rstrip("/")
    return billing_service.create_checkout(
        user=current_user,
        request=request,
        base_url=base_url,
    )


# ── 2. POST /billing/webhooks ─────────────────────────────────────────────────

@router.post("/webhooks")
async def webhooks(
    http_request: Request,
    billing_service: BillingService = Depends(),
):
    """Receive and process Tap payment webhook events."""
    body = await http_request.body()
    hash_header = http_request.headers.get("hashstring")
    result = billing_service.process_webhook(body=body, hash_header=hash_header)
    return result


# ── 3. POST /billing/cancel ───────────────────────────────────────────────────

@router.post("/cancel", response_model=SubscriptionRead)
def cancel_subscription(
    billing_service: BillingService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Cancel the current user's active subscription."""
    return billing_service.cancel_subscription(current_user.id)


# ── 4. POST /billing/reactivate ───────────────────────────────────────────────

@router.post("/reactivate", response_model=SubscriptionRead)
def reactivate_subscription(
    billing_service: BillingService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Reactivate a canceled subscription."""
    return billing_service.reactivate_subscription(current_user.id)


# ── 5. POST /billing/change ───────────────────────────────────────────────────

@router.post("/change", response_model=Message)
def change_subscription(
    request: ChangeSubscriptionRequest,
    billing_service: BillingService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Change subscription plan (effective at period end)."""
    return billing_service.change_subscription(current_user.id, request)


# ── 6. GET /billing/invoices ─────────────────────────────────────────────────

@router.get("/invoices", response_model=PaginationResult[InvoicePublic])
def get_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    billing_service: BillingService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get paginated invoice history for the current user."""
    return billing_service.get_invoices(current_user.id, page, page_size)


# ── 7. GET /billing/redirect ─────────────────────────────────────────────────

@router.get("/redirect")
def redirect_url(
    tap_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    billing_service: BillingService = Depends(),
):
    """Handle redirect from Tap after payment completion."""
    return billing_service.handle_redirect(tap_id=tap_id, session_id=session_id)
