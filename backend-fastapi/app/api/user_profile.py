"""
User profile and preference API routes.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.deps import get_current_user
from app.schemas.user_profile import (
    UserProfileUpdate,
    UserProfileResponse,
    UserProfileDetail,
    UserPreferenceUpdate,
    UserPreferenceResponse,
    UserStatsResponse,
    FullUserProfileResponse,
    AvatarUploadResponse,
)
from app.models.user import User
from app.models.user_profile import UserProfile, UserPreference
from app.models.document import Document, RawVersion
from app.models.project import Project

router = APIRouter()


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify router is working."""
    return {"message": "User profile router is working"}


# ==================== UserProfile Routes ====================

@router.get("/profile", response_model=UserProfileDetail)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current user's profile.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserProfileDetail: User profile details
    """
    # Get or create profile
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        # Create default profile
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return UserProfileDetail(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        bio=profile.bio,
        avatar_url=profile.avatar_url,
        location=profile.location,
        website=profile.website,
        github_url=profile.github_url,
        updated_at=profile.updated_at,
        username=current_user.username,
        email=current_user.email,
    )


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the current user's profile.

    Args:
        profile_update: Profile update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserProfileResponse: Updated profile
    """
    # Get or create profile
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        # Create profile with update data
        profile = UserProfile(
            user_id=current_user.id,
            display_name=profile_update.display_name,
            bio=profile_update.bio,
            location=profile_update.location,
            website=profile_update.website,
            github_url=profile_update.github_url,
        )
        db.add(profile)
    else:
        # Update existing profile
        if profile_update.display_name is not None:
            profile.display_name = profile_update.display_name
        if profile_update.bio is not None:
            profile.bio = profile_update.bio
        if profile_update.location is not None:
            profile.location = profile_update.location
        if profile_update.website is not None:
            profile.website = profile_update.website
        if profile_update.github_url is not None:
            profile.github_url = profile_update.github_url

    await db.commit()
    await db.refresh(profile)

    return UserProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        bio=profile.bio,
        avatar_url=profile.avatar_url,
        location=profile.location,
        website=profile.website,
        github_url=profile.github_url,
        updated_at=profile.updated_at,
    )


@router.post("/profile/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload avatar for the current user.

    Args:
        file: Avatar image file
        current_user: Current authenticated user
        db: Database session

    Returns:
        AvatarUploadResponse: Avatar URL

    Note:
        This is a placeholder implementation. In production, you should:
        1. Validate file type and size
        2. Store the file in S3/OSS or local storage
        3. Return the actual file URL
    """
    # TODO: Implement actual file upload logic
    # For now, return a placeholder URL
    avatar_url = f"/api/v1/user/avatar/{current_user.id}/{file.filename}"

    # Get or create profile
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=current_user.id, avatar_url=avatar_url)
        db.add(profile)
    else:
        profile.avatar_url = avatar_url

    await db.commit()

    return AvatarUploadResponse(avatar_url=avatar_url)


# ==================== UserPreference Routes ====================

@router.get("/preferences", response_model=UserPreferenceResponse)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current user's preferences.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserPreferenceResponse: User preferences
    """
    # Get or create preferences
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == current_user.id)
    )
    preferences = result.scalar_one_or_none()

    if not preferences:
        # Create default preferences
        preferences = UserPreference(user_id=current_user.id)
        db.add(preferences)
        await db.commit()
        await db.refresh(preferences)

    return UserPreferenceResponse(
        id=preferences.id,
        user_id=preferences.user_id,
        theme=preferences.theme,
        language=preferences.language,
        editor_font_size=preferences.editor_font_size,
        editor_theme=preferences.editor_theme,
        notification_enabled=preferences.notification_enabled,
        email_notification=preferences.email_notification,
        created_at=preferences.created_at,
        updated_at=preferences.updated_at,
    )


@router.put("/preferences", response_model=UserPreferenceResponse)
async def update_user_preferences(
    preference_update: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the current user's preferences.

    Args:
        preference_update: Preference update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserPreferenceResponse: Updated preferences
    """
    # Get or create preferences
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == current_user.id)
    )
    preferences = result.scalar_one_or_none()

    if not preferences:
        # Create preferences with update data
        update_data = preference_update.model_dump(exclude_unset=True)
        preferences = UserPreference(
            user_id=current_user.id,
            **update_data
        )
        db.add(preferences)
    else:
        # Update existing preferences
        if preference_update.theme is not None:
            preferences.theme = preference_update.theme
        if preference_update.language is not None:
            preferences.language = preference_update.language
        if preference_update.editor_font_size is not None:
            preferences.editor_font_size = preference_update.editor_font_size
        if preference_update.editor_theme is not None:
            preferences.editor_theme = preference_update.editor_theme
        if preference_update.notification_enabled is not None:
            preferences.notification_enabled = preference_update.notification_enabled
        if preference_update.email_notification is not None:
            preferences.email_notification = preference_update.email_notification

    await db.commit()
    await db.refresh(preferences)

    return UserPreferenceResponse(
        id=preferences.id,
        user_id=preferences.user_id,
        theme=preferences.theme,
        language=preferences.language,
        editor_font_size=preferences.editor_font_size,
        editor_theme=preferences.editor_theme,
        notification_enabled=preferences.notification_enabled,
        email_notification=preferences.email_notification,
        created_at=preferences.created_at,
        updated_at=preferences.updated_at,
    )


# ==================== User Stats Routes ====================

@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get statistics for the current user.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserStatsResponse: User statistics
    """
    # Count documents
    documents_count_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.user_id == current_user.id)
    )
    documents_count = documents_count_result.scalar() or 0

    # Count total versions
    total_versions_result = await db.execute(
        select(func.count())
        .select_from(RawVersion)
        .join(Document, Document.id == RawVersion.document_id)
        .where(Document.user_id == current_user.id)
    )
    total_versions = total_versions_result.scalar() or 0

    # Count projects
    projects_count_result = await db.execute(
        select(func.count()).select_from(Project).where(Project.owner_id == current_user.id)
    )
    projects_count = projects_count_result.scalar() or 0

    # Calculate storage used (placeholder: sum of markdown content lengths)
    storage_result = await db.execute(
        select(func.sum(func.length(RawVersion.markdown_content)))
        .join(Document, Document.id == RawVersion.document_id)
        .where(Document.user_id == current_user.id)
    )
    storage_used = storage_result.scalar() or 0

    return UserStatsResponse(
        documents_count=documents_count,
        total_versions=total_versions,
        projects_count=projects_count,
        storage_used=storage_used,
    )


# ==================== Full Profile Routes ====================

@router.get("/me", response_model=FullUserProfileResponse)
async def get_full_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current user's complete profile including preferences and stats.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        FullUserProfileResponse: Complete user profile
    """
    # Get profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    # Get preferences
    pref_result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == current_user.id)
    )
    preferences = pref_result.scalar_one_or_none()

    if not preferences:
        preferences = UserPreference(user_id=current_user.id)
        db.add(preferences)
        await db.commit()
        await db.refresh(preferences)

    # Get stats
    documents_count_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.user_id == current_user.id)
    )
    documents_count = documents_count_result.scalar() or 0

    total_versions_result = await db.execute(
        select(func.count())
        .select_from(RawVersion)
        .join(Document, Document.id == RawVersion.document_id)
        .where(Document.user_id == current_user.id)
    )
    total_versions = total_versions_result.scalar() or 0

    projects_count_result = await db.execute(
        select(func.count()).select_from(Project).where(Project.owner_id == current_user.id)
    )
    projects_count = projects_count_result.scalar() or 0

    storage_result = await db.execute(
        select(func.sum(func.length(RawVersion.markdown_content)))
        .join(Document, Document.id == RawVersion.document_id)
        .where(Document.user_id == current_user.id)
    )
    storage_used = storage_result.scalar() or 0

    stats = UserStatsResponse(
        documents_count=documents_count,
        total_versions=total_versions,
        projects_count=projects_count,
        storage_used=storage_used,
    )

    return FullUserProfileResponse(
        profile=UserProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            display_name=profile.display_name,
            bio=profile.bio,
            avatar_url=profile.avatar_url,
            location=profile.location,
            website=profile.website,
            github_url=profile.github_url,
            updated_at=profile.updated_at,
        ),
        preferences=UserPreferenceResponse(
            id=preferences.id,
            user_id=preferences.user_id,
            theme=preferences.theme,
            language=preferences.language,
            editor_font_size=preferences.editor_font_size,
            editor_theme=preferences.editor_theme,
            notification_enabled=preferences.notification_enabled,
            email_notification=preferences.email_notification,
            created_at=preferences.created_at,
            updated_at=preferences.updated_at,
        ),
        stats=stats,
    )
