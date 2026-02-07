"""
Code file schemas for request and response validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# Base code file schema
class CodeFileBase(BaseModel):
    """Base code file schema with common fields."""
    filename: str = Field(..., min_length=1, max_length=255, description="File name with extension")
    path: str = Field("", max_length=500, description="File path within project")
    language: str = Field(..., min_length=1, max_length=50, description="Programming language")
    content: str = Field("", description="File content/code")


# Schema for code file creation
class CodeFileCreate(CodeFileBase):
    """Schema for creating a new code file."""
    project_id: int = Field(..., description="Project ID")


# Schema for code file update
class CodeFileUpdate(BaseModel):
    """Schema for updating a code file."""
    filename: Optional[str] = Field(None, min_length=1, max_length=255)
    path: Optional[str] = Field(None, max_length=500)
    language: Optional[str] = Field(None, min_length=1, max_length=50)
    content: Optional[str] = None


# Schema for code file response
class CodeFileResponse(CodeFileBase):
    """Schema for code file response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime


# Schema for code file with full path
class CodeFileDetail(CodeFileResponse):
    """Schema for detailed code file information."""
    full_path: str
    owner_id: int
    project_name: Optional[str] = None
