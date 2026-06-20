"""
Document numbering constraint tests.

`document_number` is generated per-user (DOC-YYYYMMDD-NNN, sequence scoped to the
owner), so its uniqueness must also be per-user. A global unique constraint makes
the second user's first document of the day collide on DOC-...-001.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base
import app.models  # noqa: F401  registers all tables/relationships on Base.metadata
from app.models.document import Document


def _fresh_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_two_users_can_share_a_document_number():
    """Different owners may each have DOC-YYYYMMDD-001."""
    engine = _fresh_db()
    with Session(engine) as s:
        s.add(Document(id=1, user_id=1, title="A", document_number="DOC-20260620-001"))
        s.add(Document(id=2, user_id=2, title="B", document_number="DOC-20260620-001"))
        s.commit()  # must not raise
        assert s.query(Document).count() == 2
    engine.dispose()


def test_same_user_cannot_reuse_a_document_number():
    """A single owner still cannot have two documents with the same number."""
    engine = _fresh_db()
    with Session(engine) as s:
        s.add(Document(id=1, user_id=1, title="A", document_number="DOC-20260620-001"))
        s.add(Document(id=2, user_id=1, title="B", document_number="DOC-20260620-001"))
        with pytest.raises(IntegrityError):
            s.commit()
    engine.dispose()
