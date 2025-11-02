"""Memory management utilities for efficient mesh processing."""
from __future__ import annotations

import gc
import psutil
import logging
import threading
import numpy as np
from typing import Dict, Optional, Any, Callable, Tuple, List
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
import time
from collections import defaultdict

class ArrayPool:
    """Memory-efficient array pool for numpy arrays."""

    def __init__(self, max_size_mb: float = 500.0):
        self.max_size_mb = max_size_mb
        self._pools: Dict[Tuple[int, ...], List[np.ndarray]] = defaultdict(list)
        self._pool_sizes: Dict[Tuple[int, ...], int] = defaultdict(int)
        self._lock = threading.RLock()
        self._total_allocated_mb = 0.0

    def get_array(self, shape: Tuple[int, ...], dtype: np.dtype = np.float64) -> np.ndarray:
        """Get an array from the pool or create a new one."""
        with self._lock:
            key = (shape, dtype)

            # Try to get from pool
            if key in self._pools and self._pools[key]:
                array = self._pools[key].pop()
                self._pool_sizes[key] -= 1
                return array

            # Create new array
            array = np.empty(shape, dtype=dtype)
            self._total_allocated_mb += array.nbytes / (1024 * 1024)
            return array

    def return_array(self, array: np.ndarray):
        """Return an array to the pool for reuse."""
        with self._lock:
            if self._total_allocated_mb > self.max_size_mb:
                # Pool is full, don't store
                return

            key = (array.shape, array.dtype)
            self._pools[key].append(array)
            self._pool_sizes[key] += 1

            # Limit pool size per type
            max_per_type = 100
            if self._pool_sizes[key] > max_per_type:
                excess = self._pool_sizes[key] - max_per_type
                self._pools[key] = self._pools[key][excess:]
                self._pool_sizes[key] = max_per_type

    def clear_pool(self):
        """Clear all pooled arrays."""
        with self._lock:
            total_cleared = sum(len(arrays) for arrays in self._pools.values())
            self._pools.clear()
            self._pool_sizes.clear()
            self._total_allocated_mb = 0.0
            return total_cleared

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                "total_pooled_arrays": sum(self._pool_sizes.values()),
                "pool_types": len(self._pools),
                "total_allocated_mb": self._total_allocated_mb,
                "pool_sizes": dict(self._pool_sizes)
            }


class SmartMemoryManager:
    """Advanced memory manager with pooling and optimization."""

    def __init__(self):
        self.array_pool = ArrayPool()
        self.leak_detector = MemoryLeakDetector()
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_max_size = 100
        self._cache_ttl = 300  # 5 minutes
        self._lock = threading.RLock()

    def get_cached_item(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired."""
        with self._lock:
            if key in self._cache:
                item, timestamp = self._cache[key]
                if time.time() - timestamp < self._cache_ttl:
                    return item
                else:
                    del self._cache[key]
            return None

    def set_cached_item(self, key: str, item: Any):
        """Set item in cache."""
        with self._lock:
            # Clean expired items
            current_time = time.time()
            expired_keys = [k for k, (_, ts) in self._cache.items() if current_time - ts > self._cache_ttl]
            for k in expired_keys:
                del self._cache[k]

            # Add new item
            if len(self._cache) < self._cache_max_size:
                self._cache[key] = (item, current_time)

    def optimize_memory_usage(self):
        """Perform memory optimization."""
        # Force garbage collection
        gc.collect()

        # Clear cache if needed
        with self._lock:
            if len(self._cache) > self._cache_max_size * 0.8:
                # Clear half the cache
                keys_to_delete = list(self._cache.keys())[:len(self._cache) // 2]
                for key in keys_to_delete:
                    del self._cache[key]

        # Clear array pool if too large
        if self.array_pool._total_allocated_mb > self.array_pool.max_size_mb * 0.9:
            cleared = self.array_pool.clear_pool()
            logger.info(f"Cleared {cleared} pooled arrays to free memory")


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    total_mb: float
    available_mb: float
    used_mb: float
    used_percent: float
    process_mb: float
    mesh_cache_mb: float
    array_pool_mb: float


class MemoryLeakDetector:
    """Advanced memory leak detection and automatic garbage collection."""

    def __init__(self, enable_auto_gc: bool = True, gc_threshold_mb: float = 100.0):
        self.enable_auto_gc = enable_auto_gc
        self.gc_threshold_mb = gc_threshold_mb
        self._baseline_memory_mb = 0.0
        self._allocation_history: List[Tuple[float, float, str]] = []
        self._gc_history: List[Tuple[float, float, str]] = []
        self._memory_snapshots: List[MemoryStats] = []
        self._lock = threading.RLock()
        self._last_gc_time = 0.0
        self._gc_interval_seconds = 30.0  # GC every 30 seconds if needed

    def start_monitoring(self):
        """Start memory leak monitoring."""
        with self._lock:
            self._baseline_memory_mb = self._get_process_memory_mb()
            self._allocation_history.clear()
            self._gc_history.clear()
            self._memory_snapshots.clear()

            logger.info(f"Memory leak detection started. Baseline: {self._baseline_memory_mb:.2f}MB")

    def record_allocation(self, size_mb: float, operation: str):
        """Record a memory allocation."""
        with self._lock:
            current_time = time.time()
            self._allocation_history.append((current_time, size_mb, operation))

            # Keep only recent history (last 1000 allocations)
            if len(self._allocation_history) > 1000:
                self._allocation_history = self._allocation_history[-1000:]

    def _get_process_memory_mb(self) -> float:
        """Get current process memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0

    def _get_system_memory_mb(self) -> float:
        """Get system memory usage in MB."""
        try:
            return psutil.virtual_memory().used / (1024 * 1024)
        except Exception:
            return 0.0

    def check_for_leaks(self) -> Tuple[bool, str]:
        """Check for potential memory leaks."""
        with self._lock:
            current_memory_mb = self._get_process_memory_mb()

            # Take memory snapshot
            snapshot = MemoryStats(
                total_mb=psutil.virtual_memory().total / (1024 * 1024),
                available_mb=psutil.virtual_memory().available / (1024 * 1024),
                used_mb=current_memory_mb,
                used_percent=(current_memory_mb / (psutil.virtual_memory().total / (1024 * 1024))) * 100,
                process_mb=current_memory_mb,
                mesh_cache_mb=0.0,  # Would need mesh cache integration
                array_pool_mb=0.0   # Would need array pool integration
            )
            self._memory_snapshots.append(snapshot)

            # Keep only recent snapshots (last 100)
            if len(self._memory_snapshots) > 100:
                self._memory_snapshots = self._memory_snapshots[-100:]

            # Check if memory usage has grown significantly since baseline
            memory_growth_mb = current_memory_mb - self._baseline_memory_mb

            if memory_growth_mb > self.gc_threshold_mb:
                # Analyze allocation patterns
                recent_allocations = [
                    (timestamp, size, op) for timestamp, size, op in self._allocation_history
                    if time.time() - timestamp < 300  # Last 5 minutes
                ]

                if len(recent_allocations) > 50:  # Many allocations without corresponding frees
                    return True, f"Potential memory leak detected. Memory grew by {memory_growth_mb:.2f}MB with {len(recent_allocations)} recent allocations."

            return False, ""

    def trigger_garbage_collection(self, reason: str = "manual") -> Tuple[float, int]:
        """Trigger garbage collection and return results."""
        with self._lock:
            pre_gc_memory = self._get_process_memory_mb()

            # Force garbage collection
            gc.collect()

            # Additional cleanup for different Python implementations
            try:
                # Try to collect cyclic garbage
                collected = gc.collect()

                # Clear any object pools or caches if they exist
                # This would need integration with specific caching systems

            except Exception as e:
                logger.warning(f"Garbage collection warning: {e}")
                collected = 0

            post_gc_memory = self._get_process_memory_mb()
            memory_freed = pre_gc_memory - post_gc_memory

            # Record GC event
            current_time = time.time()
            self._gc_history.append((current_time, memory_freed, reason))
            self._last_gc_time = current_time

            # Keep only recent GC history (last 100 events)
            if len(self._gc_history) > 100:
                self._gc_history = self._gc_history[-100:]

            logger.info(
                f"Garbage collection triggered ({reason}): "
                f"freed {memory_freed:.2f}MB, collected {collected} objects"
            )

            return memory_freed, collected

    def should_trigger_gc(self) -> Tuple[bool, str]:
        """Determine if garbage collection should be triggered."""
        with self._lock:
            current_time = time.time()

            # Check if enough time has passed since last GC
            if current_time - self._last_gc_time < self._gc_interval_seconds:
                return False, "Too soon since last garbage collection"

            # Check for potential memory leaks
            leak_detected, leak_reason = self.check_for_leaks()
            if leak_detected:
                return True, f"Memory leak detected: {leak_reason}"

            # Check if memory usage is high
            current_memory_mb = self._get_process_memory_mb()
            if current_memory_mb > self.gc_threshold_mb * 2:
                return True, f"High memory usage: {current_memory_mb:.2f}MB"

            return False, "No garbage collection needed"

    def get_memory_report(self) -> Dict[str, Any]:
        """Generate comprehensive memory report."""
        with self._lock:
            current_memory_mb = self._get_process_memory_mb()

            # Calculate allocation statistics
            recent_allocations = [
                size for timestamp, size, op in self._allocation_history
                if time.time() - timestamp < 3600  # Last hour
            ]

            total_allocated_mb = sum(recent_allocations) if recent_allocations else 0.0

            # GC statistics
            recent_gc_events = [
                (timestamp, freed, reason) for timestamp, freed, reason in self._gc_history
                if time.time() - timestamp < 3600  # Last hour
            ]

            total_freed_mb = sum(freed for _, freed, _ in recent_gc_events) if recent_gc_events else 0.0

            return {
                'current_memory_mb': current_memory_mb,
                'baseline_memory_mb': self._baseline_memory_mb,
                'memory_growth_mb': current_memory_mb - self._baseline_memory_mb,
                'recent_allocations_count': len(recent_allocations),
                'recent_allocations_mb': total_allocated_mb,
                'recent_gc_events_count': len(recent_gc_events),
                'recent_gc_freed_mb': total_freed_mb,
                'gc_threshold_mb': self.gc_threshold_mb,
                'auto_gc_enabled': self.enable_auto_gc,
                'last_gc_time': self._last_gc_time,
                'monitoring_active': len(self._allocation_history) > 0
            }

    def auto_cleanup(self):
        """Perform automatic memory cleanup if needed."""
        if not self.enable_auto_gc:
            return

        should_gc, reason = self.should_trigger_gc()
        if should_gc:
            logger.info(f"Auto-triggering garbage collection: {reason}")
            self.trigger_garbage_collection(f"auto: {reason}")
    """Memory pool for temporary NumPy arrays used in mesh processing."""

    def __init__(self, max_size_mb: float = 256.0):
        self.max_size_mb = max_size_mb
        self._pools: Dict[Tuple[int, str], List[np.ndarray]] = defaultdict(list)
        self._current_size_mb = 0.0
        self._lock = threading.RLock()
        self._allocation_stats = {
            'total_allocations': 0,
            'pool_hits': 0,
            'pool_misses': 0,
            'freed_arrays': 0
        }

    def _estimate_array_size_mb(self, array: np.ndarray) -> float:
        """Estimate memory usage of a NumPy array in MB."""
        return array.nbytes / (1024 * 1024)

    def _get_pool_key(self, shape: Tuple[int, ...], dtype: str) -> Tuple[Tuple[int, ...], str]:
        """Generate pool key for array shape and dtype."""
        return (shape, dtype)

    def get_array(self, shape: Tuple[int, ...], dtype: np.dtype = np.float64) -> np.ndarray:
        """Get array from pool or create new one."""
        dtype_str = str(dtype)

        with self._lock:
            pool_key = self._get_pool_key(shape, dtype_str)
            pool = self._pools[pool_key]

            # Try to get array from pool
            if pool:
                array = pool.pop()
                self._allocation_stats['pool_hits'] += 1
                logger.debug(f"Reused array from pool: {shape}, {dtype}")
                return array

            # Pool miss - create new array
            self._allocation_stats['pool_misses'] += 1
            array = np.empty(shape, dtype=dtype)
            array_size_mb = self._estimate_array_size_mb(array)

            # Check if we need to evict some arrays
            self._evict_if_needed(array_size_mb)

            self._current_size_mb += array_size_mb
            logger.debug(f"Created new array: {shape}, {dtype} ({array_size_mb:.2f}MB)")

            return array

    def return_array(self, array: np.ndarray):
        """Return array to pool for reuse."""
        if array is None:
            return

        with self._lock:
            shape = array.shape
            dtype_str = str(array.dtype)
            pool_key = self._get_pool_key(shape, dtype_str)

            # Only pool if we have space and array is not too large
            array_size_mb = self._estimate_array_size_mb(array)
            max_single_array_mb = self.max_size_mb * 0.1  # Max 10% per array

            if array_size_mb < max_single_array_mb:
                pool = self._pools[pool_key]

                # Limit pool size to prevent excessive memory usage
                max_pool_size = 10  # Max 10 arrays per pool
                if len(pool) < max_pool_size:
                    # Clear array to free memory immediately
                    array.fill(0)
                    pool.append(array)
                    self._allocation_stats['freed_arrays'] += 1
                    logger.debug(f"Returned array to pool: {shape}, {dtype}")
                else:
                    logger.debug(f"Pool full, not caching array: {shape}, {dtype}")
            else:
                logger.debug(f"Array too large for pool: {array_size_mb:.2f}MB")

    def _evict_if_needed(self, new_array_size_mb: float):
        """Evict arrays if adding new array would exceed limit."""
        while (self._current_size_mb + new_array_size_mb > self.max_size_mb and
               any(self._pools.values())):

            # Find largest pool and remove one array
            largest_pool_key = None
            largest_pool_size = 0

            for key, pool in self._pools.items():
                if len(pool) > largest_pool_size:
                    largest_pool_size = len(pool)
                    largest_pool_key = key

            if largest_pool_key:
                pool = self._pools[largest_pool_key]
                if pool:
                    removed_array = pool.pop()
                    removed_size_mb = self._estimate_array_size_mb(removed_array)
                    self._current_size_mb -= removed_size_mb
                    logger.debug(f"Evicted array from pool: {removed_size_mb:.2f}MB")
                else:
                    break
            else:
                break

    def clear(self):
        """Clear all pooled arrays."""
        with self._lock:
            total_arrays = sum(len(pool) for pool in self._pools.values())
            self._pools.clear()
            self._current_size_mb = 0.0
            logger.info(f"Cleared array pool ({total_arrays} arrays)")

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            total_pooled_arrays = sum(len(pool) for pool in self._pools.values())

            return {
                'size_mb': self._current_size_mb,
                'max_size_mb': self.max_size_mb,
                'usage_percent': (self._current_size_mb / self.max_size_mb) * 100,
                'pooled_arrays': total_pooled_arrays,
                'pool_keys': len(self._pools),
                **self._allocation_stats
            }


class MemoryMonitor:
    """Monitor system and process memory usage."""

    def __init__(self):
        self.process = psutil.Process()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stats_callback: Optional[Callable[[MemoryStats], None]] = None

    def get_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        # System memory
        system_mem = psutil.virtual_memory()

        # Process memory
        process_mem = self.process.memory_info()

        # Estimate mesh cache usage (simplified)
        mesh_cache_mb = getattr(self, '_mesh_cache_size_mb', 0.0)

        # Array pool usage
        array_pool_mb = getattr(self, '_array_pool_size_mb', 0.0)

        return MemoryStats(
            total_mb=system_mem.total / (1024 * 1024),
            available_mb=system_mem.available / (1024 * 1024),
            used_mb=system_mem.used / (1024 * 1024),
            used_percent=system_mem.percent,
            process_mb=process_mem.rss / (1024 * 1024),
            mesh_cache_mb=mesh_cache_mb,
            array_pool_mb=array_pool_mb
        )


class MemoryMonitor:
    """Monitor system and process memory usage."""

    def __init__(self):
        self.process = psutil.Process()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stats_callback: Optional[Callable[[MemoryStats], None]] = None

    def get_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        # System memory
        system_mem = psutil.virtual_memory()

        # Process memory
        process_mem = self.process.memory_info()

        # Estimate mesh cache usage (simplified)
        mesh_cache_mb = getattr(self, '_mesh_cache_size_mb', 0.0)

        return MemoryStats(
            total_mb=system_mem.total / (1024 * 1024),
            available_mb=system_mem.available / (1024 * 1024),
            used_mb=system_mem.used / (1024 * 1024),
            used_percent=system_mem.percent,
            process_mb=process_mem.rss / (1024 * 1024),
            mesh_cache_mb=mesh_cache_mb
        )

    def start_monitoring(self, interval: float = 5.0,
                        callback: Optional[Callable[[MemoryStats], None]] = None):
        """Start continuous memory monitoring."""
        if self._monitoring:
            return

        self._monitoring = True
        self._stats_callback = callback

        def monitor_loop():
            while self._monitoring:
                try:
                    stats = self.get_stats()

                    # Log warning if memory usage is high
                    if stats.used_percent > 90:
                        logger.warning(f"High memory usage: {stats.used_percent:.1f}% ({stats.used_mb:.1f}MB)")

                    # Call callback if provided
                    if self._stats_callback:
                        self._stats_callback(stats)

                except Exception as e:
                    logger.error(f"Error in memory monitoring: {e}")

                time.sleep(interval)

        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Memory monitoring started")

    def stop_monitoring(self):
        """Stop memory monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        logger.info("Memory monitoring stopped")

    def check_available_memory(self, required_mb: float) -> bool:
        """Check if sufficient memory is available."""
        stats = self.get_stats()
        return stats.available_mb >= required_mb

    def estimate_file_memory_requirements(self, file_path: Path) -> float:
        """Estimate memory requirements for processing a file."""
        try:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)

            # Rough estimates based on file format
            if file_path.suffix.lower() == '.stl':
                # STL: vertices + faces + normals + overhead
                return file_size_mb * 4.0
            elif file_path.suffix.lower() == '.obj':
                # OBJ: typically more compact, but can have textures
                return file_size_mb * 3.0
            elif file_path.suffix.lower() == '.ply':
                # PLY: variable, but usually efficient
                return file_size_mb * 2.5
            elif file_path.suffix.lower() in ['.3mf', '.amf']:
                # Compressed formats
                return file_size_mb * 6.0
            else:
                # Conservative estimate
                return file_size_mb * 5.0

        except Exception:
            # Default conservative estimate
            return 100.0  # 100MB default


class MeshCache:
    """LRU cache for loaded meshes with memory management."""

    def __init__(self, max_size_mb: float = 512.0):
        self.max_size_mb = max_size_mb
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_order: list = []
        self._current_size_mb = 0.0
        self._lock = threading.RLock()

    def _estimate_mesh_size(self, mesh) -> float:
        """Estimate memory usage of a mesh in MB."""
        try:
            # Vertices: 3 floats per vertex * 4 bytes per float
            vertex_bytes = len(mesh.vertices) * 3 * 4

            # Faces: 3 ints per face * 4 bytes per int
            face_bytes = len(mesh.faces) * 3 * 4

            # Additional data (normals, colors, etc.)
            extra_bytes = 0
            if hasattr(mesh, 'vertex_normals') and mesh.vertex_normals is not None:
                extra_bytes += len(mesh.vertex_normals) * 3 * 4
            if hasattr(mesh, 'vertex_colors') and mesh.vertex_colors is not None:
                extra_bytes += len(mesh.vertex_colors) * 4 * 4

            total_bytes = vertex_bytes + face_bytes + extra_bytes
            return total_bytes / (1024 * 1024)  # Convert to MB

        except Exception:
            return 10.0  # Default estimate

    def _evict_lru(self):
        """Evict least recently used items until under size limit."""
        with self._lock:
            while (self._current_size_mb > self.max_size_mb and
                   self._access_order and len(self._cache) > 0):

                # Remove oldest item
                oldest_key = self._access_order.pop(0)
                if oldest_key in self._cache:
                    item = self._cache.pop(oldest_key)
                    self._current_size_mb -= item['size_mb']
                    logger.debug(f"Evicted mesh from cache: {oldest_key}")

    def get(self, key: str):
        """Get mesh from cache."""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]['mesh']
            return None

    def put(self, key: str, mesh, file_path: Optional[Path] = None):
        """Add mesh to cache."""
        size_mb = self._estimate_mesh_size(mesh)

        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                old_item = self._cache.pop(key)
                self._current_size_mb -= old_item['size_mb']
                self._access_order.remove(key)

            # Add new entry
            self._cache[key] = {
                'mesh': mesh,
                'size_mb': size_mb,
                'timestamp': time.time(),
                'file_path': str(file_path) if file_path else None
            }
            self._access_order.append(key)
            self._current_size_mb += size_mb

            # Evict if necessary
            self._evict_lru()

            logger.debug(f"Cached mesh: {key} ({size_mb:.1f}MB)")

    def clear(self):
        """Clear all cached meshes."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._current_size_mb = 0.0
            logger.info("Mesh cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'entries': len(self._cache),
                'size_mb': self._current_size_mb,
                'max_size_mb': self.max_size_mb,
                'usage_percent': (self._current_size_mb / self.max_size_mb) * 100
            }


class MemoryManager:
    """Central memory management for the application."""

    def __init__(self, cache_size_mb: float = 512.0):
        self.monitor = MemoryMonitor()
        self.mesh_cache = MeshCache(cache_size_mb)
        self._low_memory_threshold = 85.0  # Percentage
        self._critical_memory_threshold = 95.0  # Percentage

    def start_monitoring(self):
        """Start memory monitoring with automatic cleanup."""
        def memory_callback(stats: MemoryStats):
            if stats.used_percent > self._critical_memory_threshold:
                logger.warning(f"Critical memory usage: {stats.used_percent:.1f}%")
                self.emergency_cleanup()
            elif stats.used_percent > self._low_memory_threshold:
                logger.info(f"High memory usage: {stats.used_percent:.1f}%, performing cleanup")
                self.soft_cleanup()

        self.monitor.start_monitoring(callback=memory_callback)

    def stop_monitoring(self):
        """Stop memory monitoring."""
        self.monitor.stop_monitoring()

    def soft_cleanup(self):
        """Perform soft memory cleanup."""
        # Clear half of the mesh cache
        with self.mesh_cache._lock:
            entries_to_remove = len(self.mesh_cache._cache) // 2
            for _ in range(entries_to_remove):
                if self.mesh_cache._access_order:
                    oldest_key = self.mesh_cache._access_order.pop(0)
                    if oldest_key in self.mesh_cache._cache:
                        item = self.mesh_cache._cache.pop(oldest_key)
                        self.mesh_cache._current_size_mb -= item['size_mb']

        # Force garbage collection
        gc.collect()
        logger.info("Soft memory cleanup completed")

    def emergency_cleanup(self):
        """Perform aggressive memory cleanup."""
        # Clear entire mesh cache
        self.mesh_cache.clear()

        # Force garbage collection
        gc.collect()

        logger.warning("Emergency memory cleanup completed")

    def get_system_stats(self) -> MemoryStats:
        """Get comprehensive memory statistics."""
        stats = self.monitor.get_stats()
        stats.mesh_cache_mb = self.mesh_cache._current_size_mb
        return stats

    def check_memory_for_operation(self, required_mb: float) -> bool:
        """Check if enough memory is available for an operation."""
        stats = self.get_system_stats()

        # Consider both system available memory and potential cache cleanup
        available_with_cleanup = stats.available_mb + (stats.mesh_cache_mb * 0.8)

        if available_with_cleanup < required_mb:
            logger.warning(f"Insufficient memory: need {required_mb}MB, have {available_with_cleanup}MB")
            return False

        # If tight, perform preemptive cleanup
        if stats.available_mb < required_mb:
            logger.info("Performing preemptive memory cleanup")
            self.soft_cleanup()

        return True

    @contextmanager
    def memory_context(self, operation_name: str, estimated_mb: float = 0):
        """Context manager for memory-monitored operations."""
        start_stats = self.get_system_stats()
        logger.debug(f"Starting {operation_name} (estimated: {estimated_mb}MB)")

        if estimated_mb > 0 and not self.check_memory_for_operation(estimated_mb):
            raise MemoryError(f"Insufficient memory for {operation_name}")

        try:
            yield
        finally:
            end_stats = self.get_system_stats()
            memory_diff = end_stats.process_mb - start_stats.process_mb
            logger.debug(f"Completed {operation_name} (actual memory change: {memory_diff:+.1f}MB)")


# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


def init_memory_management(cache_size_mb: float = 512.0):
    """Initialize memory management system."""
    global _memory_manager
    _memory_manager = MemoryManager(cache_size_mb)
    _memory_manager.start_monitoring()
    logger.info(f"Memory management initialized with {cache_size_mb}MB cache")


def cleanup_memory():
    """Cleanup memory management system."""
    global _memory_manager
    if _memory_manager:
        _memory_manager.stop_monitoring()
        _memory_manager.mesh_cache.clear()
        _memory_manager = None
    logger.info("Memory management cleanup completed")


@contextmanager
def memory_monitored_operation(operation_name: str, estimated_mb: float = 0):
    """Context manager for memory-monitored operations."""
    manager = get_memory_manager()
    with manager.memory_context(operation_name, estimated_mb):
        yield