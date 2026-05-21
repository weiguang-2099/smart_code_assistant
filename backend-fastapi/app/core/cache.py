"""
Unified caching system for Smart Code Assistant.

Provides multi-layer caching with LRU memory cache and optional Redis backend.
"""
import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import wraps
from threading import Lock
from typing import Any, Callable, Dict, Optional, TypeVar, ParamSpec

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    hits: int = 0
    size_bytes: int = 0


class CacheBackend(ABC):
    """Abstract cache backend interface."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL in seconds."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cached values."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class LRUCache(CacheBackend):
    """
    Thread-safe LRU (Least Recently Used) memory cache.

    Features:
    - Configurable max size (number of entries)
    - Configurable max memory (bytes)
    - TTL support
    - Hit/miss statistics
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 100,
        default_ttl: int = 300,
    ):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._max_size = max_size
        self._max_memory = max_memory_mb * 1024 * 1024
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._current_memory = 0

    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of a value."""
        try:
            return len(json.dumps(value, default=str))
        except (TypeError, ValueError):
            return 1024

    def _evict_if_needed(self) -> None:
        """Evict entries if cache is full."""
        while (
            len(self._cache) > self._max_size or
            self._current_memory > self._max_memory
        ):
            if not self._cache:
                break
            oldest_key = next(iter(self._cache))
            entry = self._cache.pop(oldest_key)
            self._current_memory -= entry.size_bytes
            self._evictions += 1
            logger.debug(f"Evicted cache entry: {oldest_key}")

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if entry is expired."""
        if entry.expires_at is None:
            return False
        return time.time() > entry.expires_at

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache, returning None if not found or expired."""
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            if self._is_expired(entry):
                self._cache.pop(key, None)
                self._current_memory -= entry.size_bytes
                self._misses += 1
                return None

            entry.hits += 1
            self._hits += 1
            self._cache.move_to_end(key)
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        ttl = ttl or self._default_ttl
        size = self._estimate_size(value)

        with self._lock:
            if key in self._cache:
                old_entry = self._cache.pop(key)
                self._current_memory -= old_entry.size_bytes

            now = time.time()
            entry = CacheEntry(
                value=value,
                created_at=now,
                expires_at=now + ttl if ttl > 0 else None,
                size_bytes=size,
            )

            self._cache[key] = entry
            self._current_memory += size
            self._cache.move_to_end(key)
            self._evict_if_needed()

        return True

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._current_memory -= entry.size_bytes
                return True
            return False

    async def clear(self) -> bool:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
            self._current_memory = 0
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "type": "lru",
                "entries": len(self._cache),
                "max_entries": self._max_size,
                "memory_bytes": self._current_memory,
                "max_memory_bytes": self._max_memory,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "evictions": self._evictions,
            }


class RedisCache(CacheBackend):
    """
    Redis cache backend (optional).

    Requires redis-py package and Redis server.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "sca:",
        default_ttl: int = 300,
    ):
        self._redis_url = redis_url
        self._prefix = prefix
        self._default_ttl = default_ttl
        self._client = None
        self._hits = 0
        self._misses = 0

    async def _get_client(self):
        """Get or create Redis client."""
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(self._redis_url)
            except ImportError:
                logger.warning("Redis package not installed, using dummy cache")
                self._client = None
        return self._client

    def _make_key(self, key: str) -> str:
        """Create prefixed key."""
        return f"{self._prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        client = await self._get_client()
        if client is None:
            self._misses += 1
            return None

        try:
            value = await client.get(self._make_key(key))
            if value is not None:
                self._hits += 1
                return json.loads(value)
            self._misses += 1
            return None
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            self._misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis with TTL."""
        client = await self._get_client()
        if client is None:
            return False

        try:
            serialized = json.dumps(value, default=str)
            ttl = ttl or self._default_ttl
            await client.setex(self._make_key(key), ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from Redis."""
        client = await self._get_client()
        if client is None:
            return False

        try:
            await client.delete(self._make_key(key))
            return True
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all cached values with prefix."""
        client = await self._get_client()
        if client is None:
            return False

        try:
            keys = await client.keys(f"{self._prefix}*")
            if keys:
                await client.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "type": "redis",
            "url": self._redis_url,
            "prefix": self._prefix,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
        }


class CacheManager:
    """
    Multi-layer cache manager.

    Manages L1 (memory) and optional L2 (Redis) caches.
    """

    def __init__(
        self,
        l1_max_size: int = 1000,
        l1_max_memory_mb: int = 50,
        l1_default_ttl: int = 300,
        redis_url: Optional[str] = None,
        l2_default_ttl: int = 600,
    ):
        self._l1 = LRUCache(
            max_size=l1_max_size,
            max_memory_mb=l1_max_memory_mb,
            default_ttl=l1_default_ttl,
        )
        self._l2: Optional[RedisCache] = None

        if redis_url:
            self._l2 = RedisCache(
                redis_url=redis_url,
                default_ttl=l2_default_ttl,
            )

    @property
    def l1(self) -> LRUCache:
        """Get L1 cache."""
        return self._l1

    @property
    def l2(self) -> Optional[RedisCache]:
        """Get L2 cache."""
        return self._l2

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache (L1 first, then L2).

        If found in L2, populates L1.
        """
        value = await self._l1.get(key)
        if value is not None:
            return value

        if self._l2:
            value = await self._l2.get(key)
            if value is not None:
                await self._l1.set(key, value)
                return value

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        l1_ttl: Optional[int] = None,
        l2_ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in both L1 and L2 caches.

        Pass `ttl` to apply the same expiry to both layers (the common case);
        pass `l1_ttl` / `l2_ttl` to override per layer.
        """
        effective_l1 = l1_ttl if l1_ttl is not None else ttl
        effective_l2 = l2_ttl if l2_ttl is not None else ttl

        await self._l1.set(key, value, effective_l1)

        if self._l2:
            await self._l2.set(key, value, effective_l2)

        return True

    async def delete(self, key: str) -> bool:
        """Delete from both caches."""
        l1_result = await self._l1.delete(key)

        if self._l2:
            await self._l2.delete(key)

        return l1_result

    async def clear(self) -> bool:
        """Clear both caches."""
        await self._l1.clear()

        if self._l2:
            await self._l2.clear()

        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get combined cache statistics."""
        stats = {
            "l1": self._l1.get_stats(),
        }
        if self._l2:
            stats["l2"] = self._l2.get_stats()
        return stats


def generate_cache_key(*args, **kwargs) -> str:
    """Generate a cache key from function arguments."""
    key_data = {
        "args": args,
        "kwargs": kwargs,
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.sha256(key_str.encode()).hexdigest()[:32]


def cached(
    ttl: int = 300,
    key_prefix: str = "",
    cache_manager: Optional[CacheManager] = None,
    key_builder: Optional[Callable] = None,
):
    """
    Decorator for caching async function results.

    Args:
        ttl: Cache TTL in seconds
        key_prefix: Prefix for cache keys
        cache_manager: CacheManager instance (uses global if None)
        key_builder: Custom key builder function

    Example:
        @cached(ttl=60, key_prefix="user:")
        async def get_user(user_id: int):
            return await db.get(User, user_id)
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache = cache_manager or global_cache_manager

            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = f"{key_prefix}{func.__name__}:{generate_cache_key(*args, **kwargs)}"

            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            logger.debug(f"Cache set for {cache_key}")

            return result

        return wrapper
    return decorator


_global_cache: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _global_cache
    if _global_cache is None:
        from app.core.config import settings
        redis_url = getattr(settings, 'REDIS_URL', None)
        _global_cache = CacheManager(
            l1_max_size=getattr(settings, 'CACHE_L1_MAX_SIZE', 1000),
            l1_max_memory_mb=getattr(settings, 'CACHE_L1_MAX_MEMORY_MB', 50),
            l1_default_ttl=getattr(settings, 'CACHE_DEFAULT_TTL', 300),
            redis_url=redis_url,
        )
    return _global_cache


global_cache_manager = get_cache_manager()
