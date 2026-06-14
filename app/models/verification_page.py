from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, TIMESTAMP, Column


# ── Junction Table: verification_page_exchange_accounts ───────────────────────

class VerificationPageExchangeAccount(SQLModel, table=True):
    __tablename__ = "verification_page_exchange_accounts"

    verification_page_id: int = Field(
        foreign_key="verification_pages.id",
        primary_key=True,
    )
    exchange_account_id: int = Field(
        foreign_key="exchange_accounts.id",
        primary_key=True,
    )


# ── VerificationPage ──────────────────────────────────────────────────────────

class VerificationPageBase(SQLModel):
    page_name: str = Field(max_length=255, unique=True, index=True)
    is_active: bool = Field(default=False)
    show_pnl: bool = Field(default=False)
    show_balance: bool = Field(default=False)
    show_trade_history: bool = Field(default=False)
    show_open_future_positions: bool = Field(default=False)
    twitter_url: str = Field(default="", max_length=500)
    user_id: int = Field(foreign_key="users.id", index=True)


class VerificationPage(VerificationPageBase, table=True):
    __tablename__ = "verification_pages"

    id: Optional[int] = Field(default=None, primary_key=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    # Relationships
    exchange_account_links: List[VerificationPageExchangeAccount] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
