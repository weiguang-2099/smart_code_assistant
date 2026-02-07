"""
Project schemas for request and response validation.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# Base project schema
class ProjectBase(BaseModel):
    """Base project schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: Optional[str] = Field(None, description="Project description")


# Schema for project creation
class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""
    pass


# Schema for project update
class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Project name")
    description: Optional[str] = Field(None, description="Project description")


# Schema for project response
class ProjectResponse(ProjectBase):
    """Schema for project response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    file_count: int = 0


# Schema for project with files
class ProjectWithFiles(ProjectResponse):
    """Schema for project response with file count."""
    file_count: int = 0


# Schema for project list response
class ProjectListResponse(BaseModel):
    """Schema for paginated project list."""
    projects: List[ProjectResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Schema for project detail
class ProjectDetail(ProjectResponse):
    """Schema for detailed project information."""
    owner_username: Optional[str] = None
    files: List[dict] = []
