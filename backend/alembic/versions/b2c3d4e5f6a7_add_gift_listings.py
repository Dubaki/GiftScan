"""Add gift_listings table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'gift_listings',
        sa.Column('nft_address', sa.String(100), primary_key=True),
        sa.Column(
            'gift_slug',
            sa.String(100),
            sa.ForeignKey('gifts_catalog.slug'),
            nullable=False,
        ),
        sa.Column('serial_number', sa.Integer(), nullable=True),
        sa.Column('rarity_tier', sa.String(20), nullable=False),
        sa.Column('price_ton', sa.Numeric(), nullable=False),
        sa.Column('marketplace', sa.String(50), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.Column('sold_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_gift_listings_slug', 'gift_listings', ['gift_slug'])
    op.create_index('ix_gift_listings_sold_at', 'gift_listings', ['sold_at'])


def downgrade() -> None:
    op.drop_index('ix_gift_listings_sold_at', table_name='gift_listings')
    op.drop_index('ix_gift_listings_slug', table_name='gift_listings')
    op.drop_table('gift_listings')
