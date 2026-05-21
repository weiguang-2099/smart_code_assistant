"""
Tests for the FastAPI auth dependencies.

We construct each scenario by calling the dependency directly with a stub DB
session and stub HTTP credentials - much cheaper than spinning up a TestClient.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core import deps
from app.core.exceptions import (
    AccountDisabledException,
    ForbiddenException,
    InvalidTokenException,
    UserNotFoundException,
)


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _user(*, id=1, active=True, superuser=False):
    u = MagicMock()
    u.id = id
    u.username = "test"
    u.is_active = active
    u.is_superuser = superuser
    return u


def _db_returning(user):
    """Build a stub AsyncSession whose execute(...).scalar_one_or_none() returns `user`."""
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result)
    return db


# ----- get_current_user -----

class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_invalid_token_payload_raises(self, monkeypatch):
        monkeypatch.setattr(deps, "get_token_payload", lambda _t: None)
        with pytest.raises(InvalidTokenException):
            await deps.get_current_user(db=_db_returning(None), credentials=_creds("x"))

    @pytest.mark.asyncio
    async def test_payload_without_user_id_raises(self, monkeypatch):
        monkeypatch.setattr(deps, "get_token_payload", lambda _t: {"sub": "1"})
        with pytest.raises(InvalidTokenException):
            await deps.get_current_user(db=_db_returning(None), credentials=_creds("x"))

    @pytest.mark.asyncio
    async def test_user_not_found_raises(self, monkeypatch):
        monkeypatch.setattr(deps, "get_token_payload", lambda _t: {"user_id": 5})
        with pytest.raises(UserNotFoundException):
            await deps.get_current_user(db=_db_returning(None), credentials=_creds("x"))

    @pytest.mark.asyncio
    async def test_inactive_user_raises(self, monkeypatch):
        monkeypatch.setattr(deps, "get_token_payload", lambda _t: {"user_id": 5})
        with pytest.raises(AccountDisabledException):
            await deps.get_current_user(
                db=_db_returning(_user(id=5, active=False)),
                credentials=_creds("x"),
            )

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, monkeypatch):
        monkeypatch.setattr(deps, "get_token_payload", lambda _t: {"user_id": 5})
        user = _user(id=5, active=True)
        returned = await deps.get_current_user(db=_db_returning(user), credentials=_creds("x"))
        assert returned is user


# ----- get_current_active_user -----

class TestGetCurrentActiveUser:
    @pytest.mark.asyncio
    async def test_active_user_passes_through(self):
        user = _user(active=True)
        result = await deps.get_current_active_user(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_inactive_user_blocked(self):
        with pytest.raises(AccountDisabledException):
            await deps.get_current_active_user(current_user=_user(active=False))


# ----- get_current_superuser -----

class TestGetCurrentSuperuser:
    @pytest.mark.asyncio
    async def test_superuser_passes_through(self):
        user = _user(superuser=True)
        result = await deps.get_current_superuser(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_non_superuser_forbidden(self):
        with pytest.raises(ForbiddenException):
            await deps.get_current_superuser(current_user=_user(superuser=False))
