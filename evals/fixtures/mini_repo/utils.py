"""Helpers that don't fit elsewhere."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def make_session_id(user_id: int, salt: str) -> str:
    return f"{user_id}-{salt}"
