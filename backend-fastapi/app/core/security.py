"""
Security utilities for authentication and authorization.
"""
from datetime import datetime, timedelta
from typing import Optional
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token (typically {"sub": user_id})
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    # Encode token
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.debug(f"JWT decoded successfully, payload: {payload}")
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding JWT: {str(e)}")
        return None


def get_token_payload(token: str) -> Optional[dict]:
    """
    Get the payload from a JWT token.

    Args:
        token: JWT token string

    Returns:
        Token payload with user_id if valid, None otherwise
    """
    payload = decode_access_token(token)
    if payload is None:
        logger.warning("decode_access_token returned None")
        return None

    sub = payload.get("sub")
    logger.debug(f"Token payload sub: {sub}, full payload: {payload}")

    if sub is None:
        logger.warning("Token payload missing 'sub' field")
        return None

    # Convert sub to int (it's stored as string in JWT)
    try:
        user_id = int(sub)
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to convert sub '{sub}' to int: {str(e)}")
        return None

    return {"user_id": user_id, **payload}
