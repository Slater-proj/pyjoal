"""
Cache Manager - Intelligent caching system for PyJOAL
Optimizes performance by reducing I/O operations and redundant computations
"""
import time
import threading
from typing import Dict, Any, Optional, Callable, TypeVar
from datetime import datetime, timedelta
import logging
import weakref

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheEntry:
    """Individual cache entry with TTL and metadata"""
    
    def __init__(self, value: Any, ttl: float, created_at: float = None):
        self.value = value
        self.ttl = ttl
        self.created_at = created_at or time.time()
        self.access_count = 0
        self.last_accessed = self.created_at
        
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl <= 0:  # Never expires
            return False
        return (time.time() - self.created_at) > self.ttl
    
    def access(self) -> Any:
        """Record access and return value"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value

class SmartCache:
    """High-performance cache with TTL and intelligent cleanup"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'cleanup_runs': 0
        }
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats['misses'] += 1
                return None
                
            if entry.is_expired():
                del self._cache[key]
                self._stats['misses'] += 1
                return None
                
            self._stats['hits'] += 1
            return entry.access()
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache with optional TTL"""
        ttl = ttl if ttl is not None else self.default_ttl
        
        with self._lock:
            # Check size limit and cleanup if needed
            if len(self._cache) >= self.max_size:
                self._cleanup_lru()
                
            self._cache[key] = CacheEntry(value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete specific key from cache"""
        with self._lock:
            return self._cache.pop(key, None) is not None
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            logger.debug("Cache cleared")
    
    def cleanup_expired(self) -> int:
        """Remove expired entries, return count removed"""
        removed_count = 0
        current_time = time.time()
        
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
                removed_count += 1
            
            self._stats['cleanup_runs'] += 1
            
        if removed_count > 0:
            logger.debug(f"Cache cleanup: removed {removed_count} expired entries")
            
        return removed_count
    
    def _cleanup_lru(self) -> None:
        """Remove least recently used entries when cache is full"""
        if len(self._cache) < self.max_size:
            return
            
        # Sort by last access time, remove oldest 10%
        entries_by_access = sorted(
            self._cache.items(), 
            key=lambda x: x[1].last_accessed
        )
        
        remove_count = max(1, len(self._cache) // 10)
        
        for i in range(remove_count):
            key, _ = entries_by_access[i]
            del self._cache[key]
            self._stats['evictions'] += 1
        
        logger.debug(f"Cache LRU cleanup: evicted {remove_count} entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self._stats['evictions'],
                'cleanup_runs': self._stats['cleanup_runs']
            }


class CacheManager:
    """Global cache manager with multiple cache categories"""
    
    def __init__(self):
        # Different caches for different data types with optimized TTLs
        # ⚠️ IMPORTANT: TTLs courts pour réactivité temps réel
        self.torrent_metadata = SmartCache(max_size=500, default_ttl=1800)  # 30 min (métadonnées statiques)
        self.tracker_responses = SmartCache(max_size=200, default_ttl=60)   # 1 min (réponses tracker)
        self.stats_aggregated = SmartCache(max_size=100, default_ttl=2)     # 2 sec (stats dynamiques - RÉDUIT pour réactivité)
        self.websocket_batches = SmartCache(max_size=50, default_ttl=1)     # 1 sec (batching WebSocket - RÉDUIT)
        
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
        
        logger.info("🚀 Cache Manager initialized with intelligent multi-layer caching")
    
    def get_torrent_metadata(self, torrent_path: str) -> Optional[Dict]:
        """Get cached torrent metadata"""
        cache_key = f"torrent_meta:{torrent_path}"
        return self.torrent_metadata.get(cache_key)
    
    def set_torrent_metadata(self, torrent_path: str, metadata: Dict) -> None:
        """Cache torrent metadata"""
        cache_key = f"torrent_meta:{torrent_path}"
        self.torrent_metadata.set(cache_key, metadata)
    
    def get_tracker_response(self, tracker_url: str, info_hash: str) -> Optional[Dict]:
        """Get cached tracker response"""
        cache_key = f"tracker:{tracker_url}:{info_hash}"
        return self.tracker_responses.get(cache_key)
    
    def set_tracker_response(self, tracker_url: str, info_hash: str, response: Dict) -> None:
        """Cache tracker response"""
        cache_key = f"tracker:{tracker_url}:{info_hash}"
        self.tracker_responses.set(cache_key, response)
    
    def get_aggregated_stats(self, stats_key: str) -> Optional[Dict]:
        """Get cached aggregated statistics"""
        return self.stats_aggregated.get(f"stats:{stats_key}")
    
    def set_aggregated_stats(self, stats_key: str, stats: Dict) -> None:
        """Cache aggregated statistics"""
        self.stats_aggregated.set(f"stats:{stats_key}", stats)
    
    def should_send_websocket_batch(self, batch_key: str) -> bool:
        """Check if WebSocket batch should be sent (throttling)"""
        cache_key = f"ws_batch:{batch_key}"
        return self.websocket_batches.get(cache_key) is None
    
    def mark_websocket_batch_sent(self, batch_key: str) -> None:
        """Mark WebSocket batch as sent"""
        cache_key = f"ws_batch:{batch_key}"
        self.websocket_batches.set(cache_key, True, ttl=1)  # 1 second throttle
    
    def periodic_cleanup(self) -> None:
        """Run periodic cleanup if needed"""
        current_time = time.time()
        
        if (current_time - self._last_cleanup) > self._cleanup_interval:
            self._run_cleanup()
            self._last_cleanup = current_time
    
    def _run_cleanup(self) -> None:
        """Run cleanup on all caches"""
        total_removed = 0
        caches = {
            'torrent_metadata': self.torrent_metadata,
            'tracker_responses': self.tracker_responses,
            'stats_aggregated': self.stats_aggregated,
            'websocket_batches': self.websocket_batches
        }
        
        for cache_name, cache in caches.items():
            removed = cache.cleanup_expired()
            total_removed += removed
            
        if total_removed > 0:
            logger.info(f"🧹 Cache cleanup completed: removed {total_removed} expired entries")
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get statistics for all caches"""
        return {
            'torrent_metadata': self.torrent_metadata.get_stats(),
            'tracker_responses': self.tracker_responses.get_stats(),
            'stats_aggregated': self.stats_aggregated.get_stats(),
            'websocket_batches': self.websocket_batches.get_stats(),
            'last_cleanup': datetime.fromtimestamp(self._last_cleanup).isoformat()
        }
    
    def clear_all(self) -> None:
        """Clear all caches"""
        self.torrent_metadata.clear()
        self.tracker_responses.clear()
        self.stats_aggregated.clear()
        self.websocket_batches.clear()
        logger.info("🧹 All caches cleared")


# Global cache manager instance
cache_manager = CacheManager()