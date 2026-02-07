"""
User profile and preference models for personalization.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class UserProfile(Base):
    """
    UserProfile model for user's personal information.

    Attributes:
        id: Primary key (same as user_id)
        user_id: Foreign key to users table (one-to-one)
        display_name: Display name for the user
        bio: User biography/description
        avatar_url: URL to user's avatar image
        location: User's location
        website: Personal website URL
        github_url: GitHub profile URL
        updated_at: Last update timestamp
    """

    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    display_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    location = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    github_url = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile(id={self.id}, user_id={self.user_id}, display_name='{self.display_name}')>"


class UserPreference(Base):
    """
    UserPreference model for user's application preferences.

    Attributes:
        id: Primary key
        user_id: Foreign key to users table (one-to-one)
        theme: UI theme preference (light/dark/auto)
        language: Language preference
        editor_font_size: Editor font size in pixels
        editor_theme: Editor color theme
        notification_enabled: Whether notifications are enabled
        email_notification: Whether email notifications are enabled
        created_at: Preference creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    theme = Column(String(20), default="dark", nullable=False)
    language = Column(String(10), default="zh-CN", nullable=False)
    editor_font_size = Column(Integer, default=14, nullable=False)
    editor_theme = Column(String(50), default="monokai", nullable=False)
    notification_enabled = Column(Boolean, default=True, nullable=False)
    email_notification = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="preferences")

    def __repr__(self) -> str:
        return f"<UserPreference(id={self.id}, user_id={self.user_id}, theme='{self.theme}')>"
