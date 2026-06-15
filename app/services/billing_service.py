"""Billing service — handles checkout, webhooks, subscription lifecycle, invoices."""
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.invoice import Invoice
from app.models.price import Price
from app.models.users import User
from app.schemas.billing import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    ChangeSubscriptionRequest,
    SubscriptionRead,
    InvoicePublic,
    AdminSubscriptionRead,
    AdminSubscriptionResponse,
    SubscriptionCounts,
)
from app.schemas.auth import Message
from app.schemas.price import PriceRead
from app.services.tap_client import tap_client
from app.utils.pagination import paginate_query, PaginationResult

logger = logging.getLogger(__name__)


class BillingService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get the user's most recent subscription."""
        return self.session.exec(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
        ).first()

    def _get_active_subscription(self, user_id: int) -> Subscription:
        """Get the user's active subscription or raise 404."""
        sub = self._get_user_subscription(user_id)
        if not sub or sub.status not in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIAL,
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found",
            )
        return sub

    def _get_price_or_404(self, price_id: int) -> Price:
        """Fetch a price by ID or raise 404."""
        price = self.session.exec(
            select(Price)
            .options(selectinload(Price.product))
            .where(Price.id == price_id)
        ).first()
        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price not found",
            )
        return price

    def _build_price_read(self, price: Price) -> Optional[PriceRead]:
        """Build PriceRead with nested product dict from a loaded Price."""
        if not price or not price.product:
            return None
        return PriceRead(
            id=price.id,
            product_id=price.product_id,
            price_amount=price.price_amount,
            price_currency=price.price_currency,
            product_period_days=price.product_period_days,
            is_active=price.is_active,
            paddle_price_id=price.paddle_price_id,
            is_annual=price.is_annual,
            is_monthly=price.is_monthly,
            created_at=price.created_at,
            updated_at=price.updated_at,
            product={
                "id": price.product.id,
                "name": price.product.name,
                "description": price.product.description,
                "account_limit": price.product.account_limit,
                "descriptive_features": price.product.descriptive_features or [],
                "is_active": price.product.is_active,
                "created_at": price.product.created_at,
                "updated_at": price.product.updated_at,
            },
        )

    def _load_price_with_product(self, price_id: int) -> Optional[Price]:
        """Load a Price with its product relationship eagerly loaded."""
        if not price_id:
            return None
        return self.session.exec(
            select(Price)
            .options(selectinload(Price.product))
            .where(Price.id == price_id)
        ).first()

    def _to_subscription_read(self, sub: Subscription) -> SubscriptionRead:
        """Convert Subscription model to read schema."""
        price = self._load_price_with_product(sub.price_id)
        price_read = self._build_price_read(price)

        # Compute account_limit from the already-loaded price/product
        account_limit = 0
        if price and price.product:
            account_limit = price.product.account_limit

        return SubscriptionRead(
            id=sub.id,
            user_id=sub.user_id,
            price_id=sub.price_id,
            next_price_id=sub.next_price_id,
            status=sub.status.value if isinstance(sub.status, SubscriptionStatus) else sub.status,
            start_date=sub.start_date,
            trial_end_date=sub.trial_end_date,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            cancel_at_period_end=sub.cancel_at_period_end,
            canceled_at=sub.canceled_at,
            ended_at=sub.ended_at,
            provider_customer_id=sub.provider_customer_id,
            provider_subscription_id=sub.provider_subscription_id,
            provider_payment_method_id=sub.provider_payment_method_id,
            created_at=sub.created_at,
            updated_at=sub.updated_at,
            retry_count=sub.retry_count,
            last_retry_at=sub.last_retry_at,
            payment_provider=sub.payment_provider,
            price=price_read,
            account_limit=account_limit,
        )

    def _to_invoice_public(self, inv: Invoice) -> InvoicePublic:
        """Convert Invoice model to public schema."""
        price = self._load_price_with_product(inv.price_id)
        price_read = self._build_price_read(price)

        return InvoicePublic(
            id=inv.id,
            user_id=inv.user_id,
            price_id=inv.price_id,
            price=price_read,
            charge_id=inv.charge_id,
            amount=inv.amount,
            currency=inv.currency,
            payment_method=inv.payment_method,
            billing_period_start=inv.billing_period_start,
            billing_period_end=inv.billing_period_end,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
            pdf_s3_path=inv.pdf_s3_path,
            invoice_url=None,
        )

    # ── Checkout ──────────────────────────────────────────────────────────────

    def create_checkout(
        self,
        user: User,
        request: CheckoutSessionRequest,
        base_url: str,
    ) -> CheckoutSessionResponse:
        """Create a Tap checkout session for the given price."""
        price = self._get_price_or_404(request.price_id)

        if not price.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price is not active",
            )

        # Calculate final amount
        amount = price.price_amount
        if request.discount_amount:
            discount = Decimal(str(request.discount_amount))
            amount = max(amount - discount, Decimal("0.01"))

        # Build redirect and webhook URLs
        redirect_url = request.return_url or f"{base_url}/billing/redirect"
        webhook_url = f"{base_url}/billing/webhooks"

        # Create charge via Tap
        metadata = {
            "user_id": str(user.id),
            "price_id": str(price.id),
            "product_id": str(price.product_id),
        }

        charge_data = tap_client.create_charge(
            amount=amount,
            currency=price.price_currency,
            customer_email=user.email,
            customer_name=user.full_name or user.email,
            redirect_url=redirect_url,
            webhook_url=webhook_url,
            metadata=metadata,
        )

        transaction_id = charge_data.get("id", "")
        checkout_url = charge_data.get("transaction_url", "")

        return CheckoutSessionResponse(
            url=checkout_url,
            transaction_id=transaction_id,
            checkout_mode="tap",
        )

    # ── Webhooks ──────────────────────────────────────────────────────────────

    def process_webhook(self, body: bytes, hash_header: Optional[str]) -> dict:
        """Process a Tap webhook event."""
        # Verify webhook signature if hash provided
        if hash_header:
            if not tap_client.verify_webhook(body, hash_header):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid webhook signature",
                )

        try:
            event = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook payload",
            )

        event_type = event.get("type", "")
        data = event.get("data", event)

        if event_type in ("charge.succeeded", "CHARGE_SUCCESS"):
            self._handle_charge_success(data)
        elif event_type in ("charge.failed", "CHARGE_FAILED"):
            self._handle_charge_failed(data)
        elif event_type in ("subscription.cancelled", "SUBSCRIPTION_CANCELLED"):
            self._handle_subscription_cancelled(data)

        return {"status": "ok"}

    def _handle_charge_success(self, data: dict) -> None:
        """Handle a successful charge — create/activate subscription + invoice."""
        metadata = data.get("metadata", {})
        user_id_str = metadata.get("user_id")
        price_id_str = metadata.get("price_id")

        if not user_id_str or not price_id_str:
            logger.warning("Charge success webhook missing metadata: %s", data)
            return

        user_id = int(user_id_str)
        price_id = int(price_id_str)
        price = self.session.get(Price, price_id)
        if not price:
            logger.error("Price %s not found in charge success", price_id)
            return

        charge_id = data.get("id", "")
        amount = Decimal(str(data.get("amount", 0)))
        currency = data.get("currency", "USD")

        # Create or update subscription
        sub = self._get_user_subscription(user_id)
        now = datetime.utcnow()
        period_end = now + timedelta(days=price.product_period_days)

        if sub and sub.status in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIAL,
            SubscriptionStatus.PAST_DUE,
        ):
            # Renewal: extend period
            sub.current_period_start = now
            sub.current_period_end = period_end
            sub.status = SubscriptionStatus.ACTIVE
            sub.cancel_at_period_end = False
            sub.canceled_at = None
            sub.retry_count = 0
            sub.payment_provider = "tap"
        else:
            # New subscription
            sub = Subscription(
                user_id=user_id,
                price_id=price_id,
                status=SubscriptionStatus.ACTIVE,
                start_date=now,
                current_period_start=now,
                current_period_end=period_end,
                payment_provider="tap",
            )
            self.session.add(sub)

        self.session.commit()

        # Create invoice (skip if already exists — e.g. redirect re-processed after webhook)
        existing_invoice = self.session.exec(
            select(Invoice).where(Invoice.charge_id == charge_id)
        ).first()
        if not existing_invoice:
            invoice = Invoice(
                user_id=user_id,
                price_id=price_id,
                charge_id=charge_id,
                amount=amount,
                currency=currency,
                billing_period_start=now,
                billing_period_end=period_end,
            )
            self.session.add(invoice)
            self.session.commit()
        logger.info("Charge success processed for user %s, charge %s", user_id, charge_id)

    def _handle_charge_failed(self, data: dict) -> None:
        """Handle a failed charge — increment retry count."""
        metadata = data.get("metadata", {})
        user_id_str = metadata.get("user_id")

        if not user_id_str:
            return

        user_id = int(user_id_str)
        sub = self._get_user_subscription(user_id)
        if sub:
            sub.retry_count += 1
            sub.last_retry_at = datetime.utcnow()
            if sub.retry_count >= 3:
                sub.status = SubscriptionStatus.PAST_DUE
            self.session.commit()

    def _handle_subscription_cancelled(self, data: dict) -> None:
        """Handle subscription cancellation from Tap."""
        metadata = data.get("metadata", {})
        user_id_str = metadata.get("user_id")

        if not user_id_str:
            return

        user_id = int(user_id_str)
        sub = self._get_user_subscription(user_id)
        if sub and sub.status == SubscriptionStatus.ACTIVE:
            sub.status = SubscriptionStatus.CANCELED
            sub.canceled_at = datetime.utcnow()
            sub.ended_at = datetime.utcnow()
            self.session.commit()

    # ── Cancel ────────────────────────────────────────────────────────────────

    def cancel_subscription(self, user_id: int) -> SubscriptionRead:
        """Cancel the user's active subscription (at period end)."""
        sub = self._get_active_subscription(user_id)

        # If provider subscription exists, cancel at Tap
        if sub.provider_subscription_id:
            try:
                tap_client.cancel_subscription(sub.provider_subscription_id)
            except Exception as e:
                logger.warning("Failed to cancel at Tap: %s", e)

        sub.cancel_at_period_end = True
        sub.canceled_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(sub)
        return self._to_subscription_read(sub)

    # ── Reactivate ────────────────────────────────────────────────────────────

    def reactivate_subscription(self, user_id: int) -> SubscriptionRead:
        """Reactivate a canceled subscription."""
        sub = self._get_user_subscription(user_id)
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found",
            )

        if sub.status == SubscriptionStatus.CANCELED:
            # Reactivate at provider if possible
            if sub.provider_subscription_id:
                try:
                    tap_client.reactivate_subscription(sub.provider_subscription_id)
                except Exception as e:
                    logger.warning("Failed to reactivate at Tap: %s", e)

            sub.status = SubscriptionStatus.ACTIVE
            sub.cancel_at_period_end = False
            sub.canceled_at = None
            sub.ended_at = None
            self.session.commit()
            self.session.refresh(sub)
        elif sub.cancel_at_period_end:
            # Just remove the cancel-at-period-end flag
            sub.cancel_at_period_end = False
            sub.canceled_at = None
            self.session.commit()
            self.session.refresh(sub)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription is not canceled",
            )

        return self._to_subscription_read(sub)

    # ── Change Plan ───────────────────────────────────────────────────────────

    def change_subscription(
        self, user_id: int, request: ChangeSubscriptionRequest
    ) -> Message:
        """Change the user's subscription plan (effective at period end)."""
        sub = self._get_active_subscription(user_id)

        new_price = self._get_price_or_404(request.price_id)
        if not new_price.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New price is not active",
            )

        if new_price.id == sub.price_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already on this plan",
            )

        sub.next_price_id = new_price.id
        self.session.commit()

        return Message(message="Plan change scheduled. It will take effect at the end of the current billing period.")

    # ── Invoices ──────────────────────────────────────────────────────────────

    def get_invoices(
        self, user_id: int, page: int = 1, page_size: int = 10
    ) -> PaginationResult[InvoicePublic]:
        """Get paginated invoices for a user."""
        statement = (
            select(Invoice)
            .where(Invoice.user_id == user_id)
            .order_by(Invoice.created_at.desc())
        )

        result = paginate_query(self.session, statement, page, page_size)

        # Convert items to InvoicePublic
        invoices = [self._to_invoice_public(inv) for inv in result.items]

        return PaginationResult(
            items=invoices,
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            has_next=result.has_next,
            has_prev=result.has_prev,
            next_page=result.next_page,
            prev_page=result.prev_page,
        )

    # ── Redirect ──────────────────────────────────────────────────────────────

    def handle_redirect(
        self, tap_id: Optional[str] = None, session_id: Optional[str] = None
    ) -> dict:
        """Handle redirect from Tap after payment. Verify charge status."""
        charge_id = tap_id or session_id
        if not charge_id:
            return {"status": "error", "message": "No charge ID provided"}

        try:
            charge_data = tap_client.get_charge(charge_id)
        except Exception as e:
            logger.error("Failed to get charge %s: %s", charge_id, e)
            return {"status": "error", "message": "Payment verification failed"}

        charge_status = charge_data.get("status", "")
        if charge_status in ("CAPTURED", "PAID"):
            # Process as success if not already processed by webhook
            self._handle_charge_success(charge_data)
            return {"status": "success", "message": "Payment confirmed"}
        elif charge_status in ("FAILED", "DECLINED"):
            return {"status": "failed", "message": "Payment was declined"}
        else:
            return {"status": "pending", "message": f"Payment status: {charge_status}"}

    # ── Admin: List Subscriptions ─────────────────────────────────────────────

    def list_admin_subscriptions(
        self,
        search: Optional[str] = None,
        status_filter: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ) -> AdminSubscriptionResponse:
        """List all subscriptions with user info for admin panel."""
        # Base query: join Subscription with User
        statement = (
            select(Subscription, User)
            .join(User, Subscription.user_id == User.id)
        )

        # Search filter (by user name or email)
        if search:
            statement = statement.where(
                (User.full_name.ilike(f"%{search}%"))
                | (User.email.ilike(f"%{search}%"))
            )

        # Status filter
        if status_filter:
            status_enums = []
            for s in status_filter:
                try:
                    status_enums.append(SubscriptionStatus(s))
                except ValueError:
                    pass
            if status_enums:
                statement = statement.where(Subscription.status.in_(status_enums))

        # Ordering
        valid_order_fields = {
            "id": Subscription.id,
            "status": Subscription.status,
            "created_at": Subscription.created_at,
            "current_period_start": Subscription.current_period_start,
            "current_period_end": Subscription.current_period_end,
            "canceled_at": Subscription.canceled_at,
            "ended_at": Subscription.ended_at,
        }
        if order_by and order_by in valid_order_fields:
            field = valid_order_fields[order_by]
            if order == "desc":
                statement = statement.order_by(field.desc())
            else:
                statement = statement.order_by(field.asc())
        else:
            statement = statement.order_by(Subscription.id.desc())

        # Get counts by status (before pagination)
        counts_query = select(
            Subscription.status, func.count(Subscription.id)
        ).group_by(Subscription.status)
        count_rows = self.session.exec(counts_query).all()
        counts_dict = {}
        for row in count_rows:
            status_val = row[0].value if isinstance(row[0], SubscriptionStatus) else row[0]
            counts_dict[status_val] = row[1]

        counts = SubscriptionCounts(
            ACTIVE=counts_dict.get("ACTIVE", 0),
            TRIAL=counts_dict.get("TRIAL", 0),
            INACTIVE=counts_dict.get("INACTIVE", 0),
            CANCELED=counts_dict.get("CANCELED", 0),
            PAST_DUE=counts_dict.get("PAST_DUE", 0),
        )

        # Paginate
        count_statement = select(func.count()).select_from(statement.subquery())
        total = self.session.exec(count_statement).one()

        offset = (page - 1) * page_size
        paginated = statement.offset(offset).limit(page_size)
        rows = self.session.exec(paginated).all()

        # Batch-load prices to avoid N+1 query
        price_ids = {sub.price_id for sub, _ in rows if sub.price_id}
        price_map: dict = {}
        if price_ids:
            prices = self.session.exec(
                select(Price)
                .options(selectinload(Price.product))
                .where(Price.id.in_(price_ids))
            ).all()
            price_map = {p.id: p for p in prices}

        # Build items
        items: List[AdminSubscriptionRead] = []
        for sub, user in rows:
            # Get plan name and price info from preloaded map
            plan_name = None
            price_amount = None
            price_currency = None
            billing_cycle = None
            account_limit = None

            price = price_map.get(sub.price_id) if sub.price_id else None
            if price:
                price_amount = price.price_amount
                price_currency = price.price_currency
                if price.is_monthly:
                    billing_cycle = "monthly"
                elif price.is_annual:
                    billing_cycle = "annual"
                else:
                    billing_cycle = f"{price.product_period_days} days"
                if price.product:
                    plan_name = price.product.name
                    account_limit = price.product.account_limit

            status_val = sub.status.value if isinstance(sub.status, SubscriptionStatus) else sub.status

            items.append(AdminSubscriptionRead(
                user_id=user.id,
                full_name=user.full_name,
                email=user.email,
                subscription_id=sub.id,
                status=status_val,
                start_date=sub.start_date,
                trial_end_date=sub.trial_end_date,
                current_period_start=sub.current_period_start,
                next_pay_date=sub.current_period_end,
                cancel_at_period_end=sub.cancel_at_period_end,
                canceled_at=sub.canceled_at,
                ended_at=sub.ended_at,
                retry_count=sub.retry_count,
                last_retry_at=sub.last_retry_at,
                created_at=sub.created_at,
                plan=plan_name,
                price_amount=price_amount,
                price_currency=price_currency,
                billing_cycle=billing_cycle,
                account_limit=account_limit,
            ))

        has_next = page * page_size < total
        has_prev = page > 1

        return AdminSubscriptionResponse(
            counts=counts,
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next,
            has_prev=has_prev,
            next_page=page + 1 if has_next else None,
            prev_page=page - 1 if has_prev else None,
        )
