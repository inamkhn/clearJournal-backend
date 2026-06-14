from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Column, JSON, TIMESTAMP, Relationship

if TYPE_CHECKING:
    from app.models.price import Price


class ProductBase(SQLModel):
    name: str = Field(index=True, max_length=255)
    description: str = Field(default="")
    account_limit: int = Field(default=0, ge=0)
    descriptive_features: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON)
    )
    is_active: bool = Field(default=True)


class Product(ProductBase, table=True):
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Relationships
    prices: List["Price"] = Relationship(back_populates="product")
