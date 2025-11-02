"""Caching system for performance optimization."""
from typing import Any, Optional, Dict, Callable
from pathlib import Path
import pickle
import hashlib
import time
import json
import logging
from functools import wraps
from dataclasses import dataclass
import threading

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float]
    hit_count: int = 0


class MemoryCache:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600, max_memory_mb: int = 1024):
        """Initialize memory cache.

        Args:
            max_size: Maximum number of cached items
            default_ttl: Default time-to-live in seconds
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.max_memory_mb = max_memory_mb
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: Dict[str, CacheEntry] = {}
        self.lock = threading.RLock()
        self.hit_count = 0
        self.miss_count = 0
        self.current_memory_usage = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self.lock:
            if key not in self.cache:
                self.miss_count += 1
                return None

            entry = self.cache[key]

            # Check expiration
            if entry.expires_at and time.time() > entry.expires_at:
                del self.cache[key]
                self.miss_count += 1
                return None

            # Update statistics
            entry.hit_count += 1
            self.hit_count += 1

            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value in cache.

        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (None for default)
        """
        with self.lock:
            # Evict oldest entry if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()

            if ttl is None:
                ttl = self.default_ttl

            expires_at = time.time() + ttl if ttl > 0 else None

            self.cache[key] = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                expires_at=expires_at
            )

    def delete(self, key: str) -> bool:
        """Remove key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cached items."""
        with self.lock:
            self.cache.clear()
            self.hit_count = 0
            self.miss_count = 0

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.cache:
            return

        # Find entry with lowest hit count
        lru_key = min(self.cache.keys(), key=lambda k: self.cache[k].hit_count)
        del self.cache[lru_key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            total_requests = self.hit_count + self.miss_count
            hit_rate = self.hit_count / total_requests if total_requests > 0 else 0

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "hit_rate": hit_rate,
                "total_requests": total_requests
            }


class FileCache:
    """Persistent file-based cache."""

    def __init__(self, cache_dir: Path = Path("cache")):
        """Initialize file cache.

        Args:
            cache_dir: Directory for cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.index_file = self.cache_dir / "index.json"
        self.index = self._load_index()

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Load cache index from file."""
        if self.index_file.exists():
            try:
                with self.index_file.open("r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_index(self) -> None:
        """Save cache index to file."""
        with self.index_file.open("w") as f:
            json.dump(self.index, f)

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.pkl"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.index:
            return None

        entry = self.index[key]

        # Check expiration
        if entry.get("expires_at") and time.time() > entry["expires_at"]:
            self.delete(key)
            return None

        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            # Index out of sync, clean up
            del self.index[key]
            self._save_index()
            return None

        try:
            with cache_path.open("rb") as f:
                data = pickle.load(f)
                logger.debug(f"Cache hit for key: {key[:32]}...")
                return data
        except (pickle.PickleError, IOError) as e:
            # Corrupted cache file, clean up
            logger.warning(f"Corrupted cache file for key {key[:32]}...: {e}")
            self.delete(key)
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value in cache.

        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds
        """
        cache_path = self._get_cache_path(key)

        try:
            with cache_path.open("wb") as f:
                pickle.dump(value, f)

            self.index[key] = {
                "created_at": time.time(),
                "expires_at": time.time() + ttl if ttl else None,
                "path": str(cache_path)
            }
            self._save_index()

        except (pickle.PickleError, IOError) as e:
            # Clean up on failure
            logger.error(f"Failed to cache key {key[:32]}...: {e}")
            if cache_path.exists():
                cache_path.unlink()
            raise

    def delete(self, key: str) -> bool:
        """Remove key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        if key not in self.index:
            return False

        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()

        del self.index[key]
        self._save_index()
        return True

    def clear(self) -> None:
        """Clear all cached items."""
        file_count = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()
            file_count += 1

        self.index = {}
        self._save_index()
        logger.info(f"Cleared {file_count} cache files")


class MeshCache:
    """Specialized cache for mesh validation results."""

    def __init__(self, memory_cache: Optional[MemoryCache] = None):
        """Initialize mesh cache.

        Args:
            memory_cache: Optional memory cache instance
        """
        self.memory_cache = memory_cache or MemoryCache()

    def get_mesh_key(self, file_path: Path, settings_hash: Optional[str] = None) -> str:
        """Generate cache key for mesh file.

        Args:
            file_path: Path to mesh file
            settings_hash: Optional hash of validation settings

        Returns:
            Cache key string
        """
        # Get file modification time and size
        stat = file_path.stat()
        file_hash = f"{file_path.name}_{stat.st_mtime}_{stat.st_size}"

        if settings_hash:
            return f"mesh_{file_hash}_{settings_hash}"
        return f"mesh_{file_hash}"

    def get_validation_result(self, file_path: Path, settings_hash: Optional[str] = None) -> Optional[Any]:
        """Get cached validation result.

        Args:
            file_path: Path to mesh file
            settings_hash: Hash of validation settings

        Returns:
            Cached validation result or None
        """
        key = self.get_mesh_key(file_path, settings_hash)
        return self.memory_cache.get(key)

    def set_validation_result(
        self,
        file_path: Path,
        result: Any,
        settings_hash: Optional[str] = None,
        ttl: int = 3600
    ) -> None:
        """Cache validation result.

        Args:
            file_path: Path to mesh file
            result: Validation result to cache
            settings_hash: Hash of validation settings
            ttl: Time-to-live in seconds
        """
        key = self.get_mesh_key(file_path, settings_hash)
        self.memory_cache.set(key, result, ttl)


def cached(ttl: int = 3600, key_func: Optional[Callable] = None):
    """Decorator for caching function results.

    Args:
        ttl: Time-to-live in seconds
        key_func: Optional function to generate cache key from arguments

    Returns:
        Decorated function
    """
    cache = MemoryCache()

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                cache_key = f"{func.__name__}_{str(args)}_{str(kwargs)}"

            # Check cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, ttl)

            return result

        wrapper.cache = cache
        return wrapper

    return decorator


def preload_cache(keys: List[str], cache: MemoryCache) -> None:
    """Preload cache with specified keys."""
    for key in keys:
        if key not in cache.cache:
            # Placeholder - in real implementation, load actual data
            cache.cache[key] = CacheEntry(key, None, time.time(), None)