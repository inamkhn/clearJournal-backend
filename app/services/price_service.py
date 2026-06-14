from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models.price import Price
from app.models.product import Product
from app.schemas.price import PriceCreate, PriceUpdate, PriceRead
from app.schemas.product import ProductRead


class PriceService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _to_product_read(self, product: Product) -> ProductRead:
        """Convert Product model to read schema."""
        return ProductRead(
            id=product.id,
            name=product.name,
            description=product.description,
            account_limit=product.account_limit,
            descriptive_features=product.descriptive_features or [],
            is_active=product.is_active,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )

    def _to_read(self, price: Price) -> PriceRead:
        """Convert price model to read schema with nested product."""
        product = price.product
        if not product:
            # Fallback: load product separately if relationship not loaded
            product = self.session.get(Product, price.product_id)

        product_read = self._to_product_read(product) if product else None

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
            product=product_read,
        )

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

    def _verify_product_exists(self, product_id: int) -> None:
        """Verify a product exists."""
        product = self.session.get(Product, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found",
            )

    def _compute_period_flags(self, period_days: int) -> tuple[bool, bool]:
        """Compute is_monthly and is_annual flags from period days."""
        is_monthly = 25 <= period_days <= 35  # ~30 days
        is_annual = 360 <= period_days <= 370  # ~365 days
        return is_monthly, is_annual

    # ── List ──────────────────────────────────────────────────────────────────

    def list_prices(
        self,
        price_ids: Optional[List[int]] = None,
        product_ids: Optional[List[int]] = None,
        product_period_days: Optional[int] = None,
        is_active: Optional[bool] = None,
        order_by: Optional[str] = None,
        order: Optional[str] = None,
        offset: int = 0,
        page_size: int = 10,
    ) -> List[PriceRead]:
        """List prices with optional filters and pagination."""
        statement = select(Price).options(selectinload(Price.product))

        # Filters
        if price_ids:
            statement = statement.where(Price.id.in_(price_ids))
        if product_ids:
            statement = statement.where(Price.product_id.in_(product_ids))
        if product_period_days is not None:
            statement = statement.where(Price.product_period_days == product_period_days)
        if is_active is not None:
            statement = statement.where(Price.is_active == is_active)

        # Ordering
        if order_by:
            order_field = getattr(Price, order_by, None)
            if order_field is not None:
                if order == "desc":
                    statement = statement.order_by(order_field.desc())
                else:
                    statement = statement.order_by(order_field.asc())
        else:
            statement = statement.order_by(Price.id.asc())

        # Pagination
        statement = statement.offset(offset).limit(page_size)

        prices = self.session.exec(statement).all()
        return [self._to_read(p) for p in prices]

    # ── Create ────────────────────────────────────────────────────────────────

    def create_price(self, price_create: PriceCreate) -> PriceRead:
        """Create a new price."""
        # Verify product exists
        self._verify_product_exists(price_create.product_id)

        # Compute period flags
        is_monthly, is_annual = self._compute_period_flags(price_create.product_period_days)

        price = Price(
            product_id=price_create.product_id,
            price_amount=price_create.price_amount,
            price_currency=price_create.price_currency,
            product_period_days=price_create.product_period_days,
            is_active=price_create.is_active,
            is_monthly=is_monthly,
            is_annual=is_annual,
        )
        self.session.add(price)
        self.session.commit()
        self.session.refresh(price)

        # Reload with product relationship
        loaded_price = self.session.exec(
            select(Price)
            .options(selectinload(Price.product))
            .where(Price.id == price.id)
        ).first()
        return self._to_read(loaded_price)

    # ── Update ────────────────────────────────────────────────────────────────

    def update_price(self, price_id: int, price_update: PriceUpdate) -> PriceRead:
        """Update an existing price."""
        price = self._get_price_or_404(price_id)

        update_data = price_update.model_dump(exclude_unset=True)

        # Recompute period flags if period_days is being updated
        if "product_period_days" in update_data:
            is_monthly, is_annual = self._compute_period_flags(update_data["product_period_days"])
            update_data["is_monthly"] = is_monthly
            update_data["is_annual"] = is_annual

        for key, value in update_data.items():
            setattr(price, key, value)

        self.session.add(price)
        self.session.commit()
        self.session.refresh(price)

        # Reload with product relationship
        loaded_price = self.session.exec(
            select(Price)
            .options(selectinload(Price.product))
            .where(Price.id == price.id)
        ).first()
        return self._to_read(loaded_price)

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_price(self, price_id: int) -> None:
        """Delete a price."""
        price = self._get_price_or_404(price_id)
        self.session.delete(price)
        self.session.commit()
