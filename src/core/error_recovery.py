"""Error recovery manager for 3D print CAD assistant operations."""

import time
import logging
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass


class OperationType(Enum):
    """Types of operations that can fail and need recovery."""
    MESH_LOADING = "mesh_loading"
    VALIDATION = "validation"
    REPAIR = "repair"
    SLICING = "slicing"
    GCODE_GENERATION = "gcode_generation"
    RECOMMENDATIONS = "recommendations"


@dataclass
class RecoveryConfig:
    """Configuration for error recovery."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    retry_on_exceptions: tuple = (Exception,)


class ErrorRecoveryManager:
    """Manages error recovery for various 3D printing operations."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.recovery_configs: Dict[OperationType, RecoveryConfig] = {}
        self.recovery_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000

        # Default configurations for each operation type
        self._initialize_default_configs()

    def _initialize_default_configs(self):
        """Initialize default recovery configurations for each operation type."""
        configs = {
            OperationType.MESH_LOADING: RecoveryConfig(
                max_retries=3,
                base_delay=1.0,
                retry_on_exceptions=(FileNotFoundError, PermissionError, OSError)
            ),
            OperationType.VALIDATION: RecoveryConfig(
                max_retries=2,
                base_delay=0.5,
                retry_on_exceptions=(ValueError, TypeError)
            ),
            OperationType.REPAIR: RecoveryConfig(
                max_retries=3,
                base_delay=2.0,
                retry_on_exceptions=(RuntimeError, ValueError)
            ),
            OperationType.SLICING: RecoveryConfig(
                max_retries=2,
                base_delay=5.0,
                retry_on_exceptions=(RuntimeError, MemoryError)
            ),
            OperationType.GCODE_GENERATION: RecoveryConfig(
                max_retries=2,
                base_delay=3.0,
                retry_on_exceptions=(RuntimeError, ValueError)
            ),
            OperationType.RECOMMENDATIONS: RecoveryConfig(
                max_retries=1,
                base_delay=1.0,
                retry_on_exceptions=(Exception,)
            ),
        }

        self.recovery_configs.update(configs)

    def configure_operation(self, operation_type: OperationType, config: RecoveryConfig):
        """Configure recovery settings for a specific operation type.

        Args:
            operation_type: The operation type to configure
            config: Recovery configuration
        """
        self.recovery_configs[operation_type] = config
        self.logger.info(f"Updated recovery config for {operation_type.value}")

    def execute_with_recovery(self,
                            operation_type: OperationType,
                            operation_func: Callable,
                            *args,
                            fallback_func: Optional[Callable] = None,
                            **kwargs) -> Any:
        """Execute an operation with automatic error recovery.

        Args:
            operation_type: Type of operation being performed
            operation_func: Function to execute
            *args: Positional arguments for the operation function
            fallback_func: Optional fallback function to call on failure
            **kwargs: Keyword arguments for the operation function

        Returns:
            Result of the operation or fallback function

        Raises:
            Exception: If recovery fails and no fallback is available
        """
        config = self.recovery_configs.get(operation_type, RecoveryConfig())

        for attempt in range(config.max_retries + 1):
            try:
                self.logger.debug(f"Executing {operation_type.value}, attempt {attempt + 1}")

                result = operation_func(*args, **kwargs)

                if attempt > 0:
                    self.logger.info(f"Successfully recovered {operation_type.value} on attempt {attempt + 1}")
                    self._log_recovery(operation_type, True, attempt + 1, None)

                return result

            except Exception as e:
                error_msg = str(e)
                should_retry = self._should_retry(e, config, attempt)

                self.logger.warning(f"{operation_type.value} failed on attempt {attempt + 1}: {error_msg}")

                if not should_retry:
                    self._log_recovery(operation_type, False, attempt + 1, error_msg)

                    if fallback_func:
                        self.logger.info(f"Attempting fallback for {operation_type.value}")
                        try:
                            return fallback_func(*args, **kwargs)
                        except Exception as fallback_error:
                            self.logger.error(f"Fallback also failed for {operation_type.value}: {fallback_error}")
                            raise fallback_error

                    raise e

                delay = self._calculate_delay(attempt, config)
                self.logger.info(f"Retrying {operation_type.value} in {delay:.1f} seconds")
                time.sleep(delay)

        # If we get here, all retries failed
        final_error = f"All retry attempts failed for {operation_type.value}"
        self._log_recovery(operation_type, False, config.max_retries + 1, final_error)
        raise RuntimeError(final_error)

    def _should_retry(self, exception: Exception, config: RecoveryConfig, attempt: int) -> bool:
        """Determine if an operation should be retried based on the exception and attempt count."""
        if attempt >= config.max_retries:
            return False

        return isinstance(exception, config.retry_on_exceptions)

    def _calculate_delay(self, attempt: int, config: RecoveryConfig) -> float:
        """Calculate delay before retry using exponential backoff."""
        delay = config.base_delay * (config.backoff_factor ** attempt)

        # Add jitter to prevent thundering herd
        import random
        jitter = random.uniform(0.8, 1.2)
        delay *= jitter

        return min(delay, config.max_delay)

    def _log_recovery(self, operation_type: OperationType, success: bool, attempts: int, error: Optional[str]):
        """Log recovery attempt for monitoring and analysis."""
        log_entry = {
            'operation_type': operation_type.value,
            'success': success,
            'attempts': attempts,
            'timestamp': time.time(),
            'error': error
        }

        self.recovery_history.append(log_entry)

        # Maintain history size
        if len(self.recovery_history) > self.max_history_size:
            self.recovery_history = self.recovery_history[-self.max_history_size:]

    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get statistics about recovery operations."""
        if not self.recovery_history:
            return {'total_operations': 0}

        total_ops = len(self.recovery_history)
        successful_ops = sum(1 for entry in self.recovery_history if entry['success'])
        failed_ops = total_ops - successful_ops

        # Calculate average attempts for successful operations
        successful_attempts = [entry['attempts'] for entry in self.recovery_history if entry['success']]
        avg_attempts = sum(successful_attempts) / len(successful_attempts) if successful_attempts else 0

        # Group by operation type
        by_type = {}
        for entry in self.recovery_history:
            op_type = entry['operation_type']
            if op_type not in by_type:
                by_type[op_type] = {'total': 0, 'successful': 0, 'failed': 0}
            by_type[op_type]['total'] += 1
            if entry['success']:
                by_type[op_type]['successful'] += 1
            else:
                by_type[op_type]['failed'] += 1

        return {
            'total_operations': total_ops,
            'successful_operations': successful_ops,
            'failed_operations': failed_ops,
            'success_rate': successful_ops / total_ops if total_ops > 0 else 0,
            'average_attempts_successful': avg_attempts,
            'by_operation_type': by_type
        }

    def reset_recovery_history(self):
        """Reset the recovery history."""
        self.recovery_history.clear()
        self.logger.info("Recovery history reset")


# Global instance for easy access
error_recovery_manager = ErrorRecoveryManager()
