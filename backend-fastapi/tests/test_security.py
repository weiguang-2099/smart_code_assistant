"""
Tests for JWT, password hashing, token blacklist and version manager.

These exercise the full auth surface without any DB / network dependency.
"""
from datetime import datetime, timedelta

import pytest
from jose import jwt

from app.core import security
from app.core.config import settings
from app.core.token_blacklist import TokenBlacklist, TokenVersionManager


# ----- Password hashing -----

class TestPasswordHashing:
    def test_hash_then_verify_roundtrip(self):
        hashed = security.get_password_hash("correct horse battery staple")
        assert hashed != "correct horse battery staple"
        assert security.verify_password("correct horse battery staple", hashed) is True

    def test_verify_rejects_wrong_password(self):
        hashed = security.get_password_hash("right")
        assert security.verify_password("wrong", hashed) is False

    def test_two_hashes_of_same_password_differ(self):
        """argon2 uses a per-call salt - identical passwords must hash differently."""
        a = security.get_password_hash("same")
        b = security.get_password_hash("same")
        assert a != b
        # but both verify
        assert security.verify_password("same", a)
        assert security.verify_password("same", b)


# ----- Access / refresh tokens -----

class TestAccessToken:
    def test_create_access_token_contains_required_claims(self):
        token = security.create_access_token({"sub": "42"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "42"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "jti" in payload
        assert "ver" in payload

    def test_create_access_token_respects_custom_expiry(self):
        """
        Compare two tokens minted with different deltas using the same code
        path - this sidesteps the naive-utcnow / local-time conversion that
        bites if you mix datetime.utcnow().timestamp() with payload['exp'].
        """
        short = security.create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=5))
        longer = security.create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=3600))

        short_payload = jwt.decode(short, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        longer_payload = jwt.decode(longer, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        gap = longer_payload["exp"] - short_payload["exp"]
        # Should be ~3595 seconds apart, allow a couple seconds of jitter
        assert 3590 <= gap <= 3600

    def test_create_access_token_can_omit_jti(self):
        token = security.create_access_token({"sub": "1"}, include_jti=False)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "jti" not in payload


class TestRefreshToken:
    def test_refresh_token_is_typed_correctly(self):
        token = security.create_refresh_token({"sub": "7"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["type"] == "refresh"
        assert payload["sub"] == "7"
        assert "jti" in payload

    def test_validate_refresh_token_returns_user_id(self):
        token = security.create_refresh_token({"sub": "99"})
        validated = security.validate_refresh_token(token)
        assert validated is not None
        assert validated["user_id"] == 99

    def test_validate_refresh_token_rejects_access_token(self):
        access = security.create_access_token({"sub": "1"})
        assert security.validate_refresh_token(access) is None

    def test_validate_refresh_token_rejects_garbage(self):
        assert security.validate_refresh_token("not-a-jwt") is None
        assert security.validate_refresh_token("") is None


class TestTokenPair:
    def test_create_token_pair_returns_four_items(self):
        access, refresh, access_exp, refresh_exp = security.create_token_pair(1)
        assert isinstance(access, str) and isinstance(refresh, str)
        assert refresh_exp > access_exp
        assert access != refresh


# ----- Decode + payload extraction -----

class TestDecode:
    def test_decode_valid_token(self):
        token = security.create_access_token({"sub": "5"})
        payload = security.decode_token(token)
        assert payload is not None
        assert payload["sub"] == "5"

    def test_decode_returns_none_on_invalid(self):
        assert security.decode_token("invalid.token.here") is None
        assert security.decode_token("") is None

    def test_decode_returns_none_on_wrong_secret(self):
        bogus = jwt.encode({"sub": "1", "exp": datetime.utcnow() + timedelta(hours=1)}, "WRONG_KEY", algorithm=settings.ALGORITHM)
        assert security.decode_token(bogus) is None

    def test_decode_returns_none_on_expired(self):
        token = security.create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-10))
        assert security.decode_token(token) is None


class TestGetTokenPayload:
    def test_returns_user_id_for_valid_token(self):
        token = security.create_access_token({"sub": "123"})
        payload = security.get_token_payload(token)
        assert payload is not None
        assert payload["user_id"] == 123

    def test_returns_none_when_sub_missing(self):
        # craft a token without sub
        bad = jwt.encode(
            {"exp": datetime.utcnow() + timedelta(hours=1), "type": "access"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        assert security.get_token_payload(bad) is None

    def test_returns_none_when_sub_is_not_numeric(self):
        bad = jwt.encode(
            {"sub": "not-a-number", "exp": datetime.utcnow() + timedelta(hours=1)},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        assert security.get_token_payload(bad) is None


# ----- Token blacklist -----

class TestTokenBlacklist:
    def test_token_not_blacklisted_by_default(self):
        bl = TokenBlacklist()
        assert bl.is_blacklisted("any-token", 1) is False

    def test_add_then_check_returns_blacklisted(self):
        bl = TokenBlacklist()
        token = "sample-token"
        bl.add(token, user_id=42, expires_at=datetime.utcnow() + timedelta(hours=1))
        assert bl.is_blacklisted(token, 42) is True

    def test_expired_entry_is_not_considered_blacklisted(self):
        bl = TokenBlacklist()
        token = "expired-token"
        bl.add(token, user_id=1, expires_at=datetime.utcnow() - timedelta(seconds=1))
        assert bl.is_blacklisted(token, 1) is False

    def test_size_reports_growing_count(self):
        bl = TokenBlacklist()
        assert bl.size() == 0
        bl.add("t1", 1, datetime.utcnow() + timedelta(hours=1))
        bl.add("t2", 1, datetime.utcnow() + timedelta(hours=1))
        assert bl.size() == 2

    def test_revoke_all_user_tokens_runs_without_error(self):
        bl = TokenBlacklist()
        assert bl.revoke_all_user_tokens(1) == 0  # in-memory stub


class TestTokenVersionManager:
    def test_default_version_is_one(self):
        mgr = TokenVersionManager()
        assert mgr.get_version(1) == 1

    def test_increment_returns_new_version(self):
        mgr = TokenVersionManager()
        v1 = mgr.increment_version(1)
        v2 = mgr.increment_version(1)
        assert v1 == 2 and v2 == 3
        assert mgr.get_version(1) == 3

    def test_versions_are_per_user(self):
        mgr = TokenVersionManager()
        mgr.increment_version(1)
        assert mgr.get_version(2) == 1


# ----- Token revocation through security module -----

class TestRevocationFlow:
    def test_revoke_token_marks_it_invalid(self):
        token = security.create_access_token({"sub": "10"})
        assert security.revoke_token(token, 10) is True
        assert security.is_token_blacklisted(token, 10) is True

    def test_revoke_garbage_token_returns_false(self):
        assert security.revoke_token("not.a.token", 1) is False

    def test_revoke_all_increments_version_and_invalidates_old_tokens(self):
        # First make an access token for user 77.
        token = security.create_access_token({"sub": "77"})
        # Bumping the version means decode will pass but get_token_payload returns None.
        new_ver = security.revoke_all_user_tokens(77)
        assert new_ver >= 2
        assert security.get_token_payload(token) is None


# ----- Misc helpers -----

class TestSecureToken:
    def test_generate_secure_token_default_length(self):
        # 32 bytes -> 64 hex chars
        token = security.generate_secure_token()
        assert len(token) == 64
        int(token, 16)  # must be valid hex

    def test_generate_secure_token_custom_length(self):
        assert len(security.generate_secure_token(8)) == 16

    def test_two_secure_tokens_are_different(self):
        assert security.generate_secure_token() != security.generate_secure_token()
