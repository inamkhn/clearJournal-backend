"""Create invoices table

Revision ID: 022_create_invoices
Revises: 020_create_user_instructions
Create Date: 2024-01-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '022_create_invoices'
down_revision: Union[str, None] = '020_create_user_instructions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('price_id', sa.Integer(), nullable=False),
        sa.Column('charge_id', sa.String(length=255), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('payment_method', sa.String(length=100), nullable=True),
        sa.Column('billing_period_start', sa.TIMESTAMP(), nullable=True),
        sa.Column('billing_period_end', sa.TIMESTAMP(), nullable=True),
        sa.Column('pdf_s3_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['price_id'], ['prices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_invoices_user_id'), 'invoices', ['user_id'], unique=False)
    op.create_index(op.f('ix_invoices_price_id'), 'invoices', ['price_id'], unique=False)
    op.create_index(op.f('ix_invoices_charge_id'), 'invoices', ['charge_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_invoices_charge_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_price_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_user_id'), table_name='invoices')
    op.drop_table('invoices')
