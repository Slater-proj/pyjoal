"""Tests for cache_manager.py — SmartCache + CacheManager."""
import time
import pytest
from unittest.mock import patch

import os
os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.core.cache_manager import SmartCache, CacheManager, CacheEntry


# ── CacheEntry ──────────────────────────────────────────────────────

class TestCacheEntry:
    def test_not_expired(self):
        e = CacheEntry("val", ttl=60)
        assert not e.is_expired()

    def test_expired(self):
        e = CacheEntry("val", ttl=0.01, created_at=time.time() - 1)
        assert e.is_expired()

    def test_never_expires(self):
        e = CacheEntry("val", ttl=0, created_at=time.time() - 99999)
        assert not e.is_expired()

    def test_access(self):
        e = CacheEntry("val", ttl=60)
        assert e.access() == "val"
        assert e.access_count == 1


# ── SmartCache ──────────────────────────────────────────────────────

class TestSmartCache:
    def test_get_miss(self):
        c = SmartCache()
        assert c.get("nope") is None

    def test_set_and_get(self):
        c = SmartCache()
        c.set("k", "v")
        assert c.get("k") == "v"

    def test_get_expired(self):
        c = SmartCache(default_ttl=0.01)
        c.set("k", "v")
        time.sleep(0.02)
        assert c.get("k") is None

    def test_delete(self):
        c = SmartCache()
        c.set("k", "v")
        assert c.delete("k") is True
        assert c.delete("k") is False

    def test_clear(self):
        c = SmartCache()
        c.set("a", 1)
        c.set("b", 2)
        c.clear()
        assert c.get("a") is None

    def test_cleanup_expired(self):
        c = SmartCache(default_ttl=0.01)
        for i in range(5):
            c.set(f"k{i}", i)
        time.sleep(0.02)
        removed = c.cleanup_expired()
        assert removed == 5

    def test_lru_eviction(self):
        c = SmartCache(max_size=3)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)
        # Access a and b to make c the LRU
        c.get("a")
        c.get("b")
        # Adding d triggers LRU eviction
        c.set("d", 4)
        # at least one eviction happened
        stats = c.get_stats()
        assert stats["evictions"] >= 1

    def test_get_stats(self):
        c = SmartCache()
        c.get("miss")
        c.set("k", "v")
        c.get("k")
        stats = c.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0
        assert stats["size"] == 1

    def test_get_stats_zero_requests(self):
        c = SmartCache()
        stats = c.get_stats()
        assert stats["hit_rate"] == 0

    def test_custom_ttl_on_set(self):
        c = SmartCache(default_ttl=300)
        c.set("k", "v", ttl=0.01)
        time.sleep(0.02)
        assert c.get("k") is None


# ── CacheManager ────────────────────────────────────────────────────

class TestCacheManager:
    def test_torrent_metadata(self):
        cm = CacheManager()
        assert cm.get_torrent_metadata("/fake.torrent") is None
        cm.set_torrent_metadata("/fake.torrent", {"name": "test"})
        assert cm.get_torrent_metadata("/fake.torrent") == {"name": "test"}

    def test_tracker_response(self):
        cm = CacheManager()
        assert cm.get_tracker_response("http://t.com", "abc") is None
        cm.set_tracker_response("http://t.com", "abc", {"seeders": 10})
        assert cm.get_tracker_response("http://t.com", "abc") == {"seeders": 10}

    def test_aggregated_stats(self):
        cm = CacheManager()
        assert cm.get_aggregated_stats("test") is None
        cm.set_aggregated_stats("test", {"val": 1})
        assert cm.get_aggregated_stats("test") == {"val": 1}

    def test_websocket_batch_throttle(self):
        cm = CacheManager()
        assert cm.should_send_websocket_batch("ws1") is True
        cm.mark_websocket_batch_sent("ws1")
        assert cm.should_send_websocket_batch("ws1") is False

    def test_periodic_cleanup_not_due(self):
        cm = CacheManager()
        cm._last_cleanup = time.time()
        cm.periodic_cleanup()
        # should not raise

    def test_periodic_cleanup_due(self):
        cm = CacheManager()
        cm._last_cleanup = time.time() - 600
        cm.periodic_cleanup()
        # after cleanup, _last_cleanup should be updated
        assert time.time() - cm._last_cleanup < 5

    def test_run_cleanup(self):
        cm = CacheManager()
        cm.torrent_metadata.set("k", "v", ttl=0.01)
        time.sleep(0.02)
        cm._run_cleanup()
        assert cm.torrent_metadata.get("k") is None

    def test_get_global_stats(self):
        cm = CacheManager()
        stats = cm.get_global_stats()
        assert "torrent_metadata" in stats
        assert "tracker_responses" in stats
        assert "last_cleanup" in stats

    def test_clear_all(self):
        cm = CacheManager()
        cm.set_torrent_metadata("/t", {"a": 1})
        cm.set_tracker_response("http://t", "h", {"b": 2})
        cm.clear_all()
        assert cm.get_torrent_metadata("/t") is None
        assert cm.get_tracker_response("http://t", "h") is None
