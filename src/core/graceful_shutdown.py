"""
Graceful shutdown handler for production deployments.

Handles SIGTERM, SIGINT, and other shutdown signals to ensure:
- Ongoing requests complete before shutdown
- Database connections are properly closed
- Cache connections are cleaned up
- Resources are released properly
- Audit logs are flushed
"""

import atexit
import logging
import signal
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class GracefulShutdownHandler:
    """
    Manages graceful application shutdown.

    Coordinates orderly shutdown of all application components,
    ensuring data integrity and proper resource cleanup.
    """

    def __init__(self, grace_period_seconds: int = 30):
        """
        Initialize shutdown handler.

        Args:
            grace_period_seconds: Maximum time to wait for graceful shutdown
        """
        self.grace_period_seconds = grace_period_seconds
        self.shutdown_requested = False
        self.shutdown_event = threading.Event()
        self.cleanup_handlers: List[Callable[[], None]] = []
        self.shutdown_lock = threading.Lock()
        self._original_handlers = {}
        self._registered = False

    def register_cleanup_handler(self, handler: Callable[[], None], name: Optional[str] = None):
        """
        Register a cleanup handler to be called during shutdown.

        Args:
            handler: Function to call during cleanup
            name: Optional name for logging purposes
        """
        self.cleanup_handlers.append((handler, name or handler.__name__))
        logger.debug(f"Registered cleanup handler: {name or handler.__name__}")

    def register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        if self._registered:
            logger.warning("Signal handlers already registered")
            return

        # Store original handlers
        self._original_handlers[signal.SIGTERM] = signal.signal(signal.SIGTERM, self._signal_handler)
        self._original_handlers[signal.SIGINT] = signal.signal(signal.SIGINT, self._signal_handler)

        # On Unix systems, handle additional signals
        if hasattr(signal, 'SIGHUP'):
            self._original_handlers[signal.SIGHUP] = signal.signal(signal.SIGHUP, self._signal_handler)

        # Register atexit handler
        atexit.register(self._atexit_handler)

        self._registered = True
        logger.info("Graceful shutdown handlers registered")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.warning(f"Received signal {signal_name} ({signum}), initiating graceful shutdown")

        # Trigger shutdown
        self.initiate_shutdown()

    def _atexit_handler(self):
        """Handle process exit."""
        if not self.shutdown_requested:
            logger.info("Process exiting, running cleanup handlers")
            self._run_cleanup_handlers()

    def initiate_shutdown(self):
        """Initiate graceful shutdown sequence."""
        with self.shutdown_lock:
            if self.shutdown_requested:
                logger.warning("Shutdown already in progress")
                return

            self.shutdown_requested = True
            self.shutdown_event.set()

        logger.info(f"Graceful shutdown initiated (grace period: {self.grace_period_seconds}s)")

        # Start shutdown sequence in separate thread
        shutdown_thread = threading.Thread(target=self._shutdown_sequence, daemon=False)
        shutdown_thread.start()

    def _shutdown_sequence(self):
        """Execute shutdown sequence."""
        try:
            start_time = time.time()

            # Wait for grace period or until all handlers complete
            self._run_cleanup_handlers()

            elapsed = time.time() - start_time
            logger.info(f"Graceful shutdown completed in {elapsed:.2f}s")

        except Exception as exc:
            logger.exception(f"Error during shutdown sequence: {exc}")
        finally:
            # Force exit after grace period
            if time.time() - start_time > self.grace_period_seconds:
                logger.warning(f"Grace period exceeded, forcing shutdown")

            sys.exit(0)

    def _run_cleanup_handlers(self):
        """Run all registered cleanup handlers."""
        logger.info(f"Running {len(self.cleanup_handlers)} cleanup handlers")

        for handler, name in self.cleanup_handlers:
            try:
                logger.debug(f"Running cleanup handler: {name}")
                start = time.time()
                handler()
                duration = time.time() - start
                logger.debug(f"Cleanup handler '{name}' completed in {duration:.2f}s")
            except Exception as exc:
                logger.exception(f"Cleanup handler '{name}' failed: {exc}")

    def is_shutting_down(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_requested

    def wait_for_shutdown(self, timeout: Optional[float] = None):
        """
        Block until shutdown is requested.

        Args:
            timeout: Maximum time to wait (None = wait forever)

        Returns:
            True if shutdown was requested, False if timeout occurred
        """
        return self.shutdown_event.wait(timeout)

    @contextmanager
    def shutdown_barrier(self):
        """
        Context manager that prevents new work during shutdown.

        Usage:
            with shutdown_handler.shutdown_barrier():
                # This code will not execute if shutdown is in progress
                do_work()
        """
        if self.shutdown_requested:
            raise RuntimeError("Shutdown in progress, rejecting new work")

        try:
            yield
        finally:
            pass


class RequestDrainer:
    """
    Manages request draining during shutdown.

    Tracks active requests and blocks shutdown until all requests complete
    or the grace period expires.
    """

    def __init__(self, grace_period_seconds: int = 30):
        """
        Initialize request drainer.

        Args:
            grace_period_seconds: Maximum time to wait for request completion
        """
        self.grace_period_seconds = grace_period_seconds
        self.active_requests = 0
        self.shutdown_requested = False
        self.lock = threading.Lock()
        self.no_requests_event = threading.Event()
        self.no_requests_event.set()  # Initially no active requests

    @contextmanager
    def request_context(self):
        """
        Context manager for tracking active requests.

        Usage:
            with request_drainer.request_context():
                handle_request()
        """
        # Check if shutdown requested
        with self.lock:
            if self.shutdown_requested:
                raise RuntimeError("Shutdown in progress, rejecting new requests")

            self.active_requests += 1
            if self.active_requests == 1:
                self.no_requests_event.clear()

        try:
            yield
        finally:
            with self.lock:
                self.active_requests -= 1
                if self.active_requests == 0:
                    self.no_requests_event.set()

    def drain_requests(self) -> bool:
        """
        Drain active requests before shutdown.

        Returns:
            True if all requests completed, False if timeout occurred
        """
        with self.lock:
            self.shutdown_requested = True
            active = self.active_requests

        if active == 0:
            logger.info("No active requests to drain")
            return True

        logger.info(f"Draining {active} active requests (timeout: {self.grace_period_seconds}s)")

        start_time = time.time()
        completed = self.no_requests_event.wait(timeout=self.grace_period_seconds)

        elapsed = time.time() - start_time

        if completed:
            logger.info(f"All requests drained in {elapsed:.2f}s")
            return True
        else:
            with self.lock:
                remaining = self.active_requests
            logger.warning(
                f"Request drain timeout after {elapsed:.2f}s, "
                f"{remaining} requests still active"
            )
            return False

    def get_active_count(self) -> int:
        """Get number of currently active requests."""
        with self.lock:
            return self.active_requests


# Global instances
_shutdown_handler: Optional[GracefulShutdownHandler] = None
_request_drainer: Optional[RequestDrainer] = None


def get_shutdown_handler(grace_period_seconds: int = 30) -> GracefulShutdownHandler:
    """Get or create global shutdown handler."""
    global _shutdown_handler
    if _shutdown_handler is None:
        _shutdown_handler = GracefulShutdownHandler(grace_period_seconds)
        _shutdown_handler.register_signal_handlers()
    return _shutdown_handler


def get_request_drainer(grace_period_seconds: int = 30) -> RequestDrainer:
    """Get or create global request drainer."""
    global _request_drainer
    if _request_drainer is None:
        _request_drainer = RequestDrainer(grace_period_seconds)

        # Register with shutdown handler
        shutdown_handler = get_shutdown_handler(grace_period_seconds)
        shutdown_handler.register_cleanup_handler(
            _request_drainer.drain_requests,
            name="drain_active_requests"
        )

    return _request_drainer


def register_cleanup(handler: Callable[[], None], name: Optional[str] = None):
    """
    Register a cleanup handler for graceful shutdown.

    Args:
        handler: Function to call during cleanup
        name: Optional name for logging
    """
    shutdown_handler = get_shutdown_handler()
    shutdown_handler.register_cleanup_handler(handler, name)


# Convenience decorators
def with_request_tracking(func):
    """
    Decorator to track request lifecycle.

    Usage:
        @with_request_tracking
        def handle_request():
            ...
    """
    def wrapper(*args, **kwargs):
        request_drainer = get_request_drainer()
        with request_drainer.request_context():
            return func(*args, **kwargs)

    return wrapper
