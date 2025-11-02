"""Optimized parallel processing for 3D mesh operations with enhanced error handling."""

import gc
import os
import signal
import time
import traceback
import multiprocessing
import psutil
import threading
import resource
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from tqdm import tqdm

class MemoryMonitor(threading.Thread):
    """Monitor memory usage in a separate thread."""
    
    def __init__(self, interval: float = 1.0):
        super().__init__(daemon=True)
        self.interval = interval
        self.peak_usage = 0.0
        self._stop_event = threading.Event()
        
    def run(self):
        """Monitor memory usage until stopped."""
        while not self._stop_event.is_set():
            self.peak_usage = max(
                self.peak_usage,
                psutil.Process().memory_percent() / 100.0  # Normalize to 0.0-1.0 range
            )
            time.sleep(self.interval)
            
    def stop(self):
        """Stop the memory monitoring thread."""
        self._stop_event.set()


def init_worker():
    """Initialize worker process with proper signal handling and resource limits."""
    # Reset signal handlers (for Ctrl+C handling)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    # Set memory limits (in bytes)
    if hasattr(resource, 'RLIMIT_AS'):
        resource.setrlimit(
            resource.RLIMIT_AS,
            (4 * 1024 * 1024 * 1024, 8 * 1024 * 1024 * 1024)  # 4GB soft, 8GB hard
        )
    """Raised when a worker process is terminated unexpectedly."""
    pass

class BatchProcessingError(Exception):
    """Raised when a batch of items fails to process."""
    def __init__(self, message: str, failed_items: List[Any] = None):
        self.failed_items = failed_items or []
        super().__init__(message)

# Type variables for generic type hints
T = TypeVar('T')  # Input item type
R = TypeVar('R')  # Result type

# Global flag for worker process initialization
_worker_initialized = False

# Constants for resource management
DEFAULT_CHECK_INTERVAL = 0.1  # seconds
MAX_MEMORY_LEAK_RETRIES = 3
MEMORY_LEAK_THRESHOLD = 1.5  # 50% increase in memory usage

class ProcessState(Enum):
    IDLE = auto()
    BUSY = auto()
    SUSPECT = auto()
    TERMINATED = auto()

class ResourceType(Enum):
    CPU = "CPU"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"

# Type variables for generic type hints
T = TypeVar('T')  # Input item type
R = TypeVar('R')  # Result type

# Global flag for worker process initialization
_worker_initialized = False



@dataclass
class ResourceStats:
    """Container for detailed system resource statistics."""
    timestamp: float = field(default_factory=time.time)
    # CPU metrics
    cpu_percent: float = 0.0
    cpu_count: int = os.cpu_count() or 1
    cpu_load_avg: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    
    # Memory metrics
    memory_percent: float = 0.0
    memory_used_gb: float = 0.0
    memory_available_gb: float = 0.0
    memory_total_gb: float = 0.0
    
    # Process-specific metrics
    process_memory_mb: float = 0.0
    process_threads: int = 0
    process_fds: Optional[int] = None
    
    # System-wide metrics
    swap_percent: float = 0.0
    swap_used_gb: float = 0.0
    swap_total_gb: float = 0.0
    
    # I/O metrics
    io_read_bytes: int = 0
    io_write_bytes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp,
            'cpu': {
                'percent': self.cpu_percent,
                'count': self.cpu_count,
                'load_avg': self.cpu_load_avg
            },
            'memory': {
                'percent': self.memory_percent,
                'used_gb': self.memory_used_gb,
                'available_gb': self.memory_available_gb,
                'total_gb': self.memory_total_gb
            },
            'process': {
                'memory_mb': self.process_memory_mb,
                'threads': self.process_threads,
                'file_descriptors': self.process_fds
            },
            'swap': {
                'percent': self.swap_percent,
                'used_gb': self.swap_used_gb,
                'total_gb': self.swap_total_gb
            },
            'io': {
                'read_bytes': self.io_read_bytes,
                'write_bytes': self.io_write_bytes
            }
        }


class ResourceMonitor(threading.Thread):
    """Advanced system resource monitor with historical tracking and analysis.
    
    Features:
    - Real-time CPU, memory, disk, and network monitoring
    - Historical data with configurable retention
    - Leak detection and trend analysis
    - Resource usage prediction
    """
    
    def __init__(self, interval: float = 1.0, max_history: int = 3600):
        """Initialize the resource monitor.
        
        Args:
            interval: Monitoring interval in seconds
            max_history: Maximum number of historical samples to keep
        """
        super().__init__(daemon=True)
        self.interval = max(0.1, float(interval))  # Minimum 100ms interval
        self.max_history = max(100, int(max_history))  # Keep at least 100 samples
        
        # Thread control
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        
        # Process tracking
        self.process = psutil.Process()
        self._process_creation_time = time.time()
        
        # I/O tracking
        self.io_counters = self._get_io_counters()
        self._last_io_time = time.time()
        
        # Historical data with thread-safe access
        self.history: List[ResourceStats] = []
        
        # Performance metrics
        self.metrics = {
            'cpu_avg': 0.0,
            'memory_avg': 0.0,
            'io_read_mb_sec': 0.0,
            'io_write_mb_sec': 0.0,
            'leak_suspected': False,
            'last_leak_check': 0.0,
            'leak_check_interval': 300.0  # 5 minutes between leak checks
        }
        
    def _calculate_cpu_percent(self, last_cpu_times, current_cpu_times) -> float:
        """Calculate CPU usage percentage between two measurements.
        
        Args:
            last_cpu_times: Previous CPU times from psutil.Process.cpu_times()
            current_cpu_times: Current CPU times from psutil.Process.cpu_times()
            
        Returns:
            CPU usage as a percentage (0-100)
        """
        try:
            # Calculate delta CPU time
            delta_proc = (
                (current_cpu_times.user - last_cpu_times.user) +
                (current_cpu_times.system - last_cpu_times.system)
            )
            
            # Calculate total CPU time
            total_time = sum(current_cpu_times) - sum(last_cpu_times)
            
            # Calculate percentage (avoid division by zero)
            if total_time > 0:
                return min(100.0, max(0.0, (delta_proc / total_time) * 100.0))
        except (AttributeError, TypeError):
            pass
        return 0.0

    def _check_for_memory_leak(self) -> bool:
        """Check for potential memory leaks by analyzing memory usage patterns.
        
        Returns:
            bool: True if a memory leak is suspected, False otherwise
        """
        if len(self.history) < 10:  # Need at least 10 samples
            return False
            
        try:
            # Get memory usage history (last 100 samples or all if fewer)
            samples = min(100, len(self.history))
            mem_history = [h.memory_used_gb for h in self.history[-samples:]]
            
            # Calculate memory growth rate using linear regression
            x = np.arange(len(mem_history))
            y = np.array(mem_history)
            
            # Skip if not enough variation
            if np.ptp(y) < 0.1:  # Less than 100MB variation
                return False
                
            # Calculate linear regression
            slope, _, r_value, _, _ = linregress(x, y)
            
            # Calculate memory growth in MB per hour
            samples_per_hour = 3600 / self.interval
            growth_rate_mb_per_hour = slope * samples_per_hour * 1024  # Convert GB to MB
            
            # Consider it a leak if:
            # 1. Positive slope (memory is growing)
            # 2. Good fit (r_value > 0.7)
            # 3. Growth rate > 50MB/hour
            is_leak = (
                slope > 0 and 
                abs(r_value) > 0.7 and 
                growth_rate_mb_per_hour > 50
            )
            
            if is_leak and self.verbose:
                self.logger.warning(
                    f"Potential memory leak detected: "
                    f"growth={growth_rate_mb_per_hour:.1f}MB/hour, "
                    f"r_value={r_value:.3f}"
                )
                
            return is_leak
            
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"Error checking for memory leak: {e}")
            return False

    def _get_io_counters(self) -> Optional[Any]:
        """Get initial I/O counters if available."""
        try:
            return self.process.io_counters()
        except (AttributeError, NotImplementedError):
            return None
    
    def run(self) -> None:
        """Main monitoring loop with enhanced resource tracking and leak detection."""
        last_cpu_times = self.process.cpu_times()
        last_io_time = time.time()
        
        while not self._stop_event.is_set():
            try:
                start_time = time.monotonic()
                
                # Collect system-wide stats
                stats = self._collect_stats()
                
                # Calculate CPU usage since last check
                current_cpu_times = self.process.cpu_times()
                cpu_percent = self._calculate_cpu_percent(last_cpu_times, current_cpu_times)
                last_cpu_times = current_cpu_times
                
                # Calculate I/O rates
                current_time = time.time()
                time_diff = current_time - last_io_time
                if time_diff > 0 and self.io_counters:
                    try:
                        new_io = self.process.io_counters()
                        read_mb = (new_io.read_bytes - self.io_counters.read_bytes) / (1024 * 1024)
                        write_mb = (new_io.write_bytes - self.io_counters.write_bytes) / (1024 * 1024)
                        self.io_counters = new_io
                        
                        with self._lock:
                            self.metrics['io_read_mb_sec'] = read_mb / time_diff
                            self.metrics['io_write_mb_sec'] = write_mb / time_diff
                    except (AttributeError, NotImplementedError):
                        pass
                
                last_io_time = current_time
                
                # Update metrics
                with self._lock:
                    # Update running averages
                    alpha = 0.1  # Smoothing factor
                    self.metrics['cpu_avg'] = (
                        alpha * cpu_percent + 
                        (1 - alpha) * self.metrics['cpu_avg']
                    )
                    self.metrics['memory_avg'] = (
                        alpha * stats.memory_percent + 
                        (1 - alpha) * self.metrics['memory_avg']
                    )
                    
                    # Store history
                    self.history.append(stats)
                    
                    # Check for memory leaks periodically
                    current_time = time.time()
                    if current_time - self.metrics['last_leak_check'] > self.metrics['leak_check_interval']:
                        self.metrics['leak_suspected'] = self._check_for_memory_leak()
                        self.metrics['last_leak_check'] = current_time
                    
                    # Keep history size bounded
                    if len(self.history) > self.max_history:
                        self.history = self.history[-self.max_history:]
                
                # Calculate sleep time to maintain consistent interval
                elapsed = time.monotonic() - start_time
                sleep_time = max(0, self.interval - elapsed)
                
                # Sleep in small increments to be responsive to stop events
                while sleep_time > 0 and not self._stop_event.is_set():
                    time.sleep(min(0.1, sleep_time))
                    sleep_time -= 0.1
                    
            except Exception as e:
                # Log errors but don't crash the monitor
                sys.stderr.write(f"Error in resource monitor: {e}\n")
                time.sleep(1)  # Prevent tight loop on error
                
    def _collect_stats(self) -> ResourceStats:
        """Collect current system and process statistics."""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        io = self._get_io_counters()
        
        stats = ResourceStats(
            cpu_percent=psutil.cpu_percent(interval=None),
            cpu_load_avg=os.getloadavg() if hasattr(os, 'getloadavg') else (0.0, 0.0, 0.0),
            
            memory_percent=mem.percent,
            memory_used_gb=mem.used / (1024 ** 3),
            memory_available_gb=mem.available / (1024 ** 3),
            memory_total_gb=mem.total / (1024 ** 3),
            
            process_memory_mb=self.process.memory_info().rss / (1024 ** 2),
            process_threads=self.process.num_threads(),
            process_fds=self._get_num_fds(),
            
            swap_percent=swap.percent,
            swap_used_gb=swap.used / (1024 ** 3),
            swap_total_gb=swap.total / (1024 ** 3) if swap.total else 0.0,
            
            io_read_bytes=io.read_bytes if io else 0,
            io_write_bytes=io.write_bytes if io else 0
        )
        
        # Update I/O counters for next iteration
        if io:
            self.io_counters = io
            
        return stats
    
    def _get_num_fds(self) -> Optional[int]:
        """Get number of open file descriptors if available."""
        try:
            if sys.platform == 'win32':
                import ctypes
                from ctypes.wintypes import DWORD, HANDLE
                
                GetProcessHandleCount = ctypes.windll.kernel32.GetProcessHandleCount
                GetProcessHandleCount.argtypes = [HANDLE, POINTER(DWORD)]
                
                count = DWORD()
                if GetProcessHandleCount(self.process._handle, byref(count)):
                    return count.value
            else:
                return len(os.listdir(f'/proc/{self.process.pid}/fd'))
        except (OSError, AttributeError):
            pass
        return None
    
    def get_recent_stats(self, seconds: int = 60) -> List[ResourceStats]:
        """Get resource statistics for the last N seconds."""
        cutoff = time.time() - seconds
        with self._lock:
            return [s for s in self.history if s.timestamp >= cutoff]
    
    def get_peak_memory_usage(self) -> float:
        """Get peak memory usage as a percentage."""
        with self._lock:
            if not self.history:
                return 0.0
            return max(s.memory_percent / 100.0 for s in self.history)
    
    def get_cpu_usage_stats(self) -> Dict[str, float]:
        """Get CPU usage statistics."""
        with self._lock:
            if not self.history:
                return {'avg': 0.0, 'max': 0.0, 'current': 0.0}
                
            current = self.history[-1].cpu_percent
            max_cpu = max(s.cpu_percent for s in self.history)
            avg_cpu = sum(s.cpu_percent for s in self.history) / len(self.history)
            
            return {
                'current': current,
                'max': max_cpu,
                'avg': avg_cpu
            }
    
    def stop(self) -> None:
        """Stop the monitoring thread."""
        self._stop_event.set()
        self.join(timeout=2.0)


def init_worker(process_name: Optional[str] = None) -> None:
    """Initialize worker process with proper resource limits and signal handling.
    
    Args:
        process_name: Optional name to identify this worker in logs
    """
    global _worker_initialized
    
    if _worker_initialized:
        return
    
    # Set process name if provided
    if process_name and hasattr(psutil.Process(), 'name'):
        try:
            import setproctitle
            setproctitle.setproctitle(f"{process_name} worker")
        except (ImportError, AttributeError):
            pass  # setproctitle not available, continue without it
    
    # Reset signal handlers (for Ctrl+C handling)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    # Configure process priority and CPU affinity
    try:
        current_process = psutil.Process()
        
        # Set process priority
        if sys.platform == 'win32':
            import win32api, win32process, win32con
            handle = win32api.GetCurrentProcess()
            win32process.SetPriorityClass(handle, win32process.BELOW_NORMAL_PRIORITY_CLASS)
            
            # Try to set CPU affinity to use only some cores
            try:
                available_cores = list(range(os.cpu_count() or 1))
                # Use only half the cores, but at least 1
                num_cores = max(1, len(available_cores) // 2)
                current_process.cpu_affinity(available_cores[:num_cores])
            except (AttributeError, psutil.AccessDenied):
                pass
        else:
            # On Unix-like systems
            os.nice(5)  # Lower priority
            
            # Try to set CPU affinity
            try:
                import os
                os.sched_setaffinity(0, range(max(1, os.cpu_count() // 2)))
            except (AttributeError, OSError):
                pass
    except Exception as e:
        sys.stderr.write(f"Warning: Could not set process priority/affinity: {e}\n")
    
    # Set resource limits
    try:
        # Memory limits
        if hasattr(resource, 'RLIMIT_AS'):
            total_mem = psutil.virtual_memory().total
            
            # Calculate limits based on available memory
            soft_limit = min(4 * 1024**3, int(total_mem * 0.8))  # 80% of total or 4GB
            hard_limit = min(8 * 1024**3, int(total_mem * 0.9))  # 90% of total or 8GB
            
            resource.setrlimit(resource.RLIMIT_AS, (soft_limit, hard_limit))
            
        # File descriptor limits
        if hasattr(resource, 'RLIMIT_NOFILE'):
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            # Try to increase soft limit up to hard limit
            if soft < hard:
                resource.setrlimit(resource.RLIMIT_NOFILE, (min(4096, hard), hard))
                
    except (ValueError, resource.error) as e:
        sys.stderr.write(f"Warning: Could not set resource limits: {e}\n")
    
    # Configure Python's garbage collector
    gc.enable()
    # Disable debug flags to speed up garbage collection
    gc.set_debug(0)
    # Run garbage collection more frequently but with lower threshold
    gc.set_threshold(700, 10, 10)
    
    # Configure Python's memory allocator
    try:
        if hasattr(sys, 'getallocatedblocks'):
            # Enable malloc trimming if available
            try:
                import ctypes
                libc = ctypes.CDLL(None)
                libc.malloc_trim(0)
            except (OSError, AttributeError):
                pass
    except Exception as e:
        sys.stderr.write(f"Warning: Could not configure memory allocator: {e}\n")
    
    _worker_initialized = True


class ProcessManager:
    """Manages worker processes with advanced features like health checks and auto-scaling."""
    
    def __init__(
        self,
        target: Callable[..., Any],
        args: Optional[Tuple[Any, ...]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        num_workers: Optional[int] = None,
        max_restarts: int = 3,
        health_check_interval: float = 30.0,
        logger: Optional[Any] = None
    ):
        """Initialize the process manager.
        
        Args:
            target: Target function for worker processes
            args: Positional arguments for the target function
            kwargs: Keyword arguments for the target function
            num_workers: Number of worker processes (default: CPU count)
            max_restarts: Maximum number of times to restart failed workers
            health_check_interval: Interval between health checks in seconds
            logger: Logger instance for process management events
        """
        self.target = target
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.num_workers = num_workers or os.cpu_count() or 1
        self.max_restarts = max_restarts
        self.health_check_interval = health_check_interval
        self.logger = logger or logging.getLogger(__name__)
        
        self._processes: List[Tuple[multiprocessing.Process, int]] = []  # (process, restart_count)
        self._shutdown_event = multiprocessing.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Statistics
        self.start_time = time.monotonic()
        self.worker_starts = 0
        self.worker_restarts = 0
        self.worker_failures = 0
    
    def start(self) -> None:
        """Start the worker processes and monitoring thread."""
        if self._monitor_thread is not None:
            self.logger.warning("Process manager already started")
            return
            
        self._shutdown_event.clear()
        
        # Start worker processes
        for _ in range(self.num_workers):
            self._start_worker()
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_workers,
            daemon=True,
            name="ProcessMonitor"
        )
        self._monitor_thread.start()
        
        self.logger.info(
            f"Started process manager with {self.num_workers} workers "
            f"(max_restarts={self.max_restarts})"
        )
    
    def stop(self, timeout: float = 5.0) -> None:
        """Stop all worker processes and monitoring thread.
        
        Args:
            timeout: Maximum time to wait for processes to terminate
        """
        if self._monitor_thread is None:
            return
            
        self.logger.info("Stopping process manager...")
        self._shutdown_event.set()
        
        # Signal all workers to terminate
        with self._lock:
            for process, _ in self._processes:
                try:
                    if process.is_alive():
                        process.terminate()
                except Exception as e:
                    self.logger.error(f"Error terminating worker {process.pid}: {e}")
        
        # Wait for monitoring thread to finish
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=timeout)
            if self._monitor_thread.is_alive():
                self.logger.warning("Monitoring thread did not stop gracefully")
            self._monitor_thread = None
        
        # Force kill any remaining processes
        self._kill_all_workers()
        self._processes.clear()
        
        self.logger.info("Process manager stopped")
    
    def _start_worker(self) -> None:
        """Start a single worker process."""
        process = multiprocessing.Process(
            target=self._worker_wrapper,
            args=self.args,
            kwargs={"worker_id": f"worker-{self.worker_starts}", **self.kwargs},
            daemon=True
        )
        
        with self._lock:
            self._processes.append((process, 0))
            self.worker_starts += 1
        
        process.start()
        self.logger.debug(f"Started worker {process.pid}")
    
    def _worker_wrapper(self, *args: Any, worker_id: str = "", **kwargs: Any) -> None:
        """Wrapper function for worker processes."""
        # Set process name if available
        if worker_id and hasattr(psutil.Process(), 'name'):
            try:
                import setproctitle
                setproctitle.setproctitle(f"{worker_id} worker")
            except (ImportError, AttributeError):
                pass
        
        # Initialize worker
        init_worker(worker_id)
        
        try:
            # Call the target function
            self.target(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"Worker {worker_id} failed: {e}", exc_info=True)
            raise
    
    def _monitor_workers(self) -> None:
        """Monitor worker processes and restart failed ones."""
        while not self._shutdown_event.is_set():
            try:
                self._check_workers()
            except Exception as e:
                self.logger.error(f"Error in worker monitor: {e}", exc_info=True)
            
            # Wait for next check
            self._shutdown_event.wait(self.health_check_interval)
    
    def _check_workers(self) -> None:
        """Check worker processes and restart failed ones."""
        with self._lock:
            current_time = time.monotonic()
            new_processes = []
            
            for process, restart_count in self._processes:
                if not process.is_alive():
                    self.worker_failures += 1
                    
                    # Check if we should restart the worker
                    if restart_count < self.max_restarts:
                        self.logger.warning(
                            f"Worker {process.pid} died with exit code {process.exitcode}, "
                            f"restarting ({restart_count + 1}/{self.max_restarts})"
                        )
                        
                        # Start a new worker
                        new_process = multiprocessing.Process(
                            target=self._worker_wrapper,
                            args=self.args,
                            kwargs={
                                "worker_id": f"worker-replace-{process.pid}",
                                **self.kwargs
                            },
                            daemon=True
                        )
                        new_process.start()
                        new_processes.append((new_process, restart_count + 1))
                        self.worker_restarts += 1
                        self.logger.info(f"Restarted worker {process.pid} as {new_process.pid}")
                    else:
                        self.logger.error(
                            f"Worker {process.pid} failed too many times "
                            f"({restart_count} restarts), not restarting"
                        )
                else:
                    # Worker is still running, keep it
                    new_processes.append((process, restart_count))
            
            # Replace the process list
            self._processes = new_processes
            
            # Log statistics periodically
            if current_time - getattr(self, '_last_stats_log', 0) > 300:  # Every 5 minutes
                self._log_statistics()
                self._last_stats_log = current_time
    
    def _kill_all_workers(self) -> None:
        """Force kill all worker processes."""
        with self._lock:
            for process, _ in self._processes:
                try:
                    if process.is_alive():
                        process.kill()
                except Exception as e:
                    self.logger.error(f"Error killing worker {process.pid}: {e}")
    
    def _log_statistics(self) -> None:
        """Log process manager statistics."""
        uptime = time.monotonic() - self.start_time
        uptime_str = str(datetime.timedelta(seconds=int(uptime)))
        
        stats = {
            "uptime": uptime_str,
            "active_workers": len([p for p, _ in self._processes if p.is_alive()]),
            "total_workers_started": self.worker_starts,
            "worker_restarts": self.worker_restarts,
            "worker_failures": self.worker_failures,
            "avg_uptime_per_worker": f"{uptime / max(1, self.worker_starts):.1f}s"
        }
        
        self.logger.info("Process manager statistics: " + 
                        "; ".join(f"{k}={v}" for k, v in stats.items()))
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class ProcessResult(Generic[T]):
    """Container for process results with metadata."""
    
    def __init__(
        self,
        item: T,
        success: bool = False,
        result: Any = None,
        error: Optional[str] = None,
        attempt: int = 0,
        duration: float = 0.0,
        memory_used_mb: float = 0.0
    ):
        self.item = item
        self.success = success
        self.result = result
        self.error = error
        self.attempt = attempt
        self.duration = duration
        self.memory_used_mb = memory_used_mb
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'item': str(self.item),
            'success': self.success,
            'result': self.result,
            'error': self.error,
            'attempt': self.attempt,
            'duration': self.duration,
            'memory_used_mb': self.memory_used_mb,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessResult':
        """Create from dictionary."""
        return cls(
            item=data.get('item'),
            success=data.get('success', False),
            result=data.get('result'),
            error=data.get('error'),
            attempt=data.get('attempt', 0),
            duration=data.get('duration', 0.0),
            memory_used_mb=data.get('memory_used_mb', 0.0)
        )


class ParallelProcessor(Generic[T, R]):
    """Optimized parallel processing for compute-intensive tasks with advanced features.
    
    This class provides a robust framework for parallel processing with:
    - Automatic resource management and monitoring
    - Configurable retry mechanisms with exponential backoff
    - Memory and CPU usage tracking
    - Dynamic batch sizing
    - Process isolation and error recovery
    - Detailed progress tracking and statistics
    """
    
    def __init__(
        self, 
        logger: Any,
        verbose: bool = False,
        max_workers: Optional[int] = None,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 30.0,
        memory_limit_ratio: float = 0.8,
        max_memory_gb: Optional[float] = None,
        cpu_affinity: bool = True,
        process_timeout: Optional[float] = None,
        result_callback: Optional[Callable[[ProcessResult[R]], None]] = None,
        error_callback: Optional[Callable[[Exception, T, int], None]] = None,
        enable_metrics: bool = True,
        auto_adjust_batch: bool = True,
        min_batch_size: int = 1,
        max_batch_size: int = 1000,
        leak_detection_threshold: int = 100
    ):
        """Initialize the parallel processor with advanced configuration options.
        
        Args:
            logger: Logger instance for logging messages
            verbose: Enable verbose logging of processing details
            max_workers: Maximum number of worker processes (None for auto-detect)
            max_retries: Maximum number of retry attempts for failed items
            initial_backoff: Initial backoff time in seconds for retries
            max_backoff: Maximum backoff time in seconds
            memory_limit_ratio: Maximum memory usage ratio (0.5-0.95) before throttling
            max_memory_gb: Optional absolute memory limit in GB for the entire processor
            cpu_affinity: Whether to set CPU affinity for workers
            process_timeout: Maximum time in seconds for a single process to run
            result_callback: Optional callback for processing each result
            error_callback: Optional callback for handling processing errors
            enable_metrics: Whether to collect and report performance metrics
            auto_adjust_batch: Whether to automatically adjust batch sizes
            min_batch_size: Minimum batch size when auto-adjusting
            max_batch_size: Maximum batch size when auto-adjusting
            leak_detection_threshold: Number of batches after which to check for memory leaks
            
        Raises:
            ValueError: If invalid parameters are provided
        """
        # Input validation
        if memory_limit_ratio < 0.5 or memory_limit_ratio > 0.95:
            raise ValueError("memory_limit_ratio must be between 0.5 and 0.95")
        if min_batch_size < 1:
            raise ValueError("min_batch_size must be at least 1")
        if max_batch_size < min_batch_size:
            raise ValueError("max_batch_size must be >= min_batch_size")
            
        self.logger = logger
        self.verbose = verbose
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.memory_limit_ratio = memory_limit_ratio
        self.max_memory_gb = max_memory_gb
        self.cpu_affinity = cpu_affinity
        self.process_timeout = process_timeout
        self.result_callback = result_callback
        self.error_callback = error_callback
        self.enable_metrics = enable_metrics
        self.auto_adjust_batch = auto_adjust_batch
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.leak_detection_threshold = leak_detection_threshold
        
        # Initialize resource tracking
        self._resource_monitor = ResourceMonitor(interval=0.5)
        self._start_time = time.monotonic()
        self._processed_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._retry_count = 0
        self._total_processing_time = 0.0
        self._batch_counter = 0
        self._last_memory_check = 0
        self._consecutive_memory_high = 0
        self._current_batch_size = min_batch_size
        self._batch_size_history = []
        self._memory_history = []
        
        # Performance metrics
        self.metrics = {
            'start_time': self._start_time,
            'end_time': None,
            'items_processed': 0,
            'items_succeeded': 0,
            'items_failed': 0,
            'total_retries': 0,
            'avg_processing_time': 0.0,
            'peak_memory_mb': 0.0,
            'cpu_usage_avg': 0.0,
            'batch_size_stats': {
                'min': float('inf'),
                'max': 0,
                'avg': 0,
                'last': 0
            },
            'memory_leak_detected': False,
            'circuit_breaker': {
                'tripped': False,
                'trip_count': 0,
                'last_tripped': None
            }
        }
        
    @classmethod
    def calculate_resource_limits(cls) -> Dict[str, Any]:
        """Calculate system resource limits and optimal configuration.
        
        Returns:
            Dictionary containing:
            - cpu_count: Number of available CPU cores
            - total_memory_gb: Total system memory in GB
            - available_memory_gb: Currently available memory in GB
            - max_workers: Recommended maximum number of worker processes
            - memory_per_worker_gb: Recommended memory per worker in GB
        """
        try:
            # Get CPU information
            cpu_count = os.cpu_count() or 1
            
            # Get memory information
            mem = psutil.virtual_memory()
            total_memory_gb = mem.total / (1024 ** 3)
            available_memory_gb = mem.available / (1024 ** 3)
            
            # Calculate recommended max workers
            max_workers = min(
                cpu_count * 2,  # Up to 2x CPU count
                max(1, int(available_memory_gb * 0.8 / 2))  # 80% of available memory, min 2GB per worker
            )
            
            # Ensure at least 1 worker
            max_workers = max(1, max_workers)
            
            # Calculate memory per worker
            memory_per_worker_gb = max(0.5, min(4.0, available_memory_gb / max_workers * 0.8))
            
            return {
                'cpu_count': cpu_count,
                'total_memory_gb': round(total_memory_gb, 2),
                'available_memory_gb': round(available_memory_gb, 2),
                'max_workers': max_workers,
                'memory_per_worker_gb': round(memory_per_worker_gb, 2)
            }
            
        except Exception as e:
            # Fallback to conservative defaults
            return {
                'cpu_count': 1,
                'total_memory_gb': 4.0,
                'available_memory_gb': 2.0,
                'max_workers': 1,
                'memory_per_worker_gb': 1.0
            }
    
    def _calculate_optimal_batch_size(self, items: List[T]) -> int:
        """Calculate optimal batch size based on system resources, item count, and historical performance.
        
        This method considers multiple factors:
        - Available system memory
        - CPU load and core count
        - Historical performance
        - Item size estimation
        - Current system load
        
        Args:
            items: List of items to process
            
        Returns:
            Optimal batch size considering current system state and history
        """
        if not items:
            return 0
            
        try:
            # Get system resources
            resources = self.calculate_resource_limits()
            
            # Estimate item size (using a more sophisticated approach)
            avg_item_size = self._estimate_item_size(items)
            
            # Get current system state
            mem = psutil.virtual_memory()
            available_mem_gb = mem.available / (1024 ** 3)
            used_mem_ratio = mem.percent / 100.0
            
            # Get CPU load (weighted average over different time periods)
            cpu_load = self._get_weighted_cpu_load()
            
            # Calculate memory-based batch size
            memory_batch = self._calculate_memory_based_batch(
                available_mem_gb, used_mem_ratio, avg_item_size
            )
            
            # Calculate CPU-based batch size
            cpu_batch = self._calculate_cpu_based_batch(cpu_load, resources['cpu_count'])
            
            # Calculate final batch size with adaptive strategy
            batch_size = self._calculate_adaptive_batch(
                memory_batch, 
                cpu_batch,
                len(items)
            )
            
            # Store for future reference and learning
            self._update_batch_history(batch_size)
            
            if self.verbose:
                self._log_batch_decision(
                    batch_size, len(items), avg_item_size, 
                    available_mem_gb, cpu_load, memory_batch, cpu_batch
                )
                
            return batch_size
            
        except Exception as e:
            self.logger.warning(f"Error calculating batch size: {e}, using default")
            return min(self.min_batch_size, len(items))
    
    def _estimate_item_size(self, items: List[T]) -> float:
        """Estimate the average size of items in MB."""
        if not items:
            return 1.0  # Default size if no items
            
        try:
            # Sample up to 10 items for estimation
            sample_size = min(10, len(items))
            sample = random.sample(items, sample_size)
            
            total_size = 0
            count = 0
            
            for item in sample:
                try:
                    # Try to get size directly
                    if hasattr(item, '__getsizeof__'):
                        size = sys.getsizeof(item)
                    # Handle common data structures
                    elif isinstance(item, (list, tuple, set, dict)):
                        size = sum(sys.getsizeof(i) for i in item) + sys.getsizeof(item)
                    else:
                        # Fallback to string representation size
                        size = len(str(item).encode('utf-8'))
                    
                    total_size += size
                    count += 1
                except Exception:
                    continue
            
            # Return average size in MB, with minimum of 1KB
            return max(0.001, (total_size / max(1, count)) / (1024 ** 2))
            
        except Exception:
            return 1.0  # Fallback to 1MB if estimation fails
    
    def _get_weighted_cpu_load(self) -> float:
        """Get weighted CPU load (recent load has more weight)."""
        try:
            # Get load averages (1, 5, 15 minutes)
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0.1, 0.1, 0.1)
            
            # Weighted average (50% 1min, 30% 5min, 20% 15min)
            weighted_load = (load_avg[0] * 0.5 + load_avg[1] * 0.3 + load_avg[2] * 0.2)
            
            # Normalize by number of CPUs
            cpu_count = os.cpu_count() or 1
            normalized_load = min(1.0, weighted_load / cpu_count)
            
            return normalized_load
            
        except Exception:
            return 0.5  # Default to 50% if we can't determine load
    
    def _calculate_memory_based_batch(
        self, 
        available_mem_gb: float, 
        used_mem_ratio: float, 
        avg_item_size_mb: float
    ) -> int:
        """Calculate batch size based on available memory and item size."""
        # Adjust for memory pressure (more aggressive backoff as memory fills)
        memory_factor = 1.0 - (used_mem_ratio ** 2)  # Quadratic backoff
        memory_factor = max(0.1, min(1.0, memory_factor))  # Keep in [0.1, 1.0]
        
        # Calculate maximum items that fit in available memory
        safety_margin = 1.5  # 50% safety margin
        max_items = int((available_mem_gb * 1024 * memory_factor) / 
                       ((avg_item_size_mb + 0.1) * safety_margin))
        
        return max(1, max_items)
    
    def _calculate_cpu_based_batch(self, cpu_load: float, cpu_count: int) -> int:
        """Calculate batch size based on CPU load and core count."""
        # Scale batch size based on CPU load (inverse relationship)
        # At 0% load: use 2x CPU count
        # At 100% load: use 0.5x CPU count
        cpu_factor = 2.0 - (1.5 * cpu_load)
        
        # Calculate base batch size
        batch_size = max(1, int(cpu_count * cpu_factor))
        
        return batch_size
    
    def _calculate_adaptive_batch(
        self, 
        memory_batch: int, 
        cpu_batch: int,
        total_items: int
    ) -> int:
        """Calculate final batch size using adaptive strategy."""
        # Start with the more restrictive of memory or CPU-based batch size
        batch_size = min(memory_batch, cpu_batch)
        
        # Apply historical learning if available
        if self._batch_size_history:
            # Use exponential moving average of last 5 successful batch sizes
            last_batches = self._batch_size_history[-5:]
            hist_avg = sum(last_batches) / len(last_batches)
            
            # Weighted average: 60% historical, 40% current calculation
            batch_size = int(0.6 * hist_avg + 0.4 * batch_size)
        
        # Apply configured bounds
        batch_size = max(
            self.min_batch_size, 
            min(batch_size, self.max_batch_size, total_items)
        )
        
        return batch_size
    
    def _update_batch_history(self, batch_size: int) -> None:
        """Update batch size history for learning."""
        self._batch_size_history.append(batch_size)
        
        # Keep history size bounded (last 20 batches)
        if len(self._batch_size_history) > 20:
            self._batch_size_history.pop(0)
    
    def _log_batch_decision(
        self,
        batch_size: int,
        total_items: int,
        avg_item_size: float,
        available_mem_gb: float,
        cpu_load: float,
        memory_batch: int,
        cpu_batch: int
    ) -> None:
        """Log batch size decision details."""
        self.logger.debug(
            f"Batch size: {batch_size} (of {total_items} items)\n"
            f"  - Item size: {avg_item_size*1024:.1f} KB avg\n"
            f"  - Memory: {available_mem_gb:.1f} GB available\n"
            f"  - CPU load: {cpu_load*100:.1f}%\n"
            f"  - Memory-based: {memory_batch}, CPU-based: {cpu_batch}"
        )
    
    def _check_for_memory_leak(self) -> bool:
        """Check for potential memory leaks by analyzing memory usage patterns.

        Returns:
            bool: True if a memory leak is suspected, False otherwise
        """
        if len(self._memory_history) < 10:  # Need at least 10 samples
            return False

        try:
            # Calculate memory growth rate
            x = np.arange(len(self._memory_history))
            y = np.array(self._memory_history)

            # Simple linear regression to detect increasing trend
            slope, _, _, _, _ = linregress(x, y)

            # If memory is consistently increasing, we might have a leak
            leak_detected = slope > (0.1 * y.mean())  # More than 10% increase per sample

            if leak_detected and self.verbose:
                self.logger.warning(
                    f"Potential memory leak detected: memory growth rate {slope:.2f} MB/sample"
                )

            return leak_detected

        except Exception as e:
            self.logger.warning(f"Error checking for memory leaks: {e}")
            return False
    
    def _adjust_batch_size(self, success: bool, memory_used: float) -> None:
        """Dynamically adjust batch size based on success rate and memory usage.

        Args:
            success: Whether the last batch was successful
            memory_used: Memory used in the last batch (MB)
        """
        if not self.auto_adjust_batch:
            return

        # Record memory usage for leak detection
        self._memory_history.append(memory_used)
        if len(self._memory_history) > 20:  # Keep last 20 samples
            self._memory_history.pop(0)

        # Check for memory leaks periodically
        self._batch_counter += 1
        if self._batch_counter % self.leak_detection_threshold == 0:
            if self._check_for_memory_leak():
                self.metrics['memory_leak_detected'] = True
                # Reduce batch size on leak detection
                self._current_batch_size = max(
                    self.min_batch_size,
                    int(self._current_batch_size * 0.8)  # Reduce by 20%
                )
                self.logger.warning(
                    f"Reducing batch size to {self._current_batch_size} due to memory leak detection"
                )
                return

        # Adjust batch size based on success and memory usage
        mem_ratio = memory_used / (self.memory_limit_ratio * psutil.virtual_memory().total / (1024 ** 2))

        if success:
            if mem_ratio < 0.7:  # Using less than 70% of memory limit
                # Increase batch size if we're not memory constrained
                new_size = min(
                    self.max_batch_size,
                    int(self._current_batch_size * 1.2)  # Increase by 20%
                )
                if new_size > self._current_batch_size:
                    self._current_batch_size = new_size
                    if self.verbose:
                        self.logger.debug(f"Increased batch size to {self._current_batch_size}")
        else:
            if mem_ratio > 0.9:  # Using more than 90% of memory limit
                # Reduce batch size if we're memory constrained
                self._current_batch_size = max(
                    self.min_batch_size,
                    int(self._current_batch_size * 0.8)  # Reduce by 20%
                )
                if self.verbose:
                    self.logger.warning(
                        f"Reduced batch size to {self._current_batch_size} "
                        f"due to high memory usage ({mem_ratio*100:.1f}% of limit)"
                    )

        # Update metrics
        self.metrics['batch_size_stats'].update({
            'min': min(self.metrics['batch_size_stats']['min'], self._current_batch_size),
            'max': max(self.metrics['batch_size_stats']['max'], self._current_batch_size),
            'avg': (self.metrics['batch_size_stats']['avg'] * (self._batch_counter - 1) + 
                   self._current_batch_size) / self._batch_counter,
            'last': self._current_batch_size
        })
    
    def _trip_circuit_breaker(self, error: Exception) -> None:
        """Trip the circuit breaker to prevent further processing.
        
        Args:
            error: The error that caused the circuit to trip
        """
        self.metrics['circuit_breaker'].update({
            'tripped': True,
            'trip_count': self.metrics['circuit_breaker']['trip_count'] + 1,
            'last_tripped': time.time(),
            'last_error': str(error)
        })
        self.logger.error(
            f"Circuit breaker tripped due to: {error}"
            f" (trip count: {self.metrics['circuit_breaker']['trip_count']})"
        )
    
    def _is_circuit_breaker_tripped(self) -> bool:
        """Check if the circuit breaker is currently tripped.
        
        Returns:
            bool: True if the circuit breaker is tripped, False otherwise
        """
        if not self.metrics['circuit_breaker']['tripped']:
            return False
            
        # Auto-reset after 5 minutes
        last_tripped = self.metrics['circuit_breaker'].get('last_tripped')
        if last_tripped and (time.time() - last_tripped) > 300:  # 5 minutes
            self.logger.info("Circuit breaker auto-reset after 5 minutes")
            self.metrics['circuit_breaker']['tripped'] = False
            return False
            
        return True
    
    def _process_with_retry(
        self,
        item: T,
        process_func: Callable[[T, Dict[str, Any]], R],
        process_args: Dict[str, Any],
        max_retries: int,
        initial_backoff: float,
        max_backoff: float
    ) -> ProcessResult[R]:
        """Process a single item with retry logic and circuit breaker.
        
        Args:
            item: Item to process
            process_func: Function to process the item
            process_args: Additional arguments for process_func
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff time in seconds
            max_backoff: Maximum backoff time in seconds
            
        Returns:
            ProcessResult containing the result or error information
            
        Raises:
            CircuitBreakerError: If the circuit breaker is tripped
        """
        # Check circuit breaker first
        if self._is_circuit_breaker_tripped():
            raise CircuitBreakerError(
                "Processing halted: Circuit breaker is tripped. "
                "Please check system status and try again later."
            )
            
        attempt = 0
        start_time = time.monotonic()
        last_error = None
        consecutive_errors = 0
        
        while attempt <= max_retries:
            try:
                # Check memory before processing
                if self._resource_monitor.get_peak_memory_usage() > self.memory_limit_ratio:
                    # Memory is high, wait before retrying
                    wait_time = min(initial_backoff * (2 ** attempt), max_backoff)
                    if self.verbose:
                        self.logger.warning(
                            f"High memory usage detected, waiting {wait_time:.1f}s before "
                            f"processing (attempt {attempt + 1}/{max_retries + 1})"
                        )
                    time.sleep(wait_time)
                    continue
                
                # Process the item
                result = process_func(item, {**process_args, 'attempt': attempt})
                
                # Calculate processing time and memory usage
                duration = time.monotonic() - start_time
                memory_used = psutil.Process().memory_info().rss / (1024 ** 2)  # MB
                
                # Update metrics
                self._processed_count += 1
                self._success_count += 1
                self._total_processing_time += duration
                
                return ProcessResult(
                    item=item,
                    success=True,
                    result=result,
                    attempt=attempt + 1,
                    duration=duration,
                    memory_used_mb=memory_used
                )
                
            except Exception as e:
                last_error = e
                attempt += 1
                self._retry_count += 1
                self._failure_count += 1
                
                # Call error callback if provided
                if self.error_callback:
                    try:
                        self.error_callback(e, item, attempt)
                    except Exception as cb_error:
                        self.logger.error(f"Error in error callback: {cb_error}", exc_info=True)
                
                # Log the error
                error_msg = f"Error processing item (attempt {attempt}/{max_retries + 1}): {str(e)}"
                if attempt <= max_retries:
                    self.logger.warning(error_msg)
                else:
                    self.logger.error(error_msg, exc_info=self.verbose)
                
                # Calculate backoff time with jitter
                if attempt <= max_retries:
                    backoff = min(initial_backoff * (2 ** (attempt - 1)), max_backoff)
                    jitter = random.uniform(0.5, 1.5)  # Add some randomness
                    sleep_time = backoff * jitter
                    
                    if self.verbose:
                        self.logger.debug(f"Retrying in {sleep_time:.1f}s...")
                    
                    time.sleep(sleep_time)
        
        # If we get here, all retries failed
        duration = time.monotonic() - start_time
        memory_used = psutil.Process().memory_info().rss / (1024 ** 2)  # MB
        
        return ProcessResult(
            item=item,
            success=False,
            error=str(last_error),
            attempt=attempt,
            duration=duration,
            memory_used_mb=memory_used
        )
    
    def process_batch(
        self,
        items: List[T],
        process_func: Callable[[T, Dict[str, Any]], R],
        process_args: Optional[Dict[str, Any]] = None,
        max_workers: Optional[int] = None,
        quiet: bool = False,
        max_retries: Optional[int] = None,
        initial_backoff: Optional[float] = None,
        max_backoff: Optional[float] = None,
        batch_size: Optional[int] = None
    ) -> List[ProcessResult[R]]:
        """Process a batch of items in parallel with optimized resource usage.
        
        Args:
            items: List of items to process
            process_func: Function to process each item (must be picklable)
            process_args: Additional arguments to pass to process_func
            max_workers: Maximum number of worker processes (None for auto-detect)
            quiet: Whether to suppress progress output
            max_retries: Maximum number of retry attempts for failed items
            initial_backoff: Initial backoff time in seconds for retries
            max_backoff: Maximum backoff time in seconds
            batch_size: Fixed batch size (None for auto-calculate)
            
        Returns:
            List of ProcessResult objects with detailed status information
        """
        if not items:
            return []
            
        # Set default values
        process_args = process_args or {}
        max_retries = max_retries if max_retries is not None else self.max_retries
        initial_backoff = initial_backoff if initial_backoff is not None else self.initial_backoff
        max_backoff = max_backoff if max_backoff is not None else self.max_backoff
        
        # Calculate optimal batch size if not specified
        if batch_size is None:
            batch_size = self._calculate_optimal_batch_size(items)
        
        # Determine number of workers
        if max_workers is None:
            resources = self.calculate_resource_limits()
            max_workers = min(
                resources['max_workers'],
                (len(items) + batch_size - 1) // batch_size  # Ceiling division
            )
        
        # Ensure we have at least 1 worker and at most len(items) workers
        max_workers = max(1, min(max_workers, len(items)))
        
        if self.verbose and not quiet:
            self.logger.info(
                f"Processing {len(items)} items with {max_workers} workers, "
                f"batch size {batch_size}, max_retries={max_retries}"
            )
        
        # Start resource monitoring
        self._resource_monitor.start()
        start_time = time.monotonic()
        
        try:
            results: List[ProcessResult[R]] = []
            
            # Process items in batches
            with ProcessPoolExecutor(
                max_workers=max_workers,
                initializer=init_worker,
                mp_context=multiprocessing.get_context('spawn')
            ) as executor:
                # Create a queue of work items
                work_queue = []
                for i in range(0, len(items), batch_size):
                    batch = items[i:i + batch_size]
                    work_queue.append((i // batch_size, batch))
                
                # Process batches with tqdm progress bar
                with tqdm(
                    total=len(work_queue),
                    disable=quiet or len(work_queue) == 1,
                    desc="Processing batches",
                    unit="batch"
                ) as pbar:
                    # Submit all batches to the executor
                    futures = {}
                    for batch_id, batch in work_queue:
                        future = executor.submit(
                            self._process_batch,
                            batch,
                            process_func,
                            process_args,
                            max_retries,
                            initial_backoff,
                            max_backoff
                        )
                        futures[future] = batch_id
                    
                    # Process completed futures as they complete
                    for future in as_completed(futures):
                        batch_id = futures[future]
                        try:
                            batch_results = future.result()
                            results.extend(batch_results)
                            
                            # Update metrics
                            self._update_metrics(batch_results)
                            
                            # Call result callbacks
                            for result in batch_results:
                                if self.result_callback:
                                    try:
                                        self.result_callback(result)
                                    except Exception as e:
                                        self.logger.error(f"Error in result callback: {e}", exc_info=True)
                            
                        except Exception as e:
                            self.logger.error(f"Error processing batch {batch_id}: {e}", exc_info=True)
                        
                        # Update progress bar
                        pbar.update(1)
                        
                        # Update progress description with resource usage
                        if not quiet:
                            mem_usage = self._resource_monitor.get_peak_memory_usage() * 100
                            pbar.set_postfix({
                                'mem': f"{mem_usage:.1f}%",
                                'success': f"{self._success_count}/{self._processed_count}"
                            })
            
            return results
            
        finally:
            # Stop resource monitoring
            self._resource_monitor.stop()
            
            # Update final metrics
            self.metrics.update({
                'end_time': time.monotonic(),
                'items_processed': self._processed_count,
                'items_succeeded': self._success_count,
                'items_failed': self._failure_count,
                'total_retries': self._retry_count,
                'avg_processing_time': self._total_processing_time / max(1, self._processed_count),
                'peak_memory_mb': self._resource_monitor.get_peak_memory_usage() * 1024,  # Convert to MB
                'cpu_usage_avg': self._resource_monitor.get_cpu_usage_stats()['avg']
            })
            
            if not quiet:
                self._log_summary()
    
    def _process_batch(
        self,
        items: List[T],
        process_func: Callable[[T, Dict[str, Any]], R],
        process_args: Dict[str, Any],
        max_retries: int,
        initial_backoff: float,
        max_backoff: float
    ) -> List[ProcessResult[R]]:
        """Process a batch of items sequentially.
        
        This method runs in a worker process.
        """
        results = []
        for item in items:
            result = self._process_with_retry(
                item=item,
                process_func=process_func,
                process_args=process_args,
                max_retries=max_retries,
                initial_backoff=initial_backoff,
                max_backoff=max_backoff
            )
            results.append(result)
        return results
    
    def _update_metrics(self, results: List[ProcessResult[R]]) -> None:
        """Update metrics based on processing results."""
        for result in results:
            self._processed_count += 1
            if result.success:
                self._success_count += 1
            else:
                self._failure_count += 1
            self._total_processing_time += result.duration
    
    def _log_summary(self) -> None:
        """Log a summary of the processing results."""
        duration = time.monotonic() - self._start_time
        success_rate = (self._success_count / max(1, self._processed_count)) * 100
        
        self.logger.info(
            f"Processing complete: "
            f"{self._success_count} succeeded, "
            f"{self._failure_count} failed, "
            f"{self._retry_count} retries, "
            f"{success_rate:.1f}% success rate, "
            f"took {duration:.1f}s"
        )
        
        if self.verbose:
            # Log detailed resource usage
            cpu_stats = self._resource_monitor.get_cpu_usage_stats()
            peak_mem = self._resource_monitor.get_peak_memory_usage() * 100
            
            self.logger.debug(
                f"Resource usage: "
                f"CPU {cpu_stats['avg']:.1f}% avg, "
                f"Peak memory {peak_mem:.1f}%, "
                f"{self._processed_count / max(1, duration):.1f} items/s"
            )
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Calculate available resources with safety margins
            available_mem_gb = mem.available / (1024 ** 3)
            
            # Adjust max workers based on available memory and CPU
            max_workers = min(
                cpu_count,
                max(1, int(available_mem_gb / 1.5)),  # 1 worker per 1.5GB of available memory
                cpu_count * 2  # Don't exceed 2x CPU count
            )
            
            # Calculate memory limit per worker (in bytes) with safety margin
            mem_per_worker = int((mem.total * 0.75) / max_workers)  # Use 75% of total memory
            
            # Get process info for current process
            process = psutil.Process()
            
            return {
                'max_workers': max_workers,
                'memory_per_worker': mem_per_worker,
                'cpu_percent': 100 / max_workers,
                'total_memory_gb': mem.total / (1024 ** 3),
                'available_memory_gb': available_mem_gb,
                'used_memory_gb': mem.used / (1024 ** 3),
                'swap_total_gb': swap.total / (1024 ** 3),
                'swap_used_gb': swap.used / (1024 ** 3),
                'cpu_count': cpu_count,
                'process_memory_mb': process.memory_info().rss / (1024 ** 2),
                'process_threads': process.num_threads(),
                'timestamp': time.time()
            }
            
        except Exception as e:
            # Fallback to conservative defaults if resource detection fails
            return {
                'max_workers': 2,
                'memory_per_worker': 1 * 1024 * 1024 * 1024,  # 1GB
                'cpu_percent': 50.0,
                'total_memory_gb': 4.0,
                'available_memory_gb': 2.0,
                'used_memory_gb': 2.0,
                'swap_total_gb': 0.0,
                'swap_used_gb': 0.0,
                'cpu_count': 2,
                'process_memory_mb': 100.0,
                'process_threads': 1,
                'timestamp': time.time(),
                'error': str(e)
            }
    
    @classmethod
    def calculate_optimal_batch_size(
        cls, 
        avg_file_size: float, 
        max_workers: int, 
        available_memory_gb: Optional[float] = None
    ) -> int:
        """Calculate optimal batch size based on file size and available resources.
        
        Args:
            avg_file_size: Average file size in bytes
            max_workers: Maximum number of worker processes
            available_memory_gb: Available memory in GB (optional, will be calculated if None)
            
        Returns:
            Optimal batch size
        """
        try:
            resources = cls.calculate_resource_limits()
            
            # Use provided available memory or calculate from system
            if available_memory_gb is None:
                available_memory_mb = resources['available_memory_gb'] * 1024
            else:
                available_memory_mb = available_memory_gb * 1024
            
            # Adjust max_workers based on available memory
            max_workers = min(max_workers, resources['max_workers'])
            
            # Estimate memory needed per item (with 2x safety factor)
            est_mem_per_item_mb = (avg_file_size / (1024 * 1024)) * 2
            
            if est_mem_per_item_mb <= 0:
                est_mem_per_item_mb = 10  # Default to 10MB if we can't estimate
            
            # Calculate max items that can fit in available memory
            max_items_in_memory = int((available_memory_mb * 0.8) / (est_mem_per_item_mb + 1))
            
            # Adjust batch size based on file size and available memory
            if avg_file_size > 200 * 1024 * 1024:  # >200MB
                batch_size = max(1, min(max_workers // 3, max_items_in_memory))
            elif avg_file_size > 50 * 1024 * 1024:  # 50-200MB
                batch_size = max(2, min(max_workers // 2, max_items_in_memory))
            elif avg_file_size > 10 * 1024 * 1024:  # 10-50MB
                batch_size = max(4, min(max_workers, max_items_in_memory))
            else:  # <10MB
                batch_size = max(8, min(max_workers * 2, max_items_in_memory))
            
            return max(1, batch_size)  # Ensure at least 1
            
        except Exception as e:
            # Fallback to conservative defaults
            import logging
            logging.warning(f"Error calculating batch size: {e}, using defaults")
            return min(4, max_workers)
    
    def process_batch(
        self,
        items: List[T],
        process_func: Callable[[T, Dict[str, Any]], R],
        process_args: Optional[Dict[str, Any]] = None,
        max_workers: Optional[int] = None,
        quiet: bool = False,
        max_retries: Optional[int] = None,
        initial_backoff: Optional[float] = None,
        max_backoff: Optional[float] = None,
        batch_size: Optional[int] = None
    ) -> List[ProcessResult[R]]:
        """Process a batch of items in parallel with optimized resource usage.
        
        Args:
            items: List of items to process
            process_func: Function to process each item (must be picklable)
            process_args: Additional arguments to pass to process_func
            max_workers: Maximum number of worker processes (None for auto-detect)
            quiet: Whether to suppress progress output
            max_retries: Maximum number of retry attempts for failed items
            initial_backoff: Initial backoff time in seconds for retries
            max_backoff: Maximum backoff time in seconds
            batch_size: Fixed batch size (None for auto-calculate)
            
        Returns:
            List of ProcessResult objects with detailed status information
        """
        if not items:
            return []
            
        # Use instance defaults if not overridden
        max_retries = self.max_retries if max_retries is None else max_retries
        initial_backoff = self.initial_backoff if initial_backoff is None else initial_backoff
        max_backoff = self.max_backoff if max_backoff is None else max_backoff
        
        total_items = len(items)
        process_args = process_args or {}
        
        # Get system resource information
        resources = self.calculate_resource_limits()
        
        # Adjust max_workers based on available resources
        max_workers = min(
            max_workers or resources['max_workers'],
            resources['max_workers'],
            total_items
        )
        
        # Calculate average item size for batch size determination
        try:
            # Try to get file sizes if items are file paths
            avg_item_size = sum(
                os.path.getsize(str(item)) 
                if hasattr(item, '__fspath__') and os.path.exists(str(item)) 
                else 0 
                for item in items
            ) / total_items if total_items > 0 else 0
            
            # Calculate batch size if not provided
            if batch_size is None:
                batch_size = self.calculate_optimal_batch_size(
                    avg_item_size, 
                    max_workers,
                    resources['available_memory_gb']
                )
        except (OSError, AttributeError) as e:
            self.logger.warning(f"Error calculating item sizes: {e}, using default batch size")
            batch_size = max(1, min(10, total_items // max_workers or 1))
        
        # Initialize results and tracking
        results: List[ProcessResult[R]] = []
        retry_queue: List[Tuple[T, int]] = []  # (item, attempt)
        
        # Setup memory monitoring
        memory_monitor = MemoryMonitor(interval=0.5)
        memory_monitor.start()
        
        try:
            # Process with retry mechanism
            for attempt in range(max_retries + 1):
                if attempt > 0:
                    if not retry_queue:
                        break  # No more items to retry
                        
                    # Apply exponential backoff with jitter
                    backoff = min(
                        initial_backoff * (2 ** (attempt - 1)) * (0.5 + 0.5 * random.random()),
                        max_backoff
                    )
                    
                    if not quiet:
                        self.logger.info(f"Retry attempt {attempt}/{max_retries} after {backoff:.1f}s...")
                    
                    time.sleep(backoff)
                    
                    # Update items to process for this attempt
                    items_to_process = [item for item, _ in retry_queue]
                    retry_queue = []
                else:
                    items_to_process = items
                
                # Split items into batches
                batches = [
                    items_to_process[i:i + batch_size]
                    for i in range(0, len(items_to_process), batch_size)
                ]
                
                # Setup progress bar for this attempt
                with tqdm(
                    total=len(items_to_process),
                    desc=f"Attempt {attempt + 1}/{max_retries + 1}",
                    unit="items",
                    disable=quiet or len(items_to_process) == 1,
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]',
                    dynamic_ncols=True,
                    leave=False
                ) as pbar:
                    # Initialize process pool for this attempt
                    with ProcessPoolExecutor(
                        max_workers=max_workers,
                        initializer=init_worker,
                        mp_context=multiprocessing.get_context('spawn')  # More reliable on Windows
                    ) as executor:
                        # Process each batch
                        for batch in batches:
                            # Check memory usage and throttle if needed
                            while memory_monitor.get_peak_memory_usage() > self.memory_limit_ratio:
                                if not quiet:
                                    self.logger.warning(
                                        f"High memory usage ({memory_monitor.get_peak_memory_usage():.1%}), "
                                        "pausing to allow cleanup..."
                                    )
                                time.sleep(2)
                            
                            # Process batch with error handling
                            try:
                                batch_results = self._process_batch(
                                    executor,
                                    batch,
                                    process_func,
                                    process_args,
                                    attempt,
                                    pbar
                                )
                                
                                # Process results
                                for result in batch_results:
                                    if result.success:
                                        results.append(result)
                                    elif attempt < max_retries:
                                        retry_queue.append((result.item, attempt + 1))
                            
                            except Exception as e:
                                self.logger.error(
                                    f"Error processing batch: {str(e)}",
                                    exc_info=self.verbose
                                )
                                if attempt == max_retries:
                                    raise
                                    
                            # Explicit garbage collection between batches
                            gc.collect()
                
                # If no more items to retry, we're done
                if not retry_queue or attempt == max_retries:
                    break
        
        except Exception as e:
            self.logger.error(
                f"Fatal error in parallel processing: {str(e)}",
                exc_info=self.verbose
            )
            raise
            
        finally:
            # Cleanup
            memory_monitor.stop()
            
            # Log summary of processing
            success_count = sum(1 for r in results if r.success)
            if not quiet and (retry_queue or len(results) != total_items):
                self.logger.info(
                    f"Completed with {success_count}/{total_items} successful "
                    f"({success_count/max(total_items,1):.1%}), "
                    f"{len(retry_queue)} failed after {min(attempt + 1, max_retries + 1)} attempts"
                )
            
        return results
    
    def _process_batch_with_retry(
        self,
        pool: multiprocessing.Pool,
            try:
                # Process items in parallel
                batch_results = []
                for result in pool.imap_unordered(
                    self._process_item_wrapper,
                    [(
                        item['item'], 
                        process_func, 
                        {**process_args, 'attempt': item['attempt']}
                    ) for item in current_batch],
                    chunksize=max(1, len(current_batch) // (pool._processes * 2) or 1)
                ):
                    batch_results.append(result)
                    pbar.update(1)
                
                # Update work items with results
                result_map = {str(r.get('item', '')): r for r in batch_results}
                
                for work_item in current_batch:
                    item_key = str(work_item['item'])
                    if item_key in result_map:
                        result = result_map[item_key]
                        work_item.update({
                            'success': result.get('success', False),
                            'result': result,
                            'last_error': result.get('error')
                        })
                
            except Exception as e:
                error_msg = str(e)
                self.logger.error(
                    f"Batch processing error (attempt {attempt + 1}/{max_retries}): {error_msg}",
                    exc_info=self.verbose
                )
                
                # Update failed items with error information
                for work_item in current_batch:
                    if not work_item['success']:
                        work_item.update({
                            'last_error': error_msg,
                            'success': False
                        })
                
                if attempt == max_retries:
                    self.logger.error(
                        f"Max retries ({max_retries}) reached for batch processing"
                    )
        
        # Compile final results
        final_results = []
        for work_item in work_items:
            if work_item['success'] and work_item['result']:
                final_results.append(work_item['result'])
            else:
                final_results.append({
                    'item': work_item['item'],
                    'success': False,
                    'error': work_item.get('last_error', 'Unknown error'),
                    'attempts': work_item['attempt'] + 1,
                    'timestamp': time.time()
                })
        
        return final_results
    
    @staticmethod
    def _process_item_wrapper(args_tuple: Tuple[Any, Callable, Dict]) -> Dict[str, Any]:
        """Wrapper function for processing a single item in a worker process."""
        item, process_func, process_args = args_tuple
        
        try:
            return process_func(item, **process_args)
        except Exception as e:
            return {
                'item': str(item),
                'error': str(e),
                'success': False,
                'traceback': traceback.format_exc()
            }
