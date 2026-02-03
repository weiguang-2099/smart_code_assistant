"""
Authentication API routes for user registration and login.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
)
from app.core.config import settings
from app.core.deps import get_current_user
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserResponse,
    UserWithToken,
    Token,
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

    Raises:
        HTTPException: If username or email already exists
    """
    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

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

    # Create access token
    access_token = create_access_token(
        data={"sub": str(new_user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

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
        Token: Access token with user info

    Raises:
        HTTPException: If credentials are invalid
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = user_update.email

    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    if user_update.password is not None:
        current_user.hashed_password = get_password_hash(user_update.password)

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout():
    """
    Logout current user.

    Note: Since we use JWT tokens, logout is handled client-side
    by removing the token. This endpoint exists for future implementation
    of token blacklisting if needed.

    Returns:
        dict: Logout confirmation message
    """
    return {"message": "Successfully logged out"}
