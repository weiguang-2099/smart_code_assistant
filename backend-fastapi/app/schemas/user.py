"""
User schemas for request and response validation.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# Base user schema
class UserBase(BaseModel):
    """Base user schema with common fields."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")


# Schema for user registration
class UserRegister(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=6, max_length=100, description="Password")


# Schema for user login
class UserLogin(BaseModel):
    """Schema for user login."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


# Schema for user response
class UserResponse(UserBase):
    """Schema for user response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


# Schema for user with token (after login/register)
class UserWithToken(UserResponse):
    """Schema for user response with access token."""
    access_token: str
    token_type: str = "bearer"


# Schema for token response
class Token(BaseModel):
    """Schema for token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Schema for token data (internal use)
class TokenData(BaseModel):
    """Schema for token data payload."""
    user_id: Optional[int] = None
    username: Optional[str] = None


# Schema for user update
class UserUpdate(BaseModel):
    """Schema for user profile update."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=6, max_length=100)


# Schema for password change
class PasswordChange(BaseModel):
    """Schema for changing password."""
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, max_length=100, description="New password")
