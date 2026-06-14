from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductRead


class ProductService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _to_read(self, product: Product) -> ProductRead:
        """Convert model to read schema."""
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

    def _get_product_or_404(self, product_id: int) -> Product:
        """Fetch a product by ID or raise 404."""
        product = self.session.get(Product, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        return product

    # ── List ──────────────────────────────────────────────────────────────────

    def list_products(
        self,
        product_ids: Optional[List[int]] = None,
        name: Optional[str] = None,
        is_active: Optional[bool] = None,
        order_by: Optional[str] = None,
        order: Optional[str] = None,
        offset: int = 0,
        page_size: int = 10,
    ) -> List[ProductRead]:
        """List products with optional filters and pagination."""
        statement = select(Product)

        # Filters
        if product_ids:
            statement = statement.where(Product.id.in_(product_ids))
        if name:
            statement = statement.where(Product.name.ilike(f"%{name}%"))
        if is_active is not None:
            statement = statement.where(Product.is_active == is_active)

        # Ordering
        if order_by:
            order_field = getattr(Product, order_by, None)
            if order_field is not None:
                if order == "desc":
                    statement = statement.order_by(order_field.desc())
                else:
                    statement = statement.order_by(order_field.asc())
        else:
            statement = statement.order_by(Product.id.asc())

        # Pagination
        statement = statement.offset(offset).limit(page_size)

        products = self.session.exec(statement).all()
        return [self._to_read(p) for p in products]

    # ── Create ────────────────────────────────────────────────────────────────

    def create_product(self, product_create: ProductCreate) -> ProductRead:
        """Create a new product."""
        product = Product(
            name=product_create.name,
            description=product_create.description,
            account_limit=product_create.account_limit,
            is_active=product_create.is_active,
        )
        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)
        return self._to_read(product)

    # ── Update ────────────────────────────────────────────────────────────────

    def update_product(
        self, product_id: int, product_update: ProductUpdate
    ) -> ProductRead:
        """Update an existing product."""
        product = self._get_product_or_404(product_id)

        update_data = product_update.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(product, key, value)

        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)
        return self._to_read(product)

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_product(self, product_id: int) -> None:
        """Delete a product (cascade will handle related prices)."""
        product = self._get_product_or_404(product_id)
        self.session.delete(product)
        self.session.commit()
