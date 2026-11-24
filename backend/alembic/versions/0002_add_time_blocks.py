"""add time_blocks table

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-24
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'time_blocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('start_at', sa.DateTime(), nullable=False),
        sa.Column('end_at', sa.DateTime(), nullable=False),
        sa.Column('comment', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_time_blocks_start', 'time_blocks', ['start_at'])


def downgrade() -> None:
    op.drop_index('ix_time_blocks_start', table_name='time_blocks')
    op.drop_table('time_blocks')
