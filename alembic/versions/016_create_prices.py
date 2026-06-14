"""Create prices table

Revision ID: 016_create_prices
Revises: 015_create_products
Create Date: 2024-01-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '016_create_prices'
down_revision: Union[str, None] = '015_create_products'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('price_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('price_currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('product_period_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('paddle_price_id', sa.String(length=255), nullable=True),
        sa.Column('is_annual', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_monthly', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_prices_product_id'), 'prices', ['product_id'], unique=False)
    op.create_index(op.f('ix_prices_is_active'), 'prices', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_prices_is_active'), table_name='prices')
    op.drop_index(op.f('ix_prices_product_id'), table_name='prices')
    op.drop_table('prices')
