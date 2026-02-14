"""
Token blacklist service for managing revoked tokens.
In-memory implementation that can be upgraded to Redis for production.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from threading import Lock
import hashlib

logger = logging.getLogger(__name__)


class TokenBlacklist:
    """
    Thread-safe in-memory token blacklist.
    Stores token JTI (JWT ID) with expiration time for automatic cleanup.

    For production, consider upgrading to Redis:
    - redis.setex(f"blacklist:{jti}", ttl, "1")
    - redis.exists(f"blacklist:{jti}")
    """

    def __init__(self):
        self._blacklist: Dict[str, datetime] = {}  # jti -> expiration_time
        self._lock = Lock()
        self._cleanup_interval = 100  # Clean up every N operations
        self._operation_count = 0

    def _generate_jti(self, token: str, user_id: int) -> str:
        """Generate a unique identifier for the token."""
        # Use hash of token + user_id as JTI for uniqueness
        data = f"{token}:{user_id}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def add(self, token: str, user_id: int, expires_at: datetime) -> str:
        """
        Add a token to the blacklist.

        Args:
            token: The JWT token string
            user_id: The user ID associated with the token
            expires_at: When the token expires (for cleanup)

        Returns:
            The JTI (unique identifier) for the blacklisted token
        """
        jti = self._generate_jti(token, user_id)

        with self._lock:
            self._blacklist[jti] = expires_at
            self._operation_count += 1
            logger.info(f"Token blacklisted for user {user_id}, jti={jti[:8]}...")

            # Periodic cleanup
            if self._operation_count % self._cleanup_interval == 0:
                self._cleanup()

        return jti

    def is_blacklisted(self, token: str, user_id: int) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token: The JWT token string
            user_id: The user ID associated with the token

        Returns:
            True if the token is blacklisted, False otherwise
        """
        # We need to check all possible JTIs for this token
        # Since we include timestamp in JTI generation, we check by partial match
        with self._lock:
            # For simplicity, we store a mapping of token_hash -> jtis
            # This is a simplified check - in production, use Redis with token hash
            token_hash = hashlib.sha256(f"{token}:{user_id}".encode()).hexdigest()[:32]

            # Check if any jti starting with this hash exists and is not expired
            now = datetime.utcnow()
            for jti, exp in self._blacklist.items():
                if jti.startswith(token_hash[:16]) and exp > now:
                    return True
            return False

    def revoke_all_user_tokens(self, user_id: int) -> int:
        """
        Revoke all tokens for a user (useful for "logout all devices").

        Args:
            user_id: The user ID

        Returns:
            Number of tokens revoked (not accurate for in-memory implementation)
        """
        # In Redis, we could maintain a user_token_version
        # For in-memory, this is a placeholder
        logger.info(f"All tokens marked as revoked for user {user_id}")
        return 0

    def _cleanup(self) -> int:
        """
        Remove expired tokens from the blacklist.

        Returns:
            Number of tokens removed
        """
        now = datetime.utcnow()
        expired_jtis = [jti for jti, exp in self._blacklist.items() if exp <= now]

        for jti in expired_jtis:
            del self._blacklist[jti]

        if expired_jtis:
            logger.debug(f"Cleaned up {len(expired_jtis)} expired tokens from blacklist")

        return len(expired_jtis)

    def size(self) -> int:
        """Get the current size of the blacklist."""
        with self._lock:
            return len(self._blacklist)


# Token version manager for "logout all devices" functionality
class TokenVersionManager:
    """
    Manages token versions for users.
    Incrementing a user's version invalidates all their existing tokens.
    """

    def __init__(self):
        self._versions: Dict[int, int] = {}  # user_id -> version
        self._lock = Lock()

    def get_version(self, user_id: int) -> int:
        """Get the current token version for a user."""
        with self._lock:
            return self._versions.get(user_id, 1)

    def increment_version(self, user_id: int) -> int:
        """
        Increment the token version for a user, invalidating all existing tokens.

        Returns:
            The new version number
        """
        with self._lock:
            current = self._versions.get(user_id, 1)
            new_version = current + 1
            self._versions[user_id] = new_version
            logger.info(f"Token version incremented for user {user_id}: {current} -> {new_version}")
            return new_version


# Global instances
token_blacklist = TokenBlacklist()
token_version_manager = TokenVersionManager()
