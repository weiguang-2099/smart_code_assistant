"""Token-based auth checks built on top of the DB layer."""
from evals.fixtures.mini_repo.db import get_user
from evals.fixtures.mini_repo.errors import AuthError

_TOKENS: dict[str, int] = {}


def issue_token(user_id: int, token: str) -> None:
    _TOKENS[token] = user_id


def authenticate(token: str) -> dict:
    if token not in _TOKENS:
        raise AuthError("invalid token")
    return get_user(_TOKENS[token])
