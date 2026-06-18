"""Plain data classes."""
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    email: str


@dataclass
class Session:
    token: str
    user: User
