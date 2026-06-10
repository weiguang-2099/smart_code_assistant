"""Custom exception types used across the mini fixture."""


class AuthError(Exception):
    """Raised when authentication fails."""


class NotFoundError(Exception):
    """Raised when a record lookup misses."""


class CacheMissError(Exception):
    """Raised when a required cache entry is absent."""
