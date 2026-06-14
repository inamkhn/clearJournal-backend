"""Create subscriptions table

Revision ID: 017_create_subscriptions
Revises: 016_create_prices
Create Date: 2024-01-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '017_create_subscriptions'
down_revision: Union[str, None] = '016_create_prices'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('price_id', sa.Integer(), nullable=True),
        sa.Column('next_price_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('start_date', sa.TIMESTAMP(), nullable=True),
        sa.Column('trial_end_date', sa.TIMESTAMP(), nullable=True),
        sa.Column('current_period_start', sa.TIMESTAMP(), nullable=True),
        sa.Column('current_period_end', sa.TIMESTAMP(), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('canceled_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('ended_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('provider_customer_id', sa.String(length=255), nullable=True),
        sa.Column('provider_subscription_id', sa.String(length=255), nullable=True),
        sa.Column('provider_payment_method_id', sa.String(length=255), nullable=True),
        sa.Column('discount_id', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_retry_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('payment_provider', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['price_id'], ['prices.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['next_price_id'], ['prices.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_price_id'), 'subscriptions', ['price_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_subscriptions_status'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_price_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
