"""add performance indexes

Revision ID: add_performance_indexes
Revises: add_performance_metrics
Create Date: 2026-03-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_performance_indexes'
down_revision: Union[str, None] = 'add_performance_metrics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Projects table indexes
    op.create_index('ix_projects_user_id_created', 'projects', ['user_id', 'created_at'])
    op.create_index('ix_projects_status', 'projects', ['status'])

    # Code files table indexes
    op.create_index('ix_code_files_project_id_language', 'code_files', ['project_id', 'language'])
    op.create_index('ix_code_files_project_id_updated', 'code_files', ['project_id', 'updated_at'])

    # Documents table indexes
    op.create_index('ix_documents_project_id_status', 'documents', ['project_id', 'status'])
    op.create_index('ix_documents_project_id_created', 'documents', ['project_id', 'created_at'])
    op.create_index('ix_documents_project_id_updated', 'documents', ['project_id', 'updated_at'])

    # Agents table indexes
    op.create_index('ix_agents_user_id_status', 'agents', ['user_id', 'status'])
    op.create_index('ix_agents_created_at', 'agents', ['created_at'])

    # Conversations table indexes
    op.create_index('ix_conversations_agent_id_created', 'conversations', ['agent_id', 'created_at'])
    op.create_index('ix_conversations_user_id_created', 'conversations', ['user_id', 'created_at'])

    # Messages table indexes
    op.create_index('ix_messages_conversation_id_created', 'messages', ['conversation_id', 'created_at'])
    op.create_index('ix_messages_role_created', 'messages', ['role', 'created_at'])

    # Training tasks table indexes
    op.create_index('ix_training_tasks_agent_id_status', 'training_tasks', ['agent_id', 'status'])
    op.create_index('ix_training_tasks_created_at', 'training_tasks', ['created_at'])


def downgrade() -> None:
    # Projects
    op.drop_index('ix_projects_status', table_name='projects')
    op.drop_index('ix_projects_user_id_created', table_name='projects')

    # Code files
    op.drop_index('ix_code_files_project_id_updated', table_name='code_files')
    op.drop_index('ix_code_files_project_id_language', table_name='code_files')

    # Documents
    op.drop_index('ix_documents_project_id_updated', table_name='documents')
    op.drop_index('ix_documents_project_id_created', table_name='documents')
    op.drop_index('ix_documents_project_id_status', table_name='documents')

    # Agents
    op.drop_index('ix_agents_created_at', table_name='agents')
    op.drop_index('ix_agents_user_id_status', table_name='agents')

    # Conversations
    op.drop_index('ix_conversations_user_id_created', table_name='conversations')
    op.drop_index('ix_conversations_agent_id_created', table_name='conversations')

    # Messages
    op.drop_index('ix_messages_role_created', table_name='messages')
    op.drop_index('ix_messages_conversation_id_created', table_name='messages')

    # Training tasks
    op.drop_index('ix_training_tasks_created_at', table_name='training_tasks')
    op.drop_index('ix_training_tasks_agent_id_status', table_name='training_tasks')
