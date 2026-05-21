"""
Tests for the unified caching system (LRU + CacheManager + cached decorator).
Redis backend is not exercised here - those paths are integration concerns.
"""
import asyncio
import time

import pytest

from app.core.cache import (
    CacheManager,
    LRUCache,
    cached,
    generate_cache_key,
)


# ----- LRUCache -----

class TestLRUCache:
    @pytest.mark.asyncio
    async def test_set_then_get_returns_value(self):
        cache = LRUCache(max_size=10)
        await cache.set("k", "v")
        assert await cache.get("k") == "v"

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_none(self):
        cache = LRUCache(max_size=10)
        assert await cache.get("nope") is None

    @pytest.mark.asyncio
    async def test_overwrite_updates_value(self):
        cache = LRUCache(max_size=10)
        await cache.set("k", 1)
        await cache.set("k", 2)
        assert await cache.get("k") == 2

    @pytest.mark.asyncio
    async def test_delete_removes_entry(self):
        cache = LRUCache(max_size=10)
        await cache.set("k", "v")
        assert await cache.delete("k") is True
        assert await cache.get("k") is None
        assert await cache.delete("k") is False

    @pytest.mark.asyncio
    async def test_clear_empties_cache(self):
        cache = LRUCache(max_size=10)
        await cache.set("a", 1)
        await cache.set("b", 2)
        await cache.clear()
        assert await cache.get("a") is None
        assert await cache.get("b") is None

    @pytest.mark.asyncio
    async def test_ttl_expires_entry(self):
        cache = LRUCache(max_size=10, default_ttl=300)
        await cache.set("k", "v", ttl=1)
        assert await cache.get("k") == "v"
        await asyncio.sleep(1.1)
        assert await cache.get("k") is None

    @pytest.mark.asyncio
    async def test_ttl_zero_means_never_expires(self):
        cache = LRUCache(max_size=10)
        await cache.set("k", "v", ttl=0)
        # not expired even after a tick
        await asyncio.sleep(0.01)
        assert await cache.get("k") == "v"

    @pytest.mark.asyncio
    async def test_lru_evicts_oldest_when_full(self):
        cache = LRUCache(max_size=2, max_memory_mb=100)
        await cache.set("a", "1")
        await cache.set("b", "2")
        await cache.set("c", "3")  # should push "a" out
        assert await cache.get("a") is None
        assert await cache.get("b") == "2"
        assert await cache.get("c") == "3"

    @pytest.mark.asyncio
    async def test_lru_access_promotes_entry(self):
        cache = LRUCache(max_size=2, max_memory_mb=100)
        await cache.set("a", "1")
        await cache.set("b", "2")
        # promote "a" by reading it
        await cache.get("a")
        await cache.set("c", "3")  # should evict "b" now, not "a"
        assert await cache.get("a") == "1"
        assert await cache.get("b") is None

    @pytest.mark.asyncio
    async def test_stats_count_hits_and_misses(self):
        cache = LRUCache(max_size=10)
        await cache.set("k", "v")
        await cache.get("k")          # hit
        await cache.get("missing")    # miss
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0
        assert stats["entries"] == 1
        assert stats["type"] == "lru"

    @pytest.mark.asyncio
    async def test_stats_handles_unserializable_value(self):
        """LRU must not crash on values json.dumps can't handle."""
        class NotJsonable:
            pass

        cache = LRUCache(max_size=10)
        await cache.set("k", NotJsonable())
        # entry stored (size estimate fallback used)
        stats = cache.get_stats()
        assert stats["entries"] == 1


# ----- CacheManager (L1-only) -----

class TestCacheManagerL1Only:
    @pytest.mark.asyncio
    async def test_set_and_get_through_manager(self):
        mgr = CacheManager(l1_max_size=10)
        await mgr.set("k", {"v": 1})
        assert await mgr.get("k") == {"v": 1}

    @pytest.mark.asyncio
    async def test_set_accepts_ttl_kwarg(self):
        """Regression: callers use ttl=... so manager must accept it."""
        mgr = CacheManager(l1_max_size=10)
        await mgr.set("k", "v", ttl=300)
        assert await mgr.get("k") == "v"

    @pytest.mark.asyncio
    async def test_set_accepts_l1_ttl_override(self):
        mgr = CacheManager(l1_max_size=10)
        await mgr.set("k", "v", l1_ttl=1)
        await asyncio.sleep(1.1)
        assert await mgr.get("k") is None

    @pytest.mark.asyncio
    async def test_delete_removes_value(self):
        mgr = CacheManager(l1_max_size=10)
        await mgr.set("k", "v")
        await mgr.delete("k")
        assert await mgr.get("k") is None

    @pytest.mark.asyncio
    async def test_clear_drops_everything(self):
        mgr = CacheManager(l1_max_size=10)
        await mgr.set("a", 1)
        await mgr.set("b", 2)
        await mgr.clear()
        assert await mgr.get("a") is None

    @pytest.mark.asyncio
    async def test_stats_returns_l1_block(self):
        mgr = CacheManager(l1_max_size=10)
        stats = mgr.get_stats()
        assert "l1" in stats
        assert "l2" not in stats   # no Redis configured

    def test_properties_expose_layers(self):
        mgr = CacheManager(l1_max_size=10)
        assert mgr.l1 is not None
        assert mgr.l2 is None


# ----- generate_cache_key -----

class TestGenerateCacheKey:
    def test_same_inputs_produce_same_key(self):
        a = generate_cache_key("x", 1, foo="bar")
        b = generate_cache_key("x", 1, foo="bar")
        assert a == b
        assert len(a) == 32

    def test_different_inputs_produce_different_keys(self):
        assert generate_cache_key("x") != generate_cache_key("y")
        assert generate_cache_key(foo=1) != generate_cache_key(foo=2)

    def test_kwarg_order_does_not_affect_key(self):
        a = generate_cache_key(a=1, b=2)
        b = generate_cache_key(b=2, a=1)
        assert a == b


# ----- @cached decorator -----

class TestCachedDecorator:
    @pytest.mark.asyncio
    async def test_repeat_calls_return_cached_value(self):
        mgr = CacheManager(l1_max_size=10)
        call_count = 0

        @cached(ttl=60, key_prefix="t:", cache_manager=mgr)
        async def slow(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert await slow(5) == 10
        assert await slow(5) == 10
        assert call_count == 1  # second call was cached

    @pytest.mark.asyncio
    async def test_different_args_produce_separate_cache_entries(self):
        mgr = CacheManager(l1_max_size=10)
        calls = []

        @cached(ttl=60, cache_manager=mgr)
        async def f(x):
            calls.append(x)
            return x

        await f(1)
        await f(2)
        await f(1)
        assert calls == [1, 2]

    @pytest.mark.asyncio
    async def test_custom_key_builder_is_used(self):
        mgr = CacheManager(l1_max_size=10)

        @cached(ttl=60, cache_manager=mgr, key_builder=lambda *a, **k: "fixed")
        async def f(x):
            return x

        await f(1)
        # all calls share key "fixed" so f(2) returns the cached f(1)
        assert await f(2) == 1
