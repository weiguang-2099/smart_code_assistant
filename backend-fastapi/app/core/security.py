"""
Security utilities for authentication and authorization.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging
import secrets
import uuid

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.token_blacklist import token_blacklist, token_version_manager

logger = logging.getLogger(__name__)

# Password hashing context - using argon2 (more secure, no bcrypt issues)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        True if passwords match, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password for storage.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    include_jti: bool = True
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token (typically {"sub": user_id})
        expires_delta: Optional expiration time delta
        include_jti: Whether to include a JWT ID (for blacklisting)

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "type": "access",
    })

    # Add JTI (JWT ID) for blacklisting support
    if include_jti:
        to_encode["jti"] = str(uuid.uuid4())

    # Add token version for user if user_id is in data
    user_id = data.get("sub")
    if user_id:
        to_encode["ver"] = token_version_manager.get_version(int(user_id))

    # Encode token
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Data to encode in the token (typically {"sub": user_id})
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()

    # Set expiration time (default: 7 days)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid.uuid4()),  # Always include JTI for refresh tokens
    })

    # Add token version for user
    user_id = data.get("sub")
    if user_id:
        to_encode["ver"] = token_version_manager.get_version(int(user_id))

    # Encode token
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_token_pair(user_id: int) -> Tuple[str, str, datetime, datetime]:
    """
    Create both access and refresh tokens for a user.

    Args:
        user_id: The user's ID

    Returns:
        Tuple of (access_token, refresh_token, access_expires_at, refresh_expires_at)
    """
    token_data = {"sub": str(user_id)}

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    access_expires_at = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    return access_token, refresh_token, access_expires_at, refresh_expires_at


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding JWT: {str(e)}")
        return None


def get_token_payload(token: str) -> Optional[dict]:
    """
    Get the payload from a JWT token with validation.

    Args:
        token: JWT token string

    Returns:
        Token payload with user_id if valid, None otherwise
    """
    payload = decode_token(token)
    if payload is None:
        logger.warning("decode_token returned None")
        return None

    sub = payload.get("sub")
    logger.debug(f"Token payload sub: {sub}")

    if sub is None:
        logger.warning("Token payload missing 'sub' field")
        return None

    # Convert sub to int (it's stored as string in JWT)
    try:
        user_id = int(sub)
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to convert sub '{sub}' to int: {str(e)}")
        return None

    # Check token version
    token_version = payload.get("ver")
    current_version = token_version_manager.get_version(user_id)

    if token_version is not None and token_version < current_version:
        logger.warning(f"Token version {token_version} is outdated (current: {current_version})")
        return None

    return {"user_id": user_id, **payload}


def validate_refresh_token(token: str) -> Optional[dict]:
    """
    Validate a refresh token specifically.

    Args:
        token: JWT refresh token string

    Returns:
        Token payload if valid refresh token, None otherwise
    """
    payload = decode_token(token)
    if payload is None:
        return None

    # Check token type
    if payload.get("type") != "refresh":
        logger.warning("Token is not a refresh token")
        return None

    # Get user ID
    sub = payload.get("sub")
    if sub is None:
        logger.warning("Refresh token missing 'sub' field")
        return None

    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        logger.warning(f"Failed to convert sub '{sub}' to int")
        return None

    # Check token version
    token_version = payload.get("ver")
    current_version = token_version_manager.get_version(user_id)

    if token_version is not None and token_version < current_version:
        logger.warning(f"Refresh token version is outdated")
        return None

    return {"user_id": user_id, "jti": payload.get("jti"), **payload}


def revoke_token(token: str, user_id: int) -> bool:
    """
    Revoke a token by adding it to the blacklist.

    Args:
        token: The token to revoke
        user_id: The user ID associated with the token

    Returns:
        True if successfully revoked
    """
    payload = decode_token(token)
    if payload is None:
        return False

    exp = payload.get("exp")
    if exp is None:
        return False

    expires_at = datetime.fromtimestamp(exp)
    token_blacklist.add(token, user_id, expires_at)

    return True


def revoke_all_user_tokens(user_id: int) -> int:
    """
    Revoke all tokens for a user by incrementing their token version.

    Args:
        user_id: The user's ID

    Returns:
        The new token version
    """
    return token_version_manager.increment_version(user_id)


def is_token_blacklisted(token: str, user_id: int) -> bool:
    """
    Check if a token is blacklisted.

    Args:
        token: The token to check
        user_id: The user ID associated with the token

    Returns:
        True if blacklisted, False otherwise
    """
    return token_blacklist.is_blacklisted(token, user_id)


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Args:
        length: Length of the token in bytes (output will be hex, so 2x length)

    Returns:
        Secure random token string
    """
    return secrets.token_hex(length)
