"""Request-scoped middleware that uses auth + cache."""
from evals.fixtures.mini_repo.auth import authenticate
from evals.fixtures.mini_repo.cache import get_cache, set_cache
from evals.fixtures.mini_repo.errors import CacheMissError


def load_request_user(token: str) -> dict:
    try:
        return get_cache(token)
    except CacheMissError:
        user = authenticate(token)
        set_cache(token, user)
        return user
