"""
Document models for Raw materials library and version control.
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, BigInteger, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class SourceType(str, Enum):
    """Source type enum for raw versions."""
    UPLOAD = "upload"
    MANUAL = "manual"
    PARSED = "parsed"


class StorageType(str, Enum):
    """Storage type enum for attachments."""
    LOCAL = "local"
    S3 = "s3"
    OSS = "oss"


class Document(Base):
    """
    Document model representing a user's document with version control.

    Attributes:
        id: Primary key
        user_id: Foreign key to users table (owner)
        title: Document title
        document_number: Unique document number (e.g., DOC-20260213-001)
        description: Document description (optional)
        category: Document category/tag (optional)
        project_id: Foreign key to projects table (optional)
        current_version_id: Foreign key to raw_versions table
        is_published: Whether the document is published
        created_at: Document creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "documents"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    document_number = Column(String(20), unique=True, index=True, nullable=True)  # 文档编号
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    current_version_id = Column(BigInteger, ForeignKey("raw_versions.id", ondelete="SET NULL"), nullable=True)
    is_published = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="documents")
    project = relationship("Project", back_populates="documents")
    current_version = relationship("RawVersion", foreign_keys=[current_version_id], post_update=True)
    versions = relationship("RawVersion", foreign_keys="RawVersion.document_id", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}', user_id={self.user_id})>"


class RawVersion(Base):
    """
    RawVersion model representing a version snapshot of a document.

    Attributes:
        id: Primary key
        document_id: Foreign key to documents table
        version_number: Sequential version number starting from 1
        markdown_content: Markdown content of the version
        tiptap_content: TipTap JSON content of the version
        source_type: How this version was created (upload/manual/parsed)
        change_summary: Brief description of changes
        created_by: Foreign key to users table (creator)
        created_at: Version creation timestamp
    """

    __tablename__ = "raw_versions"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    document_id = Column(BigInteger, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    markdown_content = Column(Text, nullable=False)
    tiptap_content = Column(JSON, nullable=False)
    source_type = Column(String(20), default=SourceType.MANUAL, nullable=False)
    change_summary = Column(String(500), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    document = relationship("Document", foreign_keys=[document_id], back_populates="versions")
    creator = relationship("User", foreign_keys=[created_by])
    attachments = relationship("Attachment", back_populates="version", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<RawVersion(id={self.id}, document_id={self.document_id}, version_number={self.version_number})>"


class Attachment(Base):
    """
    Attachment model for file attachments linked to document versions.

    Attributes:
        id: Primary key
        version_id: Foreign key to raw_versions table
        file_name: Original file name
        file_type: MIME type or file extension
        file_size: File size in bytes
        storage_path: Storage path or URL
        storage_type: Where the file is stored (local/s3/oss)
        created_at: Upload timestamp
    """

    __tablename__ = "attachments"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    version_id = Column(BigInteger, ForeignKey("raw_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    storage_path = Column(String(500), nullable=False)
    storage_type = Column(String(20), default=StorageType.LOCAL, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    version = relationship("RawVersion", back_populates="attachments")

    def __repr__(self) -> str:
        return f"<Attachment(id={self.id}, file_name='{self.file_name}', version_id={self.version_id})>"
