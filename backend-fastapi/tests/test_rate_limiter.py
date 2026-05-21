"""
Tests for the in-memory rate limiter and the RateLimitMiddleware path matcher.
"""
import time
from unittest.mock import MagicMock

import pytest

from app.core.rate_limiter import RateLimiter, RateLimitMiddleware


@pytest.fixture
def limiter():
    return RateLimiter()


# ----- Core algorithm -----

class TestRateLimiter:
    def test_first_request_allowed(self, limiter):
        ok, remaining, retry = limiter.is_allowed("k", max_requests=3, window_seconds=60)
        assert ok is True
        assert remaining == 2
        assert retry == 0

    def test_requests_within_limit_decrement_remaining(self, limiter):
        limiter.is_allowed("k", 3, 60)
        limiter.is_allowed("k", 3, 60)
        ok, remaining, _ = limiter.is_allowed("k", 3, 60)
        assert ok is True
        assert remaining == 0

    def test_request_over_limit_is_denied(self, limiter):
        for _ in range(3):
            limiter.is_allowed("k", 3, 60)
        ok, remaining, retry = limiter.is_allowed("k", 3, 60)
        assert ok is False
        assert remaining == 0
        assert retry >= 1

    def test_keys_are_isolated(self, limiter):
        for _ in range(3):
            limiter.is_allowed("a", 3, 60)
        ok, _, _ = limiter.is_allowed("b", 3, 60)
        assert ok is True  # b's bucket is empty

    def test_expired_window_lets_new_requests_through(self, limiter):
        limiter.is_allowed("k", 1, 60)
        # forcibly age out the existing timestamp
        limiter._requests["k"] = [time.time() - 120]
        ok, _, _ = limiter.is_allowed("k", 1, 60)
        assert ok is True


# ----- Middleware helpers (unit-level, no actual HTTP) -----

class TestMiddlewarePathMatching:
    @pytest.fixture
    def middleware(self):
        return RateLimitMiddleware(app=MagicMock())

    def test_default_limit_used_for_unknown_path(self, middleware):
        max_req, window = middleware.get_limit_for_path("/api/v1/random/endpoint")
        assert max_req > 0
        assert window == 60

    def test_login_path_uses_stricter_limit(self, middleware):
        login = middleware.get_limit_for_path("/api/v1/auth/login")
        default = middleware.get_limit_for_path("/api/v1/random")
        # stricter <= default (configurable, but at least non-greater)
        assert login[0] <= default[0]

    def test_prefix_match_works(self, middleware):
        # /api/v1/auth/login/extra falls under /api/v1/auth/login by prefix
        max_req, _ = middleware.get_limit_for_path("/api/v1/auth/login/extra")
        login_max, _ = middleware.get_limit_for_path("/api/v1/auth/login")
        assert max_req == login_max

    def test_get_client_key_prefers_forwarded_for(self, middleware):
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}
        request.client = MagicMock(host="127.0.0.1")
        assert middleware.get_client_key(request) == "rate_limit:203.0.113.7"

    def test_get_client_key_falls_back_to_request_client(self, middleware):
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="198.51.100.5")
        assert middleware.get_client_key(request) == "rate_limit:198.51.100.5"

    def test_get_client_key_handles_missing_client(self, middleware):
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert middleware.get_client_key(request) == "rate_limit:unknown"

    def test_skip_paths_include_health_and_docs(self, middleware):
        for p in ["/health", "/", "/docs", "/redoc"]:
            assert p in middleware.skip_paths
