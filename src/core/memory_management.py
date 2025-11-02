"""Enhanced memory management and cleanup system for 3D printing operations."""

import gc
import psutil
import threading
import time
import weakref
import logging
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass
import sys
import os


@dataclass
class MemorySnapshot:
    """Snapshot of memory usage at a specific point in time."""
    timestamp: float
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size
    heap_mb: float  # Python heap size
    objects: int    # Number of Python objects
    gc_collections: Dict[int, int]  # GC collection counts by generation


class MemoryManager:
    """Advanced memory management system for 3D printing operations."""

    def __init__(self,
                 max_memory_percent: float = 80.0,
                 cleanup_interval: float = 60.0,
                 enable_gc_tuning: bool = True,
                 enable_weakrefs: bool = True):
        """Initialize memory manager.

        Args:
            max_memory_percent: Maximum memory usage percentage before triggering cleanup
            cleanup_interval: Interval between automatic cleanup checks in seconds
            enable_gc_tuning: Enable garbage collector tuning
            enable_weakrefs: Enable weak reference tracking for cleanup
        """
        self.logger = logging.getLogger(__name__)
        self.max_memory_percent = max_memory_percent
        self.cleanup_interval = cleanup_interval
        self.enable_gc_tuning = enable_gc_tuning
        self.enable_weakrefs = enable_weakrefs

        # Memory tracking
        self.snapshots: List[MemorySnapshot] = []
        self.max_snapshots = 1000
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Weak reference tracking
        self._weakrefs: Set[weakref.ref] = set() if enable_weakrefs else None

        # Performance metrics
        self.cleanup_count = 0
        self.forced_gc_count = 0
        self.memory_warnings = 0

        # Initialize memory monitoring
        if enable_gc_tuning:
            self._tune_garbage_collector()

        self._start_automatic_cleanup()

    def _tune_garbage_collector(self):
        """Tune Python's garbage collector for better performance."""
        try:
            # Get current thresholds
            current_thresholds = gc.get_threshold()

            # Optimize for 3D printing workloads (larger, less frequent collections)
            # Generation 0: Trigger after 700 allocations (default 700)
            # Generation 1: Trigger after 10 collections of gen 0 (default 10)
            # Generation 2: Trigger after 10 collections of gen 1 (default 10)
            gc.set_threshold(700, 10, 10)

            # Disable debug flags for better performance
            gc.set_debug(0)

            self.logger.info(f"Tuned GC thresholds from {current_thresholds} to {gc.get_threshold()}")

        except Exception as e:
            self.logger.warning(f"Failed to tune garbage collector: {e}")

    def _start_automatic_cleanup(self):
        """Start automatic memory cleanup thread."""
        if self._cleanup_thread is not None:
            return

        self._cleanup_thread = threading.Thread(
            target=self._automatic_cleanup_loop,
            daemon=True,
            name="MemoryCleanup"
        )
        self._cleanup_thread.start()
        self.logger.info("Started automatic memory cleanup")

    def _automatic_cleanup_loop(self):
        """Main loop for automatic memory cleanup."""
        while not self._stop_event.is_set():
            try:
                self._check_and_cleanup()
            except Exception as e:
                self.logger.error(f"Error in automatic cleanup: {e}")

            # Wait for next cleanup interval
            self._stop_event.wait(self.cleanup_interval)

    def _check_and_cleanup(self):
        """Check memory usage and perform cleanup if needed."""
        current_memory = self.get_current_memory_usage()

        if current_memory > self.max_memory_percent:
            self.logger.warning(f"Memory usage at {current_memory:.1f}%, triggering cleanup")
            self.memory_warnings += 1
            self.perform_cleanup()

    def get_current_memory_usage(self) -> float:
        """Get current memory usage as percentage of total system memory."""
        try:
            memory = psutil.virtual_memory()
            return memory.percent
        except Exception as e:
            self.logger.error(f"Failed to get memory usage: {e}")
            return 0.0

    def get_process_memory_info(self) -> Dict[str, float]:
        """Get detailed process memory information."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            return {
                'rss_mb': memory_info.rss / (1024 * 1024),  # Resident Set Size
                'vms_mb': memory_info.vms / (1024 * 1024),  # Virtual Memory Size
                'heap_mb': self._get_python_heap_size(),
                'memory_percent': process.memory_percent()
            }
        except Exception as e:
            self.logger.error(f"Failed to get process memory info: {e}")
            return {}

    def _get_python_heap_size(self) -> float:
        """Get Python heap size in MB."""
        try:
            # Force garbage collection to get accurate stats
            gc.collect()

            # Get object counts by generation
            heap_size = 0
            for i in range(gc.get_count()):
                heap_size += sys.getsizeof(gc.get_objects())

            return heap_size / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0

    def take_memory_snapshot(self) -> MemorySnapshot:
        """Take a snapshot of current memory usage."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            # Get GC stats
            gc_stats = gc.get_stats()
            gc_collections = {i: stats['collections'] for i, stats in enumerate(gc_stats)}

            snapshot = MemorySnapshot(
                timestamp=time.time(),
                rss_mb=memory_info.rss / (1024 * 1024),
                vms_mb=memory_info.vms / (1024 * 1024),
                heap_mb=self._get_python_heap_size(),
                objects=len(gc.get_objects()),
                gc_collections=gc_collections
            )

            # Store snapshot
            self.snapshots.append(snapshot)
            if len(self.snapshots) > self.max_snapshots:
                self.snapshots = self.snapshots[-self.max_snapshots:]

            return snapshot

        except Exception as e:
            self.logger.error(f"Failed to take memory snapshot: {e}")
            return MemorySnapshot(timestamp=time.time(), rss_mb=0, vms_mb=0, heap_mb=0, objects=0, gc_collections={})

    def perform_cleanup(self, force: bool = False) -> Dict[str, Any]:
        """Perform memory cleanup operations.

        Args:
            force: Force cleanup even if memory usage is not critical

        Returns:
            Dictionary with cleanup results
        """
        start_time = time.time()
        initial_memory = self.get_current_memory_usage()

        cleanup_results = {
            'gc_collections': 0,
            'objects_freed': 0,
            'memory_freed_mb': 0.0,
            'weakrefs_cleaned': 0,
            'duration_seconds': 0.0
        }

        try:
            # Take snapshot before cleanup
            before_snapshot = self.take_memory_snapshot()

            # Force garbage collection
            gc.collect(0)  # Collect generation 0
            cleanup_results['gc_collections'] += 1

            gc.collect(1)  # Collect generation 1
            cleanup_results['gc_collections'] += 1

            gc.collect(2)  # Collect generation 2
            cleanup_results['gc_collections'] += 1
            self.forced_gc_count += 1

            # Clean up weak references if enabled
            if self.enable_weakrefs and self._weakrefs is not None:
                initial_weakref_count = len(self._weakrefs)
                self._weakrefs = {ref for ref in self._weakrefs if ref() is not None}
                cleanup_results['weakrefs_cleaned'] = initial_weakref_count - len(self._weakrefs)

            # Take snapshot after cleanup
            after_snapshot = self.take_memory_snapshot()

            # Calculate results
            cleanup_results['objects_freed'] = before_snapshot.objects - after_snapshot.objects
            cleanup_results['memory_freed_mb'] = before_snapshot.heap_mb - after_snapshot.heap_mb
            cleanup_results['duration_seconds'] = time.time() - start_time

            final_memory = self.get_current_memory_usage()

            self.logger.info(
                f"Memory cleanup completed: "
                f"freed {cleanup_results['objects_freed']} objects, "
                f"{cleanup_results['memory_freed_mb']:.1f}MB, "
                f"memory {initial_memory:.1f}% -> {final_memory:.1f}% "
                f"({cleanup_results['duration_seconds']:.2f}s)"
            )

            self.cleanup_count += 1

        except Exception as e:
            self.logger.error(f"Error during memory cleanup: {e}")

        return cleanup_results

    def track_object(self, obj: Any) -> weakref.ref:
        """Track an object with a weak reference for automatic cleanup.

        Args:
            obj: Object to track

        Returns:
            Weak reference to the object
        """
        if not self.enable_weakrefs or self._weakrefs is None:
            return weakref.ref(obj)

        ref = weakref.ref(obj, self._object_finalized)
        self._weakrefs.add(ref)
        return ref

    def _object_finalized(self, ref: weakref.ref):
        """Callback when a tracked object is garbage collected."""
        if self._weakrefs is not None:
            self._weakrefs.discard(ref)

    def optimize_memory_layout(self):
        """Perform memory layout optimizations."""
        try:
            # Force defragmentation by creating and deleting large objects
            large_object = [0] * (1024 * 1024)  # 1MB list
            del large_object

            # Force minor GC to clean up
            gc.collect(0)

            self.logger.debug("Performed memory layout optimization")

        except Exception as e:
            self.logger.warning(f"Failed to optimize memory layout: {e}")

    def detect_memory_leaks(self, threshold_mb: float = 100.0) -> Dict[str, Any]:
        """Detect potential memory leaks by analyzing memory growth patterns.

        Args:
            threshold_mb: Memory growth threshold in MB to trigger leak detection

        Returns:
            Dictionary with leak detection results
        """
        if len(self.snapshots) < 10:
            return {'leak_detected': False, 'reason': 'Insufficient data'}

        try:
            # Analyze memory growth over time
            recent_snapshots = self.snapshots[-20:]  # Last 20 snapshots
            memory_growth = []

            for i in range(1, len(recent_snapshots)):
                before = recent_snapshots[i-1].heap_mb
                after = recent_snapshots[i].heap_mb
                growth = after - before
                memory_growth.append(growth)

            # Calculate average growth rate
            avg_growth = sum(memory_growth) / len(memory_growth)

            # Check for sustained growth
            sustained_growth = all(g > 0 for g in memory_growth[-5:])  # Last 5 intervals
            significant_growth = avg_growth > (threshold_mb / (self.cleanup_interval * len(memory_growth)))

            leak_detected = sustained_growth and significant_growth

            return {
                'leak_detected': leak_detected,
                'avg_growth_mb_per_interval': avg_growth,
                'sustained_growth': sustained_growth,
                'significant_growth': significant_growth,
                'sample_count': len(memory_growth),
                'recommendation': 'Monitor and restart if persistent' if leak_detected else 'No action needed'
            }

        except Exception as e:
            self.logger.error(f"Error detecting memory leaks: {e}")
            return {'leak_detected': False, 'error': str(e)}

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        current_memory = self.get_current_memory_usage()
        process_info = self.get_process_memory_info()

        recent_snapshots = self.snapshots[-10:] if self.snapshots else []

        return {
            'current_usage_percent': current_memory,
            'process_info': process_info,
            'snapshot_count': len(self.snapshots),
            'cleanup_count': self.cleanup_count,
            'forced_gc_count': self.forced_gc_count,
            'memory_warnings': self.memory_warnings,
            'recent_snapshots': [snapshot.__dict__ for snapshot in recent_snapshots],
            'weakrefs_tracked': len(self._weakrefs) if self._weakrefs else 0,
            'gc_thresholds': gc.get_threshold() if self.enable_gc_tuning else None
        }

    def stop(self):
        """Stop the memory manager and cleanup resources."""
        self.logger.info("Stopping memory manager...")

        if self._cleanup_thread:
            self._stop_event.set()
            self._cleanup_thread.join(timeout=5.0)
            self._cleanup_thread = None

        # Final cleanup
        self.perform_cleanup(force=True)

        self.logger.info("Memory manager stopped")


# Context manager for automatic memory management
class memory_context:
    """Context manager for automatic memory management during operations."""

    def __init__(self,
                 max_memory_percent: float = 85.0,
                 cleanup_on_exit: bool = True):
        self.max_memory_percent = max_memory_percent
        self.cleanup_on_exit = cleanup_on_exit
        self.memory_manager = MemoryManager(max_memory_percent=max_memory_percent)
        self.start_memory = 0.0

    def __enter__(self):
        self.start_memory = self.memory_manager.get_current_memory_usage()
        return self.memory_manager

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cleanup_on_exit:
            end_memory = self.memory_manager.get_current_memory_usage()
            memory_delta = end_memory - self.start_memory

            if memory_delta > 5.0:  # Only log if significant memory increase
                self.memory_manager.logger.info(
                    f"Memory context: {self.start_memory:.1f}% -> {end_memory:.1f}% "
                    f"(Δ{memory_delta:+.1f}%)"
                )

            # Always perform cleanup on exit
            self.memory_manager.perform_cleanup()


def force_memory_cleanup():
    """Force immediate memory cleanup."""
    memory_manager = MemoryManager()
    return memory_manager.perform_cleanup(force=True)


# Global memory manager instance
memory_manager = MemoryManager()
