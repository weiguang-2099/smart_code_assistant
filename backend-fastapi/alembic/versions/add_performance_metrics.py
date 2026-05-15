"""add performance metrics tables

Revision ID: add_performance_metrics
Revises: 3802a655e6fc
Create Date: 2026-03-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_performance_metrics'
down_revision: Union[str, None] = '3802a655e6fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'performance_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('response_time_ms', sa.Float(), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('request_size', sa.Integer(), nullable=True),
        sa.Column('response_size', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('client_ip', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('meta_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_performance_metrics_id', 'performance_metrics', ['id'])
    op.create_index('ix_performance_metrics_metric_type', 'performance_metrics', ['metric_type'])
    op.create_index('ix_performance_metrics_endpoint', 'performance_metrics', ['endpoint'])
    op.create_index('ix_performance_metrics_response_time_ms', 'performance_metrics', ['response_time_ms'])
    op.create_index('ix_performance_metrics_status_code', 'performance_metrics', ['status_code'])
    op.create_index('ix_performance_metrics_user_id', 'performance_metrics', ['user_id'])
    op.create_index('ix_performance_metrics_created_at', 'performance_metrics', ['created_at'])
    op.create_index('ix_performance_metrics_endpoint_created', 'performance_metrics', ['endpoint', 'created_at'])
    op.create_index('ix_performance_metrics_type_created', 'performance_metrics', ['metric_type', 'created_at'])

    op.create_table(
        'performance_baselines',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('p50_ms', sa.Float(), nullable=False),
        sa.Column('p95_ms', sa.Float(), nullable=False),
        sa.Column('p99_ms', sa.Float(), nullable=False),
        sa.Column('avg_ms', sa.Float(), nullable=False),
        sa.Column('min_ms', sa.Float(), nullable=False),
        sa.Column('max_ms', sa.Float(), nullable=False),
        sa.Column('sample_count', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_performance_baselines_id', 'performance_baselines', ['id'])
    op.create_index('ix_performance_baselines_endpoint', 'performance_baselines', ['endpoint'])
    op.create_index('ix_performance_baselines_endpoint_method', 'performance_baselines', ['endpoint', 'method'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_performance_baselines_endpoint_method', table_name='performance_baselines')
    op.drop_index('ix_performance_baselines_endpoint', table_name='performance_baselines')
    op.drop_index('ix_performance_baselines_id', table_name='performance_baselines')
    op.drop_table('performance_baselines')

    op.drop_index('ix_performance_metrics_type_created', table_name='performance_metrics')
    op.drop_index('ix_performance_metrics_endpoint_created', table_name='performance_metrics')
    op.drop_index('ix_performance_metrics_created_at', table_name='performance_metrics')
    op.drop_index('ix_performance_metrics_user_id', table_name='performance_metrics')
    op.drop_index('ix_performance_metrics_status_code', table_name='performance_metrics')
    op.drop_index('ix_performance_metrics_response_time_ms', table_name='performance_metrics')
    op.drop_index('ix_performance_metrics_endpoint', table_name='performance_metrics')
    op.drop_index('ix_performance_metrics_metric_type', table_name='performance_metrics')
    op.drop_index('ix_performance_metrics_id', table_name='performance_metrics')
    op.drop_table('performance_metrics')
