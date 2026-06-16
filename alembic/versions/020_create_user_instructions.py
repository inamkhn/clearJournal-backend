"""Create user_agent_instructions table

Revision ID: 020_create_user_instructions
Revises: 019_create_messages
Create Date: 2024-01-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '020_create_user_instructions'
down_revision: Union[str, None] = '019_create_messages'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_agent_instructions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('content', sa.String(length=2000), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_agent_instructions_user_id'), 'user_agent_instructions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_agent_instructions_is_active'), 'user_agent_instructions', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_agent_instructions_is_active'), table_name='user_agent_instructions')
    op.drop_index(op.f('ix_user_agent_instructions_user_id'), table_name='user_agent_instructions')
    op.drop_table('user_agent_instructions')
