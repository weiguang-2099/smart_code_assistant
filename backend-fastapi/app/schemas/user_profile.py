"""
User profile and preference schemas for request and response validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, HttpUrl


# ==================== UserProfile Schemas ====================

class UserProfileBase(BaseModel):
    """Base user profile schema with common fields."""
    display_name: Optional[str] = Field(None, max_length=100, description="Display name")
    bio: Optional[str] = Field(None, description="User biography")
    location: Optional[str] = Field(None, max_length=100, description="User location")
    website: Optional[str] = Field(None, max_length=255, description="Personal website")
    github_url: Optional[str] = Field(None, max_length=255, description="GitHub profile URL")


class UserProfileCreate(UserProfileBase):
    """Schema for creating user profile."""
    pass


class UserProfileUpdate(UserProfileBase):
    """Schema for updating user profile."""
    pass


class UserProfileResponse(UserProfileBase):
    """Schema for user profile response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    avatar_url: Optional[str] = None
    updated_at: datetime


class UserProfileDetail(UserProfileResponse):
    """Schema for detailed user profile including user info."""
    username: Optional[str] = None
    email: Optional[str] = None


# ==================== Avatar Upload Schemas ====================

class AvatarUploadResponse(BaseModel):
    """Schema for avatar upload response."""
    avatar_url: str


# ==================== UserPreference Schemas ====================

class UserPreferenceBase(BaseModel):
    """Base user preference schema with common fields."""
    theme: Optional[str] = Field(None, pattern="^(light|dark|auto)$", description="UI theme")
    language: Optional[str] = Field(None, max_length=10, description="Language preference")
    editor_font_size: Optional[int] = Field(None, ge=10, le=24, description="Editor font size")
    editor_theme: Optional[str] = Field(None, max_length=50, description="Editor theme")
    notification_enabled: Optional[bool] = Field(None, description="Enable notifications")
    email_notification: Optional[bool] = Field(None, description="Enable email notifications")


class UserPreferenceUpdate(UserPreferenceBase):
    """Schema for updating user preferences."""
    pass


class UserPreferenceResponse(UserPreferenceBase):
    """Schema for user preference response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    theme: str
    language: str
    editor_font_size: int
    editor_theme: str
    notification_enabled: bool
    email_notification: bool
    created_at: datetime
    updated_at: datetime


# ==================== User Stats Schemas ====================

class UserStatsResponse(BaseModel):
    """Schema for user statistics response."""
    documents_count: int
    total_versions: int
    projects_count: int
    storage_used: int  # in bytes


# ==================== Full User Profile Schemas ====================

class FullUserProfileResponse(BaseModel):
    """Schema for complete user profile with preferences and stats."""
    profile: UserProfileResponse
    preferences: UserPreferenceResponse
    stats: UserStatsResponse
