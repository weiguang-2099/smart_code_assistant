"""
Authentication API routes for user registration and login.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_token_pair,
    validate_refresh_token,
    revoke_token,
    revoke_all_user_tokens,
)
from app.core.config import settings
from app.core.deps import get_current_user
from app.core.exceptions import (
    InvalidCredentialsException,
    AccountDisabledException,
    DuplicateEntryException,
    InvalidTokenException,
    UserNotFoundException,
)
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserResponse,
    UserWithToken,
    Token,
    TokenRefreshResponse,
    RefreshTokenRequest,
    UserUpdate,
)
from app.models.user import User

router = APIRouter()


@router.post("/register", response_model=UserWithToken, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        UserWithToken: Created user with access token
    """
    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise DuplicateEntryException(field="username")

    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise DuplicateEntryException(field="email")

    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Create token pair
    access_token, refresh_token, _, _ = create_token_pair(new_user.id)

    return UserWithToken(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        is_active=new_user.is_active,
        is_superuser=new_user.is_superuser,
        created_at=new_user.created_at,
        updated_at=new_user.updated_at,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with username/email and password.

    Args:
        user_data: User login data
        db: Database session

    Returns:
        Token: Access token, refresh token with user info
    """
    # Try to find user by username or email
    result = await db.execute(
        select(User).where(
            (User.username == user_data.username) | (User.email == user_data.username)
        )
    )
    user = result.scalar_one_or_none()

    # Verify user exists and password is correct
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise InvalidCredentialsException()

    # Check if user is active
    if not user.is_active:
        raise AccountDisabledException()

    # Update last login time
    from datetime import datetime
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # Create token pair
    access_token, refresh_token, _, _ = create_token_pair(user.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    Args:
        request: Refresh token request
        db: Database session

    Returns:
        TokenRefreshResponse: New access token and refresh token
    """
    # Validate refresh token
    payload = validate_refresh_token(request.refresh_token)

    if payload is None:
        raise InvalidTokenException(message="Invalid or expired refresh token")

    user_id = payload.get("user_id")
    if user_id is None:
        raise InvalidTokenException(message="Invalid refresh token format")

    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise UserNotFoundException(user_id=user_id)

    if not user.is_active:
        raise AccountDisabledException()

    # Revoke old refresh token
    revoke_token(request.refresh_token, user_id)

    # Create new token pair
    access_token, refresh_token, _, _ = create_token_pair(user.id)

    return TokenRefreshResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
):
    """
    Logout current user.

    Revokes the current user's token version, invalidating all tokens.
    For single-device logout, the client should discard tokens locally.

    Returns:
        dict: Logout confirmation message
    """
    # Increment token version to invalidate all tokens
    revoke_all_user_tokens(current_user.id)

    return {
        "success": True,
        "message": "Successfully logged out"
    }


@router.post("/logout-all")
async def logout_all_devices(
    current_user: User = Depends(get_current_user),
):
    """
    Logout from all devices.

    Increments the token version, invalidating all tokens across all devices.

    Returns:
        dict: Logout confirmation message
    """
    revoke_all_user_tokens(current_user.id)

    return {
        "success": True,
        "message": "Successfully logged out from all devices"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user

    Returns:
        UserResponse: Current user information
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user profile.

    Args:
        user_update: User update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserResponse: Updated user information
    """
    # Update fields if provided
    if user_update.email is not None:
        # Check if email is already taken by another user
        result = await db.execute(
            select(User).where(
                (User.email == user_update.email) & (User.id != current_user.id)
            )
        )
        if result.scalar_one_or_none():
            raise DuplicateEntryException(field="email")
        current_user.email = user_update.email

    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    if user_update.password is not None:
        current_user.hashed_password = get_password_hash(user_update.password)
        # Revoke all tokens when password changes
        revoke_all_user_tokens(current_user.id)

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)
