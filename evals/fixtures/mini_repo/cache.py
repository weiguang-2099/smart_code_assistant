"""Simple in-process cache for user lookups."""
from evals.fixtures.mini_repo.errors import CacheMissError

_CACHE: dict[str, object] = {}


def set_cache(key: str, value: object) -> None:
    _CACHE[key] = value


def get_cache(key: str) -> object:
    if key not in _CACHE:
        raise CacheMissError(key)
    return _CACHE[key]


def invalidate(key: str) -> None:
    _CACHE.pop(key, None)
