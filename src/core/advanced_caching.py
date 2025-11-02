"""Advanced caching system for performance optimization."""

import time
import threading
import hashlib
import pickle
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import weakref
from collections import OrderedDict


class CacheStrategy(Enum):
    """Cache eviction strategies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    SIZE = "size"  # Size-based eviction


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[float] = None
    tags: List[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        return (time.time() - self.created_at) > self.ttl_seconds

    def touch(self):
        """Update access time and increment access count."""
        self.accessed_at = time.time()
        self.access_count += 1


class AdvancedCache:
    """Advanced caching system with multiple eviction strategies."""

    def __init__(self,
                 max_size_mb: float = 100.0,
                 default_ttl: Optional[float] = None,
                 strategy: CacheStrategy = CacheStrategy.LRU):
        """Initialize advanced cache.

        Args:
            max_size_mb: Maximum cache size in MB
            default_ttl: Default time-to-live for cache entries in seconds
            strategy: Cache eviction strategy
        """
        self.logger = logging.getLogger(__name__)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.strategy = strategy

        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: OrderedDict = OrderedDict()  # For LRU
        self._frequency_count: Dict[str, int] = {}  # For LFU
        self._size_bytes = 0

        # Tag-based indexing
        self._tag_index: Dict[str, List[str]] = {}

        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'entries_added': 0,
            'entries_removed': 0
        }

        self._lock = threading.RLock()

    def get(self, key: str) -> Any:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self.stats['misses'] += 1
                return None

            entry = self._cache[key]

            # Check if expired
            if entry.is_expired():
                self._remove_entry(key)
                self.stats['misses'] += 1
                return None

            # Update access tracking
            entry.touch()

            if self.strategy == CacheStrategy.LRU:
                self._access_order.move_to_end(key)
            elif self.strategy == CacheStrategy.LFU:
                self._frequency_count[key] = entry.access_count

            self.stats['hits'] += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None,
            tags: Optional[List[str]] = None) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live for this entry (overrides default)
            tags: Tags for categorizing the entry

        Returns:
            True if successfully cached, False if not (e.g., too large)
        """
        with self._lock:
            # Serialize value to calculate size
            try:
                serialized = pickle.dumps(value)
                size_bytes = len(serialized)
            except (pickle.PicklingError, TypeError) as e:
                self.logger.warning(f"Failed to serialize cache value for key {key}: {e}")
                return False

            # Check size limit
            if size_bytes > self.max_size_bytes:
                self.logger.warning(f"Cache value too large for key {key}: {size_bytes} bytes")
                return False

            # Remove existing entry if present
            if key in self._cache:
                self._remove_entry(key)

            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                accessed_at=time.time(),
                size_bytes=size_bytes,
                ttl_seconds=ttl or self.default_ttl,
                tags=tags or []
            )

            # Add to cache
            self._cache[key] = entry
            self._size_bytes += size_bytes

            # Update tracking structures
            if self.strategy == CacheStrategy.LRU:
                self._access_order[key] = None
            elif self.strategy == CacheStrategy.LFU:
                self._frequency_count[key] = 1

            # Update tag index
            for tag in entry.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = []
                self._tag_index[tag].append(key)

            self.stats['entries_added'] += 1

            # Evict if necessary
            self._evict_if_needed()

            return True

    def delete(self, key: str) -> bool:
        """Delete entry from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if entry was deleted
        """
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False

    def clear(self, tags: Optional[List[str]] = None):
        """Clear cache entries.

        Args:
            tags: If provided, only clear entries with these tags
        """
        with self._lock:
            if tags:
                keys_to_remove = []
                for tag in tags:
                    if tag in self._tag_index:
                        keys_to_remove.extend(self._tag_index[tag])

                for key in set(keys_to_remove):
                    self._remove_entry(key)
            else:
                # Clear all
                for key in list(self._cache.keys()):
                    self._remove_entry(key)

    def _remove_entry(self, key: str):
        """Remove a cache entry."""
        if key not in self._cache:
            return

        entry = self._cache[key]
        self._size_bytes -= entry.size_bytes

        # Remove from tracking structures
        if self.strategy == CacheStrategy.LRU:
            self._access_order.pop(key, None)
        elif self.strategy == CacheStrategy.LFU:
            self._frequency_count.pop(key, None)

        # Remove from tag index
        for tag in entry.tags:
            if tag in self._tag_index:
                try:
                    self._tag_index[tag].remove(key)
                    if not self._tag_index[tag]:
                        del self._tag_index[tag]
                except ValueError:
                    pass

        del self._cache[key]
        self.stats['entries_removed'] += 1

    def _evict_if_needed(self):
        """Evict entries if cache size exceeds limit."""
        while self._size_bytes > self.max_size_bytes and self._cache:
            self._evict_one()

    def _evict_one(self):
        """Evict one entry based on current strategy."""
        if not self._cache:
            return

        if self.strategy == CacheStrategy.LRU:
            # Evict least recently used
            key_to_evict = next(iter(self._access_order))
        elif self.strategy == CacheStrategy.LFU:
            # Evict least frequently used
            key_to_evict = min(self._frequency_count, key=lambda k: self._frequency_count[k])
        elif self.strategy == CacheStrategy.SIZE:
            # Evict largest entry
            key_to_evict = max(self._cache, key=lambda k: self._cache[k].size_bytes)
        else:
            # Default to LRU
            key_to_evict = next(iter(self._access_order))

        self._remove_entry(key_to_evict)
        self.stats['evictions'] += 1
        self.logger.debug(f"Evicted cache entry: {key_to_evict}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0

            return {
                'entries': len(self._cache),
                'size_bytes': self._size_bytes,
                'size_mb': self._size_bytes / (1024 * 1024),
                'max_size_mb': self.max_size_bytes / (1024 * 1024),
                'utilization_percent': (self._size_bytes / self.max_size_bytes) * 100,
                'hit_rate': hit_rate,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'evictions': self.stats['evictions'],
                'entries_added': self.stats['entries_added'],
                'entries_removed': self.stats['entries_removed'],
                'tags': list(self._tag_index.keys()),
                'strategy': self.strategy.value
            }


class PersistentCache(AdvancedCache):
    """Cache with persistent storage to disk."""

    def __init__(self, cache_dir: Union[str, Path], **kwargs):
        """Initialize persistent cache.

        Args:
            cache_dir: Directory for cache storage
            **kwargs: Arguments passed to AdvancedCache
        """
        super().__init__(**kwargs)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load existing cache on startup
        self._load_persistent_cache()

    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for a key."""
        # Hash key to create filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{key_hash}.cache"

    def _load_persistent_cache(self):
        """Load cache entries from disk."""
        try:
            cache_files = list(self.cache_dir.glob("*.cache"))

            for cache_file in cache_files:
                try:
                    with open(cache_file, 'rb') as f:
                        entry = pickle.load(f)

                    if not entry.is_expired():
                        self._cache[entry.key] = entry
                        self._size_bytes += entry.size_bytes

                        # Restore tracking
                        if self.strategy == CacheStrategy.LRU:
                            self._access_order[entry.key] = None
                        elif self.strategy == CacheStrategy.LFU:
                            self._frequency_count[entry.key] = entry.access_count

                        # Restore tag index
                        for tag in entry.tags:
                            if tag not in self._tag_index:
                                self._tag_index[tag] = []
                            self._tag_index[tag].append(entry.key)

                except Exception as e:
                    self.logger.warning(f"Failed to load cache file {cache_file}: {e}")

            self.logger.info(f"Loaded {len(self._cache)} entries from persistent cache")

        except Exception as e:
            self.logger.error(f"Failed to load persistent cache: {e}")

    def set(self, key: str, value: Any, ttl: Optional[float] = None,
            tags: Optional[List[str]] = None) -> bool:
        """Set value in cache and persist to disk."""
        success = super().set(key, value, ttl, tags)

        if success:
            # Persist to disk
            self._save_entry_to_disk(key)

        return success

    def _save_entry_to_disk(self, key: str):
        """Save cache entry to disk."""
        if key not in self._cache:
            return

        try:
            cache_file = self._get_cache_file(key)
            entry = self._cache[key]

            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)

        except Exception as e:
            self.logger.error(f"Failed to save cache entry {key} to disk: {e}")

    def _remove_entry(self, key: str):
        """Remove cache entry from memory and disk."""
        super()._remove_entry(key)

        # Remove from disk
        cache_file = self._get_cache_file(key)
        try:
            if cache_file.exists():
                cache_file.unlink()
        except Exception as e:
            self.logger.warning(f"Failed to remove cache file {cache_file}: {e}")

    def cleanup_disk_cache(self, max_age_days: float = 7.0):
        """Clean up old cache files from disk.

        Args:
            max_age_days: Maximum age of cache files to keep
        """
        try:
            cutoff_time = time.time() - (max_age_days * 24 * 3600)

            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    if cache_file.stat().st_mtime < cutoff_time:
                        cache_file.unlink()
                        self.logger.debug(f"Removed old cache file: {cache_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove cache file {cache_file}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to cleanup disk cache: {e}")


class CacheManager:
    """Manager for multiple cache instances."""

    def __init__(self):
        """Initialize cache manager."""
        self.logger = logging.getLogger(__name__)
        self.caches: Dict[str, AdvancedCache] = {}
        self._lock = threading.RLock()

    def create_cache(self, name: str, **kwargs) -> AdvancedCache:
        """Create a new cache instance.

        Args:
            name: Cache name
            **kwargs: Cache configuration arguments

        Returns:
            Created cache instance
        """
        with self._lock:
            if name in self.caches:
                self.logger.warning(f"Cache {name} already exists, replacing")

            cache = AdvancedCache(**kwargs)
            self.caches[name] = cache
            self.logger.info(f"Created cache: {name}")

            return cache

    def create_persistent_cache(self, name: str, cache_dir: Union[str, Path], **kwargs) -> PersistentCache:
        """Create a new persistent cache instance.

        Args:
            name: Cache name
            cache_dir: Directory for persistent storage
            **kwargs: Cache configuration arguments

        Returns:
            Created persistent cache instance
        """
        with self._lock:
            if name in self.caches:
                self.logger.warning(f"Cache {name} already exists, replacing")

            cache = PersistentCache(cache_dir, **kwargs)
            self.caches[name] = cache
            self.logger.info(f"Created persistent cache: {name}")

            return cache

    def get_cache(self, name: str) -> Optional[AdvancedCache]:
        """Get cache instance by name.

        Args:
            name: Cache name

        Returns:
            Cache instance or None if not found
        """
        with self._lock:
            return self.caches.get(name)

    def list_caches(self) -> List[str]:
        """List all cache names.

        Returns:
            List of cache names
        """
        with self._lock:
            return list(self.caches.keys())

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches.

        Returns:
            Dictionary mapping cache names to their statistics
        """
        with self._lock:
            return {name: cache.get_stats() for name, cache in self.caches.items()}

    def clear_all_caches(self):
        """Clear all cache instances."""
        with self._lock:
            for cache in self.caches.values():
                cache.clear()
            self.logger.info("Cleared all caches")


# Decorator for automatic caching
def cache_result(cache_instance: AdvancedCache, ttl: Optional[float] = None,
                key_func: Optional[Callable] = None, tags: Optional[List[str]] = None):
    """Decorator to automatically cache function results.

    Args:
        cache_instance: Cache instance to use
        ttl: Time-to-live for cached results
        key_func: Function to generate cache key from arguments
        tags: Tags for cache entries

    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
                cache_key = hashlib.sha256(key_data.encode()).hexdigest()

            # Try to get from cache
            result = cache_instance.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_instance.set(cache_key, result, ttl=ttl, tags=tags)

            return result

        return wrapper
    return decorator


# Global cache manager
cache_manager = CacheManager()


# Convenience functions
def get_cache(name: str, **kwargs) -> AdvancedCache:
    """Get or create a cache instance."""
    cache = cache_manager.get_cache(name)
    if cache is None:
        cache = cache_manager.create_cache(name, **kwargs)
    return cache


def cache_function(func: Callable, cache_name: str = None, ttl: float = None, **cache_kwargs):
    """Cache a function with automatic key generation."""
    if cache_name is None:
        cache_name = f"func_{func.__name__}"

    cache = get_cache(cache_name, **cache_kwargs)

    return cache_result(cache, ttl=ttl)(func)
