"""Watchdog timer context manager for timeout protection."""

import signal
import time
import threading
from contextlib import contextmanager
from typing import Optional, Callable, Any
import logging


class WatchdogTimer:
    """Context manager for implementing timeouts on operations."""

    def __init__(self, timeout_seconds: float, operation_name: str = "operation"):
        """Initialize watchdog timer.

        Args:
            timeout_seconds: Maximum time to allow for the operation
            operation_name: Name of the operation for logging
        """
        self.timeout_seconds = timeout_seconds
        self.operation_name = operation_name
        self.logger = logging.getLogger(__name__)
        self._timer: Optional[threading.Timer] = None
        self._timeout_occurred = False
        self._original_handler = None

    def _timeout_handler(self, signum, frame):
        """Handle timeout signal."""
        self._timeout_occurred = True
        self.logger.warning(f"Operation '{self.operation_name}' timed out after {self.timeout_seconds} seconds")
        raise TimeoutError(f"Operation '{self.operation_name}' exceeded timeout of {self.timeout_seconds} seconds")

    def __enter__(self):
        """Enter the context manager."""
        # Set up signal-based timeout
        try:
            self._original_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(int(self.timeout_seconds))
        except (OSError, AttributeError):
            # SIGALRM not available on Windows or in some environments
            # Fall back to thread-based timeout
            self._timer = threading.Timer(self.timeout_seconds, self._thread_timeout)
            self._timer.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        # Clean up timeout mechanism
        try:
            signal.alarm(0)
            if self._original_handler is not None:
                signal.signal(signal.SIGALRM, self._original_handler)
        except (OSError, AttributeError):
            # Clean up thread-based timer
            if self._timer and self._timer.is_alive():
                self._timer.cancel()

        # Re-raise timeout exception if it occurred
        if self._timeout_occurred:
            return False  # Don't suppress the TimeoutError

        return None  # Continue normal exception handling

    def _thread_timeout(self):
        """Thread-based timeout handler for platforms without SIGALRM."""
        self._timeout_occurred = True
        self.logger.warning(f"Operation '{self.operation_name}' timed out after {self.timeout_seconds} seconds")


@contextmanager
def watchdog_timeout(timeout_seconds: float, operation_name: str = "operation"):
    """Context manager for implementing timeouts on operations.

    Args:
        timeout_seconds: Maximum time to allow for the operation
        operation_name: Name of the operation for logging

    Yields:
        None

    Raises:
        TimeoutError: If the operation exceeds the timeout
    """
    with WatchdogTimer(timeout_seconds, operation_name):
        yield


def calculate_timeout_for_file_size(file_size_mb: float, base_timeout: float = 30.0) -> float:
    """Calculate appropriate timeout based on file size.

    Args:
        file_size_mb: Size of file in megabytes
        base_timeout: Base timeout for small files

    Returns:
        Calculated timeout in seconds
    """
    if file_size_mb <= 10:
        return base_timeout
    elif file_size_mb <= 100:
        return base_timeout * 2
    elif file_size_mb <= 500:
        return base_timeout * 4
    else:
        return base_timeout * 8


class TimeoutConfig:
    """Configuration for timeout settings based on operation type and file size."""

    def __init__(self):
        self.base_timeouts = {
            'mesh_loading': 30.0,
            'mesh_validation': 15.0,
            'mesh_repair': 60.0,
            'slicing': 120.0,
            'gcode_generation': 90.0,
            'analysis': 45.0,
            'export': 30.0
        }

        # File size multipliers
        self.size_multipliers = {
            'small': 1.0,      # < 10MB
            'medium': 2.0,     # 10-100MB
            'large': 4.0,      # 100-500MB
            'huge': 8.0        # > 500MB
        }

    def get_timeout(self, operation_type: str, file_size_mb: float = 0) -> float:
        """Get timeout for operation based on type and file size.

        Args:
            operation_type: Type of operation
            file_size_mb: Size of file being processed

        Returns:
            Timeout in seconds
        """
        base_timeout = self.base_timeouts.get(operation_type, 30.0)

        # Determine size category
        if file_size_mb <= 10:
            multiplier = self.size_multipliers['small']
        elif file_size_mb <= 100:
            multiplier = self.size_multipliers['medium']
        elif file_size_mb <= 500:
            multiplier = self.size_multipliers['large']
        else:
            multiplier = self.size_multipliers['huge']

        timeout = base_timeout * multiplier

        # Add some buffer time
        return timeout + 10.0


# Global timeout configuration
timeout_config = TimeoutConfig()
