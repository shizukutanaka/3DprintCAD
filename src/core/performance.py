"""Performance optimization utilities."""
import time
import psutil
import tracemalloc
from typing import Optional, Callable, Any, Dict
from functools import wraps
from contextlib import contextmanager
import logging
from dataclasses import dataclass
import numpy as np
import numba
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    execution_time: float
    memory_used: float
    cpu_percent: float
    function_name: str
    args_size: int
    result_size: int


class PerformanceMonitor:
    """Monitor and log performance metrics."""

    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: Dict[str, list] = {}
        self.process = psutil.Process()

    def record(self, metrics: PerformanceMetrics) -> None:
        """Record performance metrics.

        Args:
            metrics: Performance metrics to record
        """
        if metrics.function_name not in self.metrics:
            self.metrics[metrics.function_name] = []

        self.metrics[metrics.function_name].append(metrics)

    def get_summary(self, function_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary.

        Args:
            function_name: Optional specific function to summarize

        Returns:
            Dictionary with performance statistics
        """
        if function_name:
            if function_name not in self.metrics:
                return {}

            metrics_list = self.metrics[function_name]
        else:
            metrics_list = []
            for func_metrics in self.metrics.values():
                metrics_list.extend(func_metrics)

        if not metrics_list:
            return {}

        exec_times = [m.execution_time for m in metrics_list]
        memory_used = [m.memory_used for m in metrics_list]
        cpu_percent = [m.cpu_percent for m in metrics_list]

        return {
            "count": len(metrics_list),
            "total_time": sum(exec_times),
            "avg_time": np.mean(exec_times),
            "min_time": min(exec_times),
            "max_time": max(exec_times),
            "avg_memory": np.mean(memory_used),
            "avg_cpu": np.mean(cpu_percent)
        }

    def clear(self) -> None:
        """Clear all recorded metrics."""
        self.metrics.clear()


# Global performance monitor
_monitor = PerformanceMonitor()


def profile(func: Callable) -> Callable:
    """Decorator to profile function performance.

    Args:
        func: Function to profile

    Returns:
        Wrapped function
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # Start monitoring
        start_time = time.perf_counter()
        start_memory = _monitor.process.memory_info().rss / 1024 / 1024  # MB
        _monitor.process.cpu_percent()  # First call to initialize

        # Execute function
        result = func(*args, **kwargs)

        # Calculate metrics
        execution_time = time.perf_counter() - start_time
        end_memory = _monitor.process.memory_info().rss / 1024 / 1024
        memory_used = end_memory - start_memory
        cpu_percent = _monitor.process.cpu_percent()

        # Estimate sizes
        args_size = len(str(args)) + len(str(kwargs))
        result_size = len(str(result)) if result else 0

        # Record metrics
        metrics = PerformanceMetrics(
            execution_time=execution_time,
            memory_used=memory_used,
            cpu_percent=cpu_percent,
            function_name=func.__name__,
            args_size=args_size,
            result_size=result_size
        )
        _monitor.record(metrics)

        # Log if slow
        if execution_time > 1.0:
            logger.warning(
                f"{func.__name__} took {execution_time:.2f}s "
                f"(memory: {memory_used:.1f}MB, CPU: {cpu_percent:.1f}%)"
            )

        return result

    return wrapper


@contextmanager
def time_block(name: str = "Operation"):
    """Context manager for timing code blocks.

    Args:
        name: Name of the operation being timed

    Yields:
        None
    """
    start = time.perf_counter()
    logger.debug(f"Starting {name}")

    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.debug(f"{name} completed in {elapsed:.3f}s")


@contextmanager
def memory_tracker(name: str = "Operation"):
    """Context manager for tracking memory usage.

    Args:
        name: Name of the operation being tracked

    Yields:
        None
    """
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    try:
        yield
    finally:
        snapshot_after = tracemalloc.take_snapshot()
        top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')

        total_size = sum(stat.size_diff for stat in top_stats)
        logger.debug(f"{name} allocated {total_size / 1024 / 1024:.2f}MB")

        # Log top memory consumers if significant
        if total_size > 10 * 1024 * 1024:  # > 10MB
            logger.info(f"Top memory allocations for {name}:")
            for stat in top_stats[:3]:
                logger.info(f"  {stat}")

        tracemalloc.stop()


class BatchProcessor:
    """Optimized batch processing with parallelization."""

    def __init__(
        self,
        max_workers: Optional[int] = None,
        use_processes: bool = False,
        batch_size: int = 100
    ):
        """Initialize batch processor.

        Args:
            max_workers: Maximum number of parallel workers
            use_processes: Use process pool instead of thread pool
            batch_size: Size of batches for processing
        """
        self.max_workers = max_workers
        self.use_processes = use_processes
        self.batch_size = batch_size

    def process(
        self,
        items: list,
        func: Callable,
        show_progress: bool = True
    ) -> list:
        """Process items in parallel batches.

        Args:
            items: List of items to process
            func: Function to apply to each item
            show_progress: Show progress bar

        Returns:
            List of results
        """
        if not items:
            return []

        # Choose executor
        executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor

        results = []
        total_batches = (len(items) + self.batch_size - 1) // self.batch_size

        with executor_class(max_workers=self.max_workers) as executor:
            # Process in batches
            for i in range(0, len(items), self.batch_size):
                batch = items[i:i + self.batch_size]
                batch_futures = [executor.submit(func, item) for item in batch]

                # Collect batch results
                for future in batch_futures:
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error processing item: {e}")
                        results.append(None)

                if show_progress:
                    current_batch = i // self.batch_size + 1
                    print(f"Processed batch {current_batch}/{total_batches}", end="\r")

        if show_progress:
            print()  # New line after progress

        return results


# Numba-optimized functions for performance-critical operations

@numba.jit(nopython=True, parallel=True)
def calculate_triangle_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Calculate triangle normals using Numba optimization.

    Args:
        vertices: Vertex array (N, 3)
        faces: Face indices array (M, 3)

    Returns:
        Normal vectors array (M, 3)
    """
    num_faces = faces.shape[0]
    normals = np.zeros((num_faces, 3), dtype=np.float64)

    for i in numba.prange(num_faces):
        v0 = vertices[faces[i, 0]]
        v1 = vertices[faces[i, 1]]
        v2 = vertices[faces[i, 2]]

        # Calculate normal
        edge1 = v1 - v0
        edge2 = v2 - v0

        # Cross product
        normal = np.zeros(3, dtype=np.float64)
        normal[0] = edge1[1] * edge2[2] - edge1[2] * edge2[1]
        normal[1] = edge1[2] * edge2[0] - edge1[0] * edge2[2]
        normal[2] = edge1[0] * edge2[1] - edge1[1] * edge2[0]

        # Normalize
        length = np.sqrt(normal[0]**2 + normal[1]**2 + normal[2]**2)
        if length > 1e-10:
            normals[i] = normal / length
        else:
            normals[i] = normal

    return normals


@numba.jit(nopython=True, parallel=True)
def calculate_edge_lengths(vertices: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Calculate edge lengths using Numba optimization.

    Args:
        vertices: Vertex array (N, 3)
        edges: Edge indices array (M, 2)

    Returns:
        Edge lengths array (M,)
    """
    num_edges = edges.shape[0]
    lengths = np.zeros(num_edges, dtype=np.float64)

    for i in numba.prange(num_edges):
        v0 = vertices[edges[i, 0]]
        v1 = vertices[edges[i, 1]]
        diff = v1 - v0
        lengths[i] = np.sqrt(diff[0]**2 + diff[1]**2 + diff[2]**2)

    return lengths


@numba.jit(nopython=True)
def find_degenerate_faces(vertices: np.ndarray, faces: np.ndarray, tolerance: float = 1e-10) -> np.ndarray:
    """Find degenerate (zero-area) faces.

    Args:
        vertices: Vertex array (N, 3)
        faces: Face indices array (M, 3)
        tolerance: Area tolerance

    Returns:
        Boolean array indicating degenerate faces
    """
    num_faces = faces.shape[0]
    degenerate = np.zeros(num_faces, dtype=np.bool_)

    for i in range(num_faces):
        v0 = vertices[faces[i, 0]]
        v1 = vertices[faces[i, 1]]
        v2 = vertices[faces[i, 2]]

        # Calculate area using cross product
        edge1 = v1 - v0
        edge2 = v2 - v0

        cross = np.zeros(3, dtype=np.float64)
        cross[0] = edge1[1] * edge2[2] - edge1[2] * edge2[1]
        cross[1] = edge1[2] * edge2[0] - edge1[0] * edge2[2]
        cross[2] = edge1[0] * edge2[1] - edge1[1] * edge2[0]

        area = 0.5 * np.sqrt(cross[0]**2 + cross[1]**2 + cross[2]**2)
        degenerate[i] = area < tolerance

    return degenerate


def get_performance_summary() -> Dict[str, Any]:
    """Get global performance summary.

    Returns:
        Dictionary with performance statistics
    """
    return _monitor.get_summary()


def clear_performance_data() -> None:
    """Clear global performance data."""
    _monitor.clear()