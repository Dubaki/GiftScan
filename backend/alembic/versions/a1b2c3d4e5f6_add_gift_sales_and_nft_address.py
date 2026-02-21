"""Add gift_sales table and nft_address to market_snapshots

Revision ID: a1b2c3d4e5f6
Revises: 783fdbee8724
Create Date: 2026-02-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '783fdbee8724'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nft_address to market_snapshots so we can track individual NFTs
    # across scans and detect when they disappear (= sold).
    op.add_column(
        'market_snapshots',
        sa.Column('nft_address', sa.String(100), nullable=True),
    )
    op.create_index(
        'ix_snapshots_nft_address',
        'market_snapshots',
        ['nft_address'],
    )

    # gift_sales: records actual completed NFT sales inferred from scan diffs.
    op.create_table(
        'gift_sales',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'gift_slug',
            sa.String(100),
            sa.ForeignKey('gifts_catalog.slug'),
            nullable=False,
            index=True,
        ),
        sa.Column('nft_address', sa.String(100), nullable=False, index=True),
        sa.Column('serial_number', sa.Integer(), nullable=True),
        sa.Column('rarity_tier', sa.String(20), nullable=False),
        sa.Column('sale_price_ton', sa.Numeric(), nullable=False),
        sa.Column('marketplace', sa.String(50), nullable=False),
        sa.Column(
            'detected_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('now()'),
        ),
    )
    op.create_index(
        'ix_gift_sales_slug_tier_time',
        'gift_sales',
        ['gift_slug', 'rarity_tier', 'detected_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_gift_sales_slug_tier_time', table_name='gift_sales')
    op.drop_table('gift_sales')
    op.drop_index('ix_snapshots_nft_address', table_name='market_snapshots')
    op.drop_column('market_snapshots', 'nft_address')
