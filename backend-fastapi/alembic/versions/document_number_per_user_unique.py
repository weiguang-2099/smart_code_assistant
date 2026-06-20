"""make document_number unique per user instead of globally

Revision ID: doc_number_per_user_unique
Revises: add_performance_indexes
Create Date: 2026-06-20 00:00:00.000000

document_number is generated per user (DOC-YYYYMMDD-NNN, sequence scoped to the
owner). A global unique constraint makes the second user's first document of the
day collide on DOC-...-001. Replace the global unique with a composite unique on
(user_id, document_number).
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'doc_number_per_user_unique'
down_revision: Union[str, None] = 'add_performance_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the global unique index on document_number (the non-unique
    # idx_document_number lookup index is kept).
    op.drop_index('document_number', table_name='documents')
    op.create_unique_constraint(
        'uq_documents_user_document_number',
        'documents',
        ['user_id', 'document_number'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_documents_user_document_number', 'documents', type_='unique')
    op.create_index('document_number', 'documents', ['document_number'], unique=True)
