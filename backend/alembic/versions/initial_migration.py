"""initial migration

Revision ID: initial
Revises: 
Create Date: 2024-03-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create algorithms table
    op.create_table(
        'algorithms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('type', sa.Enum('moving_average_crossover', 'rsi', 'macd', 'bollinger_bands', name='algorithmtype'), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_algorithms_symbol'), 'algorithms', ['symbol'], unique=False)

    # Create signals table
    op.create_table(
        'signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('algorithm_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('buy', 'sell', 'hold', name='signaltype'), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('additional_data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['algorithm_id'], ['algorithms.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_signals_symbol'), 'signals', ['symbol'], unique=False)

    # Create positions table
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('current_price', sa.Float(), nullable=False),
        sa.Column('status', sa.Enum('open', 'closed', 'pending', name='positionstatus'), nullable=False),
        sa.Column('entry_time', sa.DateTime(), nullable=False),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_positions_symbol'), 'positions', ['symbol'], unique=False)

    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('signal_id', sa.Integer(), nullable=True),
        sa.Column('position_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('side', sa.Enum('buy', 'sell', name='tradetype'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'filled', 'cancelled', 'rejected', name='tradestatus'), nullable=False),
        sa.Column('order_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('filled_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id')
    )
    op.create_index(op.f('ix_trades_symbol'), 'trades', ['symbol'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_trades_symbol'), table_name='trades')
    op.drop_table('trades')
    op.drop_index(op.f('ix_positions_symbol'), table_name='positions')
    op.drop_table('positions')
    op.drop_index(op.f('ix_signals_symbol'), table_name='signals')
    op.drop_table('signals')
    op.drop_index(op.f('ix_algorithms_symbol'), table_name='algorithms')
    op.drop_table('algorithms') 