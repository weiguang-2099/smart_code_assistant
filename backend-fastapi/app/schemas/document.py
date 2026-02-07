"""
Document schemas for request and response validation.
"""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class SourceType(str, Enum):
    """Source type enum for raw versions."""
    UPLOAD = "upload"
    MANUAL = "manual"
    PARSED = "parsed"


# ==================== Document Schemas ====================

class DocumentBase(BaseModel):
    """Base document schema with common fields."""
    title: str = Field(..., min_length=1, max_length=255, description="Document title")
    description: Optional[str] = Field(None, description="Document description")
    category: Optional[str] = Field(None, max_length=100, description="Document category/tag")
    project_id: Optional[int] = Field(None, description="Associated project ID")


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""
    pass


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata."""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Document title")
    description: Optional[str] = Field(None, description="Document description")
    category: Optional[str] = Field(None, max_length=100, description="Document category")


class DocumentResponse(DocumentBase):
    """Schema for document response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    current_version_id: Optional[int] = None
    is_published: bool
    version_count: int = 0
    created_at: datetime
    updated_at: datetime


# ==================== Raw Version Schemas ====================

class VersionBase(BaseModel):
    """Base version schema with common fields."""
    markdown_content: str = Field(..., description="Markdown content")
    change_summary: Optional[str] = Field(None, max_length=500, description="Brief description of changes")


class VersionCreate(VersionBase):
    """Schema for creating a new version."""
    tiptap_content: Optional[Dict[str, Any]] = Field(None, description="TipTap JSON content")
    source_type: SourceType = Field(default=SourceType.MANUAL, description="How this version was created")


class VersionResponse(VersionBase):
    """Schema for version response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    version_number: int
    tiptap_content: Dict[str, Any]
    source_type: str
    created_by: int
    created_at: datetime


class VersionListItem(BaseModel):
    """Schema for version list item (simplified)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_number: int
    change_summary: Optional[str] = None
    source_type: str
    created_by: int
    created_by_username: Optional[str] = None
    created_at: datetime


# ==================== Document Detail Schemas ====================

class DocumentDetail(DocumentResponse):
    """Schema for detailed document information with current version."""
    current_version: Optional[VersionResponse] = None
    versions: List[VersionListItem] = []


# ==================== Document List Schemas ====================

class DocumentListResponse(BaseModel):
    """Schema for paginated document list."""
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentListParams(BaseModel):
    """Schema for document list query parameters."""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    category: Optional[str] = Field(None, description="Filter by category")
    project_id: Optional[int] = Field(None, description="Filter by project ID")
    search: Optional[str] = Field(None, description="Search in title and description")
    sort_by: str = Field("updated_at", description="Sort field")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")


# ==================== Version Compare Schemas ====================

class VersionCompareResponse(BaseModel):
    """Schema for version comparison response."""
    from_version: VersionResponse
    to_version: VersionResponse
    diff: str  # Unified diff format


class VersionRollbackRequest(BaseModel):
    """Schema for version rollback request."""
    version_id: int = Field(..., description="Version ID to rollback to")
    change_summary: Optional[str] = Field(None, max_length=500, description="Reason for rollback")


class VersionRollbackResponse(BaseModel):
    """Schema for version rollback response."""
    new_version_id: int
    version_number: int
    message: str


# ==================== PDF Upload Schemas ====================

class PDFUploadRequest(BaseModel):
    """Schema for PDF upload request metadata."""
    title: Optional[str] = Field(None, max_length=255, description="Document title")
    description: Optional[str] = Field(None, description="Document description")
    category: Optional[str] = Field(None, max_length=100, description="Document category")


class PDFUploadResponse(BaseModel):
    """Schema for PDF upload response."""
    document_id: int
    version_id: int
    markdown_content: str
    tiptap_content: Dict[str, Any]


# ==================== Attachment Schemas ====================

class AttachmentResponse(BaseModel):
    """Schema for attachment response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_id: int
    file_name: str
    file_type: str
    file_size: int
    storage_path: str
    storage_type: str
    created_at: datetime


# ==================== Document Stats Schemas ====================

class DocumentStatsResponse(BaseModel):
    """Schema for document statistics response."""
    documents_count: int
    total_versions: int
    projects_count: int
    storage_used: int  # in bytes
