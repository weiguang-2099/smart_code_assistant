"""Top-level API handlers that everyone else feeds into."""
from evals.fixtures.mini_repo.middleware import load_request_user
from evals.fixtures.mini_repo.db import insert_user, delete_user
from evals.fixtures.mini_repo.utils import normalize_email


def create_user(user_id: int, name: str, email: str) -> dict:
    insert_user(user_id, name, normalize_email(email))
    return {"id": user_id, "name": name}


def whoami(token: str) -> dict:
    return load_request_user(token)


def remove_user(token: str, user_id: int) -> None:
    load_request_user(token)
    delete_user(user_id)
