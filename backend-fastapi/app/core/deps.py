"""
Dependency functions for FastAPI routes.
"""
from typing import AsyncGenerator
import logging
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.core.security import get_token_payload
from app.core.exceptions import (
    InvalidTokenException,
    TokenExpiredException,
    AccountDisabledException,
    UserNotFoundException,
)

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        db: Database session
        credentials: HTTP Bearer credentials

    Returns:
        User: Current authenticated user

    Raises:
        InvalidTokenException: If token is invalid or user not found
        AccountDisabledException: If user account is disabled
    """
    # Get token payload
    token = credentials.credentials
    logger.debug(f"Attempting to authenticate with token")

    payload = get_token_payload(token)

    if payload is None:
        logger.warning("Token validation failed: invalid payload")
        raise InvalidTokenException(message="Invalid or expired token")

    user_id = payload.get("user_id")
    if user_id is None:
        logger.warning("Token validation failed: no user_id in payload")
        raise InvalidTokenException(message="Invalid token format")

    logger.debug(f"Looking up user with id: {user_id}")

    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning(f"User with id {user_id} not found")
        raise UserNotFoundException(user_id=user_id)

    if not user.is_active:
        logger.warning(f"User {user_id} is inactive")
        raise AccountDisabledException()

    logger.debug(f"Successfully authenticated user: {user.username}")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get the current active user.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current active user

    Raises:
        AccountDisabledException: If user is not active
    """
    if not current_user.is_active:
        raise AccountDisabledException()
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get the current superuser.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current superuser

    Raises:
        ForbiddenException: If user is not a superuser
    """
    from app.core.exceptions import ForbiddenException

    if not current_user.is_superuser:
        raise ForbiddenException(message="Admin access required")
    return current_user


# Re-export get_db for convenience
__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
]
