"""Unified error recovery strategies using Strategy pattern.

Provides composable, reusable error recovery strategies for batch processing,
network operations, and file handling.

Replaces scattered ad-hoc error handling with structured, testable strategies.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Optional, List, Generic, TypeVar
import random

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RecoveryContext:
    """Context information for recovery strategies."""
    attempt: int
    max_attempts: int
    last_error: Optional[Exception]
    elapsed_time: float
    timeout_seconds: float


class RecoveryStrategy(ABC, Generic[T]):
    """Abstract base for recovery strategies."""

    @abstractmethod
    def should_retry(self, context: RecoveryContext) -> bool:
        """Determine if operation should be retried."""

    @abstractmethod
    def get_delay(self, context: RecoveryContext) -> float:
        """Get delay before next retry in seconds."""

    @abstractmethod
    async def execute_recovery(self, context: RecoveryContext) -> Optional[Any]:
        """Execute recovery action. Return None if not applicable."""


class ExponentialBackoffStrategy(RecoveryStrategy):
    """Exponential backoff with jitter.

    Delays: 1s, 2s, 4s, 8s, 16s...
    With random jitter to avoid thundering herd.
    """

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        jitter_factor: float = 0.1
    ):
        """Initialize exponential backoff strategy."""
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor

    def should_retry(self, context: RecoveryContext) -> bool:
        """Retry if under limit and within timeout."""
        if context.attempt >= context.max_attempts:
            logger.warning("Max retry attempts (%d) reached", context.max_attempts)
            return False

        if context.elapsed_time + self.get_delay(context) > context.timeout_seconds:
            logger.warning("Would exceed timeout; stopping retries")
            return False

        return True

    def get_delay(self, context: RecoveryContext) -> float:
        """Calculate exponential delay with jitter."""
        delay = min(self.base_delay * (2 ** (context.attempt - 1)), self.max_delay)

        # Add jitter: ±10% by default
        jitter = delay * self.jitter_factor * (random.random() - 0.5) * 2
        final_delay = max(0.0, delay + jitter)

        logger.debug(
            "Retry attempt %d/%d: waiting %.2f seconds",
            context.attempt,
            context.max_attempts,
            final_delay
        )

        return final_delay

    async def execute_recovery(self, context: RecoveryContext) -> None:
        """No specific recovery action, just backoff."""
        delay = self.get_delay(context)
        if delay > 0:
            await asyncio.sleep(delay)


class CircuitBreakerStrategy(RecoveryStrategy):
    """Circuit breaker: fail fast after threshold errors."""

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0
    ):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.consecutive_failures = 0
        self.last_failure_time = 0.0

    def should_retry(self, context: RecoveryContext) -> bool:
        """Reject if circuit is open (too many failures)."""
        current_time = time.time()

        # Check if circuit should reset
        if current_time - self.last_failure_time > self.reset_timeout:
            self.consecutive_failures = 0
            logger.info("Circuit breaker reset")

        # Count as failure
        if context.last_error is not None:
            self.consecutive_failures += 1
            self.last_failure_time = current_time

        # Open circuit if threshold exceeded
        if self.consecutive_failures >= self.failure_threshold:
            logger.error(
                "Circuit breaker open: %d consecutive failures",
                self.consecutive_failures
            )
            return False

        return context.attempt < context.max_attempts

    def get_delay(self, context: RecoveryContext) -> float:
        """Delay increases with failures."""
        return min(10.0, self.consecutive_failures * 0.5)

    async def execute_recovery(self, context: RecoveryContext) -> None:
        """No specific recovery, just track failures."""
        pass


class MemoryRecoveryStrategy(RecoveryStrategy):
    """Clear memory/caches when facing memory errors."""

    def should_retry(self, context: RecoveryContext) -> bool:
        """Retry if memory error occurred."""
        if context.last_error is None:
            return False

        is_memory_error = isinstance(context.last_error, (MemoryError, OSError))
        if is_memory_error:
            logger.warning("Memory error detected, attempting recovery")
            return context.attempt < context.max_attempts

        return False

    def get_delay(self, context: RecoveryContext) -> float:
        """Longer delay for memory recovery."""
        return 5.0 * context.attempt

    async def execute_recovery(self, context: RecoveryContext) -> None:
        """Clear caches and request garbage collection."""
        import gc

        logger.info("Executing memory recovery: clearing caches")
        gc.collect()
        logger.info("Garbage collection completed")


class TimeoutRecoveryStrategy(RecoveryStrategy):
    """Handle timeout errors with longer delays."""

    def __init__(self, timeout_multiplier: float = 2.0):
        """Initialize timeout recovery."""
        self.timeout_multiplier = timeout_multiplier

    def should_retry(self, context: RecoveryContext) -> bool:
        """Retry timeout errors."""
        if context.last_error is None:
            return False

        is_timeout = isinstance(context.last_error, (TimeoutError, asyncio.TimeoutError))
        if is_timeout:
            logger.warning("Timeout detected, retrying with longer timeout")
            return context.attempt < context.max_attempts

        return False

    def get_delay(self, context: RecoveryContext) -> float:
        """Exponential delay: allow more time on retry."""
        return 5.0 * (self.timeout_multiplier ** (context.attempt - 1))

    async def execute_recovery(self, context: RecoveryContext) -> None:
        """Inform caller to increase timeout if possible."""
        logger.info(
            "Timeout recovery: consider increasing timeout to %.0f seconds",
            context.timeout_seconds * self.timeout_multiplier
        )


class RetryableOperation:
    """Execute operation with configurable recovery strategies."""

    def __init__(
        self,
        strategies: Optional[List[RecoveryStrategy]] = None,
        max_attempts: int = 3,
        timeout_seconds: float = 300.0
    ):
        """Initialize retry operation.

        Args:
            strategies: List of recovery strategies to try in order
            max_attempts: Maximum retry attempts
            timeout_seconds: Total timeout for all retries
        """
        self.strategies = strategies or [ExponentialBackoffStrategy()]
        self.max_attempts = max_attempts
        self.timeout_seconds = timeout_seconds

    async def execute(
        self,
        operation: Callable[[], Any],
        description: str = "Operation"
    ) -> Any:
        """Execute operation with recovery strategies.

        Args:
            operation: Async callable to execute
            description: Description for logging

        Returns:
            Result of operation
        """
        start_time = time.time()
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.info("Executing %s (attempt %d/%d)", description, attempt, self.max_attempts)
                result = await operation()
                logger.info("%s succeeded on attempt %d", description, attempt)
                return result

            except Exception as exc:
                last_error = exc
                elapsed_time = time.time() - start_time

                logger.warning(
                    "%s failed (attempt %d/%d): %s",
                    description,
                    attempt,
                    self.max_attempts,
                    str(exc)
                )

                # Create recovery context
                context = RecoveryContext(
                    attempt=attempt,
                    max_attempts=self.max_attempts,
                    last_error=exc,
                    elapsed_time=elapsed_time,
                    timeout_seconds=self.timeout_seconds
                )

                # Try each recovery strategy
                recovered = False
                for strategy in self.strategies:
                    if strategy.should_retry(context):
                        logger.info("Applying %s", strategy.__class__.__name__)
                        await strategy.execute_recovery(context)
                        delay = strategy.get_delay(context)
                        if delay > 0:
                            await asyncio.sleep(delay)
                        recovered = True
                        break

                if not recovered:
                    logger.error("%s exhausted all recovery strategies", description)
                    raise

        # All attempts failed
        if last_error:
            raise last_error


# Synchronous wrapper for sync code
class SyncRetryableOperation:
    """Synchronous version of RetryableOperation."""

    def __init__(
        self,
        strategies: Optional[List[RecoveryStrategy]] = None,
        max_attempts: int = 3,
        timeout_seconds: float = 300.0
    ):
        """Initialize sync retry operation."""
        self.strategies = strategies or [ExponentialBackoffStrategy()]
        self.max_attempts = max_attempts
        self.timeout_seconds = timeout_seconds

    def execute(
        self,
        operation: Callable[[], Any],
        description: str = "Operation"
    ) -> Any:
        """Execute operation synchronously with recovery strategies."""
        start_time = time.time()
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.info("Executing %s (attempt %d/%d)", description, attempt, self.max_attempts)
                result = operation()
                logger.info("%s succeeded on attempt %d", description, attempt)
                return result

            except Exception as exc:
                last_error = exc
                elapsed_time = time.time() - start_time

                logger.warning(
                    "%s failed (attempt %d/%d): %s",
                    description,
                    attempt,
                    self.max_attempts,
                    str(exc)
                )

                context = RecoveryContext(
                    attempt=attempt,
                    max_attempts=self.max_attempts,
                    last_error=exc,
                    elapsed_time=elapsed_time,
                    timeout_seconds=self.timeout_seconds
                )

                # Try each recovery strategy
                recovered = False
                for strategy in self.strategies:
                    if strategy.should_retry(context):
                        logger.info("Applying %s", strategy.__class__.__name__)
                        # Create dummy async operation for sync wrapper
                        asyncio.run(strategy.execute_recovery(context))
                        delay = strategy.get_delay(context)
                        if delay > 0:
                            time.sleep(delay)
                        recovered = True
                        break

                if not recovered:
                    logger.error("%s exhausted all recovery strategies", description)
                    raise

        if last_error:
            raise last_error


__all__ = [
    'RecoveryStrategy',
    'ExponentialBackoffStrategy',
    'CircuitBreakerStrategy',
    'MemoryRecoveryStrategy',
    'TimeoutRecoveryStrategy',
    'RetryableOperation',
    'SyncRetryableOperation',
    'RecoveryContext'
]
