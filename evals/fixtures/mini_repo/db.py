"""Synchronous in-memory DB used by the fixture services."""
from evals.fixtures.mini_repo.errors import NotFoundError

_USERS: dict[int, dict] = {}


def insert_user(user_id: int, name: str, email: str) -> None:
    _USERS[user_id] = {"id": user_id, "name": name, "email": email}


def get_user(user_id: int) -> dict:
    user = _USERS.get(user_id)
    if user is None:
        raise NotFoundError(f"user {user_id} not found")
    return user


def delete_user(user_id: int) -> None:
    _USERS.pop(user_id, None)
