"""
Rate limiting middleware for API protection.
In-memory implementation that can be upgraded to Redis for production.
"""
import time
import logging
from typing import Dict, Tuple, Optional, Callable
from threading import Lock
from collections import defaultdict

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import RateLimitExceededException, ErrorCode

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Thread-safe in-memory rate limiter using sliding window algorithm.

    For production, consider upgrading to Redis:
    - redis.incr(key)
    - redis.expire(key, window)
    """

    def __init__(self):
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = Lock()
        self._cleanup_interval = 1000
        self._operation_count = 0

    def _cleanup_old_requests(self, key: str, window: int) -> None:
        """Remove requests older than the window."""
        current_time = time.time()
        cutoff_time = current_time - window

        self._requests[key] = [
            timestamp for timestamp in self._requests[key]
            if timestamp > cutoff_time
        ]

    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60
    ) -> Tuple[bool, int, int]:
        """
        Check if a request is allowed based on rate limiting.

        Args:
            key: Unique identifier for the client (e.g., IP address)
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        current_time = time.time()

        with self._lock:
            # Cleanup old requests
            self._cleanup_old_requests(key, window_seconds)

            # Get current request count
            request_count = len(self._requests[key])

            # Periodic full cleanup
            self._operation_count += 1
            if self._operation_count % self._cleanup_interval == 0:
                self._periodic_cleanup(window_seconds)

            if request_count >= max_requests:
                # Calculate retry after
                oldest_request = min(self._requests[key]) if self._requests[key] else current_time
                retry_after = int(oldest_request + window_seconds - current_time) + 1
                return False, 0, max(1, retry_after)

            # Record this request
            self._requests[key].append(current_time)
            remaining = max_requests - request_count - 1

            return True, remaining, 0

    def _periodic_cleanup(self, max_window: int) -> None:
        """Periodic cleanup of all keys to prevent memory leaks."""
        current_time = time.time()
        cutoff_time = current_time - max_window

        keys_to_remove = []
        for key in self._requests:
            self._requests[key] = [
                ts for ts in self._requests[key] if ts > cutoff_time
            ]
            if not self._requests[key]:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._requests[key]

        if keys_to_remove:
            logger.debug(f"Cleaned up {len(keys_to_remove)} inactive rate limit keys")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.

    Applies different rate limits based on endpoint:
    - Login/Register: Stricter limits (prevent brute force)
    - API endpoints: Standard limits
    - Health check: No limits
    """

    def __init__(self, app, rate_limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()

        # Rate limit configurations per endpoint pattern
        self.endpoint_limits = {
            # Authentication endpoints - stricter limits
            "/api/v1/auth/login": (settings.RATE_LIMIT_LOGIN_REQUESTS, 60),
            "/api/v1/auth/register": (settings.RATE_LIMIT_LOGIN_REQUESTS, 60),
            "/api/v1/auth/refresh": (10, 60),

            # Default limit for all other endpoints
            "default": (settings.RATE_LIMIT_REQUESTS, 60),
        }

        # Endpoints to skip rate limiting
        self.skip_paths = {
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        }

    def get_client_key(self, request: Request) -> str:
        """
        Get a unique key for the client.

        Uses X-Forwarded-For header if available (behind proxy),
        otherwise falls back to client IP.
        """
        # Check for forwarded header (behind reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            # Direct connection
            client_ip = request.client.host if request.client else "unknown"

        return f"rate_limit:{client_ip}"

    def get_limit_for_path(self, path: str) -> Tuple[int, int]:
        """Get rate limit configuration for a path."""
        # Check for exact match first
        if path in self.endpoint_limits:
            return self.endpoint_limits[path]

        # Check for prefix match
        for endpoint_path, limits in self.endpoint_limits.items():
            if endpoint_path != "default" and path.startswith(endpoint_path):
                return limits

        # Return default limit
        return self.endpoint_limits["default"]

    async def dispatch(self, request: Request, call_next):
        """Process the request with rate limiting."""
        path = request.url.path

        # Skip rate limiting for certain paths
        if path in self.skip_paths:
            return await call_next(request)

        # Skip for static files
        if path.startswith("/static/") or path.startswith("/_next/"):
            return await call_next(request)

        # Get client key and rate limit config
        client_key = self.get_client_key(request)
        max_requests, window = self.get_limit_for_path(path)

        # Check rate limit
        is_allowed, remaining, retry_after = self.rate_limiter.is_allowed(
            client_key, max_requests, window
        )

        # Add rate limit headers to all responses
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for {client_key} on {path}")

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": {
                        "code": ErrorCode.RATE_LIMIT_EXCEEDED,
                        "message": "Rate limit exceeded. Please try again later.",
                        "details": {
                            "retry_after": retry_after,
                            "limit": max_requests,
                            "window": window,
                        },
                    },
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window)

        return response


# Global rate limiter instance
rate_limiter = RateLimiter()


def setup_rate_limiting(app) -> None:
    """Setup rate limiting middleware for the FastAPI application."""
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
    logger.info("Rate limiting middleware enabled")
