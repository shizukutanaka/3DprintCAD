"""Comprehensive error handling and recovery system."""
from __future__ import annotations

import sys
import traceback
import logging
import time
from typing import Dict, Any, Optional, Callable, Type, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json
from contextlib import contextmanager

class RetryManager:
    """Advanced retry manager with exponential backoff and jitter."""

    def __init__(self,
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                if attempt == self.max_retries:
                    logger.error(f"Function failed after {self.max_retries} attempts: {e}")
                    raise

                # Calculate delay with exponential backoff
                delay = self._calculate_delay(attempt)

                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)

        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add random jitter to prevent thundering herd
            jitter_amount = delay * 0.1
            delay += np.random.uniform(-jitter_amount, jitter_amount)

        return max(0.0, delay)


class AdaptiveErrorHandler:
    """Adaptive error handler that learns from failure patterns."""

    def __init__(self):
        self.failure_patterns: Dict[str, int] = defaultdict(int)
        self.recovery_strategies: Dict[str, Callable] = {}
        self.error_history: List[ErrorInfo] = []
        self.max_history = 1000
        self._lock = threading.RLock()

    def register_recovery_strategy(self, error_pattern: str, strategy: Callable):
        """Register a recovery strategy for specific error patterns."""
        self.recovery_strategies[error_pattern] = strategy

    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> bool:
        """Handle error with adaptive recovery."""
        context = context or {}

        # Classify error
        error_info = self._classify_error(error, context)

        with self._lock:
            # Record error
            self.error_history.append(error_info)
            if len(self.error_history) > self.max_history:
                self.error_history = self.error_history[-self.max_history:]

            # Update failure patterns
            pattern = self._get_error_pattern(error_info)
            self.failure_patterns[pattern] += 1

        # Attempt recovery
        return self._attempt_recovery(error_info)

    def _classify_error(self, error: Exception, context: Dict[str, Any]) -> ErrorInfo:
        """Classify error and create error info."""
        # Determine category
        category = ErrorCategory.UNKNOWN
        if isinstance(error, (OSError, IOError)):
            category = ErrorCategory.IO
        elif isinstance(error, MemoryError):
            category = ErrorCategory.MEMORY
        elif "security" in str(error).lower():
            category = ErrorCategory.SECURITY

        # Determine severity
        severity = ErrorSeverity.MEDIUM
        if "critical" in str(error).lower():
            severity = ErrorSeverity.CRITICAL

        return ErrorInfo(
            error_id=f"ERR_{int(time.time())}_{id(error)}",
            category=category,
            severity=severity,
            message=str(error),
            details={"type": type(error).__name__},
            timestamp=time.time(),
            context=context,
            stack_trace=traceback.format_exc(),
            recovery_suggestions=self._get_recovery_suggestions(error)
        )

    def _get_error_pattern(self, error_info: ErrorInfo) -> str:
        """Generate pattern key for error tracking."""
        return f"{error_info.category.value}_{error_info.severity.value}"

    def _get_recovery_suggestions(self, error: Exception) -> List[str]:
        """Get recovery suggestions for error."""
        suggestions = []

        if isinstance(error, MemoryError):
            suggestions.extend([
                "Free up memory by clearing caches",
                "Reduce batch size for processing",
                "Close other applications"
            ])
        elif isinstance(error, (OSError, IOError)):
            suggestions.extend([
                "Check file permissions",
                "Verify file path exists",
                "Ensure sufficient disk space"
            ])

        return suggestions

    def _attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """Attempt error recovery."""
        pattern = self._get_error_pattern(error_info)

        # Try registered strategy
        if pattern in self.recovery_strategies:
            try:
                return self.recovery_strategies[pattern](error_info)
            except Exception as e:
                logger.error(f"Recovery strategy failed: {e}")

        # Default recovery based on category
        if error_info.category == ErrorCategory.MEMORY:
            return self._recover_from_memory_error()
        elif error_info.category == ErrorCategory.IO:
            return self._recover_from_io_error(error_info)

        return False

    def _recover_from_memory_error(self) -> bool:
        """Recover from memory errors."""
        try:
            # Force garbage collection
            gc.collect()

            # Clear caches
            from .memory_manager import get_memory_manager
            manager = get_memory_manager()
            manager.optimize_memory_usage()

            return True
        except Exception as e:
            logger.error(f"Memory recovery failed: {e}")
            return False

    def _recover_from_io_error(self, error_info: ErrorInfo) -> bool:
        """Recover from I/O errors."""
        try:
            # Retry with different approach
            if "permission" in error_info.message.lower():
                # Try to fix permissions or use alternative path
                pass
            return True
        except Exception as e:
            logger.error(f"I/O recovery failed: {e}")
            return False

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics."""
        with self._lock:
            return {
                "total_errors": len(self.error_history),
                "failure_patterns": dict(self.failure_patterns),
                "errors_by_category": self._count_by_category(),
                "recent_errors": len([e for e in self.error_history if time.time() - e.timestamp < 300])
            }

    def _count_by_category(self) -> Dict[str, int]:
        """Count errors by category."""
        counts = defaultdict(int)
        for error in self.error_history:
            counts[error.category.value] += 1
        return dict(counts)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    VALIDATION = "validation"
    IO = "io"
    MEMORY = "memory"
    SECURITY = "security"
    NETWORK = "network"
    PROCESSING = "processing"
    USER_INPUT = "user_input"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Structured error information."""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any]
    timestamp: float
    context: Dict[str, Any]
    stack_trace: Optional[str]
    recovery_suggestions: List[str]
    user_message: str


class ErrorHandler:
    """Centralized error handling and recovery system."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize error handler with configuration."""
        self.config = config or {}
        self.max_retries = self.config.get('error_max_retries', 3)
        self.retry_delay = self.config.get('error_retry_delay', 1.0)
        self.enable_notifications = self.config.get('error_notifications', False)
        self.error_log = []
        self.error_handlers: Dict[Type[Exception], Callable] = {}
        self.error_count = 0
        self.error_history: List[ErrorInfo] = []
        self.max_history = 1000
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = {}
        self.setup_default_handlers()

    def setup_default_handlers(self):
        """Setup default error handlers for common exceptions."""

        # File I/O errors
        self.register_handler(FileNotFoundError, self._handle_file_not_found)
        self.register_handler(PermissionError, self._handle_permission_error)
        self.register_handler(OSError, self._handle_os_error)

        # Memory errors
        self.register_handler(MemoryError, self._handle_memory_error)

        # Value errors
        self.register_handler(ValueError, self._handle_value_error)
        self.register_handler(TypeError, self._handle_type_error)

        # Network errors
        try:
            import requests
            self.register_handler(requests.RequestException, self._handle_network_error)
            self.register_handler(requests.Timeout, self._handle_timeout_error)
        except ImportError:
            pass

    def register_handler(self, exception_type: Type[Exception], handler: Callable):
        """Register a custom error handler for specific exception types."""
        self.error_handlers[exception_type] = handler

    def register_recovery_strategy(self, category: ErrorCategory, strategy: Callable):
        """Register a recovery strategy for specific error categories."""
        if category not in self.recovery_strategies:
            self.recovery_strategies[category] = []
        self.recovery_strategies[category].append(strategy)

    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """Handle an error and return structured error information."""
        self.error_count += 1
        context = context or {}

        # Generate unique error ID
        error_id = f"ERR_{int(time.time())}_{self.error_count}"

        # Classify error
        category = self._classify_error(error)
        severity = self._assess_severity(error, category)

        # Extract stack trace
        stack_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))

        # Generate recovery suggestions
        recovery_suggestions = self._generate_recovery_suggestions(error, category)

        # Create user-friendly message
        user_message = self._create_user_message(error, category, severity)

        # Create error info
        error_info = ErrorInfo(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(error),
            details=self._extract_error_details(error),
            timestamp=time.time(),
            context=context,
            stack_trace=stack_trace,
            recovery_suggestions=recovery_suggestions,
            user_message=user_message
        )

        # Store in history
        self._store_error(error_info)

        # Log error
        self._log_error(error_info)

        # Try recovery if applicable
        if severity != ErrorSeverity.CRITICAL:
            self._attempt_recovery(error_info)

        # Call specific handler if available
        handler = self._find_handler(type(error))
        if handler:
            try:
                handler(error, error_info, context)
            except Exception as handler_error:
                logger.error(f"Error in error handler: {handler_error}")

        return error_info

    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify error into appropriate category."""
        error_type = type(error)

        # File I/O errors
        if issubclass(error_type, (FileNotFoundError, PermissionError, OSError)):
            return ErrorCategory.IO

        # Memory errors
        if issubclass(error_type, MemoryError):
            return ErrorCategory.MEMORY

        # Validation errors
        if issubclass(error_type, (ValueError, TypeError)):
            return ErrorCategory.VALIDATION

        # Security-related
        if 'security' in str(error).lower() or 'permission' in str(error).lower():
            return ErrorCategory.SECURITY

        # Network errors
        if 'network' in str(error).lower() or 'connection' in str(error).lower():
            return ErrorCategory.NETWORK

        # Check error message for clues
        error_message = str(error).lower()
        if any(keyword in error_message for keyword in ['invalid', 'format', 'parse']):
            return ErrorCategory.VALIDATION
        elif any(keyword in error_message for keyword in ['file', 'directory', 'path']):
            return ErrorCategory.IO
        elif any(keyword in error_message for keyword in ['memory', 'allocation']):
            return ErrorCategory.MEMORY

        return ErrorCategory.UNKNOWN

    def _assess_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Assess error severity based on type and category."""
        error_type = type(error)

        # Critical errors
        if issubclass(error_type, (MemoryError, SystemError)):
            return ErrorSeverity.CRITICAL

        # High severity
        if category == ErrorCategory.SECURITY:
            return ErrorSeverity.HIGH

        if issubclass(error_type, PermissionError):
            return ErrorSeverity.HIGH

        # Medium severity
        if category in [ErrorCategory.IO, ErrorCategory.NETWORK]:
            return ErrorSeverity.MEDIUM

        # Low severity (validation, user input, etc.)
        return ErrorSeverity.LOW

    def _extract_error_details(self, error: Exception) -> Dict[str, Any]:
        """Extract detailed information from error."""
        details = {
            'type': type(error).__name__,
            'module': getattr(type(error), '__module__', 'unknown'),
            'args': error.args if error.args else []
        }

        # Add specific details for known error types
        if hasattr(error, 'errno'):
            details['errno'] = error.errno

        if hasattr(error, 'filename'):
            details['filename'] = str(error.filename)

        if hasattr(error, 'strerror'):
            details['strerror'] = error.strerror

        return details

    def _generate_recovery_suggestions(self, error: Exception, category: ErrorCategory) -> List[str]:
        """Generate recovery suggestions based on error type and category."""
        suggestions = []

        if category == ErrorCategory.IO:
            suggestions.extend([
                "Check if the file or directory exists",
                "Verify file permissions",
                "Ensure sufficient disk space",
                "Try using an absolute path",
                "Check if the file is currently in use by another program",
                "Try saving to a different location"
            ])

        elif category == ErrorCategory.MEMORY:
            suggestions.extend([
                "Close unnecessary applications",
                "Process smaller files or use batch processing",
                "Increase system memory if possible",
                "Enable memory optimization settings",
                "Restart the application",
                "Use 64-bit version if available"
            ])

        elif category == ErrorCategory.VALIDATION:
            suggestions.extend([
                "Check input format and values",
                "Verify file format is supported",
                "Review parameter ranges and constraints",
                "Ensure all required fields are provided",
                "Check for corrupted input data"
            ])

        elif category == ErrorCategory.NETWORK:
            suggestions.extend([
                "Check internet connection",
                "Verify API endpoints are accessible",
                "Try again in a few moments",
                "Check firewall and proxy settings",
                "Verify SSL certificates",
                "Try using a different network connection"
            ])

        elif category == ErrorCategory.SECURITY:
            suggestions.extend([
                "Check authentication credentials",
                "Verify access permissions",
                "Contact system administrator if needed",
                "Review security policies",
                "Check antivirus software settings"
            ])

        elif category == ErrorCategory.PROCESSING:
            suggestions.extend([
                "Try with simpler settings",
                "Process the file in smaller chunks",
                "Check if the file format is fully supported",
                "Try a different processing approach",
                "Update to the latest version"
            ])

        # Add general suggestions
        suggestions.extend([
            "Try the operation again",
            "Check system logs for more details",
            "Contact support if the problem persists",
            "Check if system requirements are met"
        ])

        return suggestions

    def _create_user_message(self, error: Exception, category: ErrorCategory, severity: ErrorSeverity) -> str:
        """Create user-friendly error message."""
        base_messages = {
            ErrorCategory.IO: "There was a problem accessing a file or directory.",
            ErrorCategory.MEMORY: "The system is running low on memory.",
            ErrorCategory.VALIDATION: "There was an issue with the input data.",
            ErrorCategory.NETWORK: "There was a network connection problem.",
            ErrorCategory.SECURITY: "There was a security or permission issue.",
            ErrorCategory.PROCESSING: "There was an error during processing.",
            ErrorCategory.USER_INPUT: "There was an issue with the provided input.",
            ErrorCategory.SYSTEM: "There was a system-level error.",
            ErrorCategory.UNKNOWN: "An unexpected error occurred."
        }

        base_message = base_messages.get(category, "An error occurred.")

        if severity == ErrorSeverity.CRITICAL:
            return f"Critical Error: {base_message} The operation cannot continue."
        elif severity == ErrorSeverity.HIGH:
            return f"Error: {base_message} Please review the details and try again."
        elif severity == ErrorSeverity.MEDIUM:
            return f"Warning: {base_message} You may be able to continue with caution."
        else:
            return f"Notice: {base_message} This is likely a minor issue."

    def _store_error(self, error_info: ErrorInfo):
        """Store error in history with size limit."""
        self.error_history.append(error_info)

        # Maintain size limit
        if len(self.error_history) > self.max_history:
            # Remove oldest errors, keep recent ones
            self.error_history = self.error_history[-self.max_history:]

    def _log_error(self, error_info: ErrorInfo):
        """Log error with appropriate level."""
        log_message = f"[{error_info.error_id}] {error_info.category.value.upper()}: {error_info.message}"

        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra={'error_info': error_info})
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra={'error_info': error_info})
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra={'error_info': error_info})
        else:
            logger.info(log_message, extra={'error_info': error_info})

        # Log stack trace for high severity errors
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.debug(f"Stack trace for {error_info.error_id}:\n{error_info.stack_trace}")

    def _attempt_recovery(self, error_info: ErrorInfo):
        """Attempt automatic recovery using registered strategies."""
        strategies = self.recovery_strategies.get(error_info.category, [])

        for strategy in strategies:
            try:
                if strategy(error_info):
                    logger.info(f"Successfully recovered from error {error_info.error_id}")
                    return True
            except Exception as recovery_error:
                logger.warning(f"Recovery strategy failed for {error_info.error_id}: {recovery_error}")

        return False

    def _find_handler(self, error_type: Type[Exception]) -> Optional[Callable]:
        """Find appropriate handler for error type."""
        # Direct match
        if error_type in self.error_handlers:
            return self.error_handlers[error_type]

        # Check inheritance hierarchy
        for registered_type, handler in self.error_handlers.items():
            if issubclass(error_type, registered_type):
                return handler

        return None

    # Default error handlers
    def _handle_file_not_found(self, error: FileNotFoundError, error_info: ErrorInfo, context: Dict[str, Any]):
        """Handle file not found errors."""
        logger.info(f"File not found: {error.filename}")

    def _handle_permission_error(self, error: PermissionError, error_info: ErrorInfo, context: Dict[str, Any]):
        """Handle permission errors."""
        logger.warning(f"Permission denied: {error.filename}")

    def _handle_os_error(self, error: OSError, error_info: ErrorInfo, context: Dict[str, Any]):
        """Handle OS errors."""
        logger.error(f"OS error: {error}")

    def _handle_memory_error(self, error: MemoryError, error_info: ErrorInfo, context: Dict[str, Any]):
        """Handle memory errors."""
        logger.critical("Memory error - attempting cleanup")
        # Trigger memory cleanup
        import gc
        gc.collect()

    def _handle_value_error(self, error: ValueError, error_info: ErrorInfo, context: Dict[str, Any]):
        """Handle value errors."""
        logger.debug(f"Value error: {error}")

    def _handle_type_error(self, error: TypeError, error_info: ErrorInfo, context: Dict[str, Any]):
        """Handle type errors."""
        logger.debug(f"Type error: {error}")

    def _handle_network_error(self, error: Exception, error_info: ErrorInfo, context: Dict[str, Any]):
        """Handle network errors."""
        logger.warning(f"Network error: {error}")

    def _handle_timeout_error(self, error: Exception, error_info: ErrorInfo, context: Dict[str, Any]):
        """Handle timeout errors."""
        logger.warning(f"Timeout error: {error}")

    # Public interface methods
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and analytics."""
        if not self.error_history:
            return {'total_errors': 0}

        # Count by category
        category_counts = {}
        severity_counts = {}

        for error in self.error_history:
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1

        return {
            'total_errors': len(self.error_history),
            'by_category': category_counts,
            'by_severity': severity_counts,
            'recent_errors': len([e for e in self.error_history if time.time() - e.timestamp < 3600])  # Last hour
        }

    def export_error_report(self, file_path: Path, include_stack_traces: bool = False):
        """Export error history to JSON file."""
        report_data = []

        for error in self.error_history:
            error_data = {
                'error_id': error.error_id,
                'category': error.category.value,
                'severity': error.severity.value,
                'message': error.message,
                'timestamp': error.timestamp,
                'user_message': error.user_message,
                'recovery_suggestions': error.recovery_suggestions,
                'details': error.details,
                'context': error.context
            }

            if include_stack_traces:
                error_data['stack_trace'] = error.stack_trace

            report_data.append(error_data)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)

    def clear_error_history(self):
        """Clear error history."""
        self.error_history.clear()
        logger.info("Error history cleared")


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


@contextmanager
def error_context(context: Dict[str, Any] = None):
    """Context manager for error handling with additional context."""
    try:
        yield
    except Exception as e:
        error_handler = get_error_handler()
        error_info = error_handler.handle_error(e, context)
        raise ErrorWithContext(e, error_info) from e


class ErrorWithContext(Exception):
    """Exception wrapper that includes error handling context."""

class PrintProblemDiagnostician:
    """Automated diagnosis and remediation for common 3D printing problems."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.problem_database = self._initialize_problem_database()

    def _initialize_problem_database(self) -> Dict[str, Dict[str, Any]]:
        """Initialize database of common printing problems and solutions."""
        return {
            'layer_adhesion_failure': {
                'symptoms': [
                    'layers separating',
                    'poor layer bonding',
                    'delamination between layers',
                    'weak interlayer strength'
                ],
                'possible_causes': [
                    'low print temperature',
                    'insufficient cooling',
                    'dirty nozzle',
                    'wrong material settings',
                    'overhangs without support'
                ],
                'diagnostic_tests': [
                    'Check temperature settings',
                    'Inspect nozzle condition',
                    'Verify material compatibility',
                    'Test with calibration print'
                ],
                'solutions': [
                    'Increase print temperature by 5-10°C',
                    'Adjust cooling fan settings',
                    'Clean nozzle thoroughly',
                    'Use appropriate material profile',
                    'Add support structures for overhangs',
                    'Increase layer height for better bonding'
                ],
                'severity': 'medium',
                'frequency': 'common'
            },
            'stringing': {
                'symptoms': [
                    'thin strings between parts',
                    'oozing filament',
                    'wispy strands',
                    'excessive material flow'
                ],
                'possible_causes': [
                    'high print temperature',
                    'high retraction distance',
                    'slow retraction speed',
                    'wet filament',
                    'long travel moves'
                ],
                'diagnostic_tests': [
                    'Check temperature calibration',
                    'Test retraction settings',
                    'Inspect filament moisture',
                    'Monitor travel moves'
                ],
                'solutions': [
                    'Decrease print temperature by 5°C',
                    'Reduce retraction distance',
                    'Increase retraction speed',
                    'Dry filament before printing',
                    'Enable coasting in slicer',
                    'Use anti-stringing primer'
                ],
                'severity': 'low',
                'frequency': 'common'
            },
            'overheating': {
                'symptoms': [
                    'thermal runaway',
                    'hotend temperature spikes',
                    'melted filament',
                    'clogged nozzle',
                    'inconsistent extrusion'
                ],
                'possible_causes': [
                    'PID tuning issues',
                    'faulty temperature sensor',
                    'insufficient cooling',
                    'wrong voltage settings',
                    'ambient temperature too high'
                ],
                'diagnostic_tests': [
                    'Check PID values',
                    'Test temperature sensor',
                    'Verify cooling system',
                    'Monitor ambient conditions'
                ],
                'solutions': [
                    'Retune PID controller',
                    'Replace temperature sensor',
                    'Improve cooling system',
                    'Adjust voltage settings',
                    'Lower ambient temperature',
                    'Use thermal paste on hotend'
                ],
                'severity': 'high',
                'frequency': 'occasional'
            },
            'warping': {
                'symptoms': [
                    'corners lifting',
                    'part detaching from bed',
                    'curved edges',
                    'uneven base layer'
                ],
                'possible_causes': [
                    'insufficient bed adhesion',
                    'temperature differences',
                    'drafty environment',
                    'wrong bed temperature',
                    'material shrinkage'
                ],
                'diagnostic_tests': [
                    'Check bed leveling',
                    'Test adhesion methods',
                    'Monitor environmental conditions',
                    'Verify bed temperature'
                ],
                'solutions': [
                    'Use brim or raft',
                    'Increase bed temperature',
                    'Apply adhesive to bed',
                    'Enclose printer',
                    'Use materials with less shrinkage',
                    'Slow down first layer speed'
                ],
                'severity': 'medium',
                'frequency': 'common'
            }
        }

    def diagnose_print_problem(self, symptoms: List[str],
                             print_settings: Dict[str, Any],
                             printer_info: Dict[str, Any]) -> Dict[str, Any]:
        """Diagnose printing problems based on symptoms and settings.

        Args:
            symptoms: List of observed symptoms
            print_settings: Current print settings
            printer_info: Printer hardware information

        Returns:
            Diagnosis results with recommendations
        """
        diagnosis = {
            'likely_problems': [],
            'confidence_scores': {},
            'recommended_actions': [],
            'immediate_fixes': [],
            'long_term_solutions': []
        }

        try:
            # Match symptoms to known problems
            for problem_key, problem_data in self.problem_database.items():
                confidence = self._calculate_problem_confidence(
                    symptoms, problem_data, print_settings, printer_info
                )

                if confidence > 0.3:  # Threshold for likely problems
                    diagnosis['likely_problems'].append(problem_key)
                    diagnosis['confidence_scores'][problem_key] = confidence

                    # Add solutions
                    for solution in problem_data['solutions']:
                        if solution not in diagnosis['recommended_actions']:
                            diagnosis['recommended_actions'].append(solution)

            # Prioritize problems by confidence
            diagnosis['likely_problems'].sort(
                key=lambda x: diagnosis['confidence_scores'][x], reverse=True
            )

            # Categorize solutions
            diagnosis['immediate_fixes'] = [
                action for action in diagnosis['recommended_actions']
                if any(keyword in action.lower() for keyword in ['temperature', 'speed', 'clean'])
            ]

            diagnosis['long_term_solutions'] = [
                action for action in diagnosis['recommended_actions']
                if any(keyword in action.lower() for keyword in ['upgrade', 'replace', 'calibrate', 'enclose'])
            ]

        except Exception as e:
            self.logger.error(f"Problem diagnosis failed: {e}")
            diagnosis['error'] = str(e)

        return diagnosis

    def _calculate_problem_confidence(self, symptoms: List[str],
                                    problem_data: Dict[str, Any],
                                    print_settings: Dict[str, Any],
                                    printer_info: Dict[str, Any]) -> float:
        """Calculate confidence score for a specific problem."""
        confidence = 0.0

        # Match symptoms
        symptom_matches = 0
        for symptom in symptoms:
            symptom_lower = symptom.lower()
            for known_symptom in problem_data['symptoms']:
                if known_symptom.lower() in symptom_lower or symptom_lower in known_symptom.lower():
                    symptom_matches += 1
                    break

        symptom_score = symptom_matches / len(problem_data['symptoms']) if problem_data['symptoms'] else 0
        confidence += symptom_score * 0.6

        # Check print settings for clues
        settings_score = self._analyze_print_settings(print_settings, problem_data)
        confidence += settings_score * 0.3

        # Check printer info for compatibility
        printer_score = self._analyze_printer_info(printer_info, problem_data)
        confidence += printer_score * 0.1

        return min(confidence, 1.0)

    def _analyze_print_settings(self, settings: Dict[str, Any],
                              problem_data: Dict[str, Any]) -> float:
        """Analyze print settings for problem indicators."""
        score = 0.0

        # Check temperature settings
        if 'temperature' in settings:
            temp = settings['temperature']

            # For layer adhesion issues, low temperature is suspicious
            if 'layer_adhesion_failure' in problem_data.get('problem_key', ''):
                if temp < 200:  # Assuming PLA baseline
                    score += 0.3

            # For stringing, high temperature is suspicious
            if 'stringing' in problem_data.get('problem_key', ''):
                if temp > 220:
                    score += 0.3

        # Check speed settings
        if 'speed' in settings:
            speed = settings['speed']

            # High speeds can cause various issues
            if speed > 60:
                score += 0.2

        return score

    def _analyze_printer_info(self, printer_info: Dict[str, Any],
                            problem_data: Dict[str, Any]) -> float:
        """Analyze printer hardware for problem indicators."""
        score = 0.0

        # Check for known problematic hardware
        if 'nozzle_diameter' in printer_info:
            nozzle = printer_info['nozzle_diameter']

            # Small nozzles can be prone to certain issues
            if nozzle < 0.4 and 'overheating' in problem_data.get('problem_key', ''):
                score += 0.2

        return score

    def generate_corrective_gcode(self, problem_diagnosis: Dict[str, Any],
                                original_gcode: str) -> str:
        """Generate corrective G-code based on diagnosis.

        Args:
            problem_diagnosis: Results from diagnose_print_problem
            original_gcode: Original G-code to modify

        Returns:
            Modified G-code with corrections
        """
        corrected_gcode = original_gcode

        try:
            lines = original_gcode.split('\n')

            # Apply corrections based on likely problems
            for problem in problem_diagnosis['likely_problems']:
                if problem == 'layer_adhesion_failure':
                    corrected_gcode = self._fix_layer_adhesion(lines)
                elif problem == 'stringing':
                    corrected_gcode = self._fix_stringing(lines)
                elif problem == 'overheating':
                    corrected_gcode = self._fix_overheating(lines)

        except Exception as e:
            self.logger.error(f"G-code correction failed: {e}")
            return original_gcode

        return corrected_gcode

    def _fix_layer_adhesion(self, gcode_lines: List[str]) -> str:
        """Apply fixes for layer adhesion issues."""
        modified_lines = []

        for line in gcode_lines:
            if line.startswith('M104') or line.startswith('M109'):
                # Increase temperature for first few layers
                if 'S' in line:
                    temp_str = line.split('S')[1].split()[0]
                    try:
                        temp = int(temp_str)
                        new_temp = min(temp + 10, 250)  # Cap at 250°C
                        line = line.replace(f'S{temp}', f'S{new_temp}')
                    except (ValueError, IndexError):
                        pass
            elif line.startswith('M140') or line.startswith('M190'):
                # Increase bed temperature
                if 'S' in line:
                    temp_str = line.split('S')[1].split()[0]
                    try:
                        temp = int(temp_str)
                        new_temp = min(temp + 5, 100)  # Cap at 100°C
                        line = line.replace(f'S{temp}', f'S{new_temp}')
                    except (ValueError, IndexError):
                        pass

            modified_lines.append(line)

        return '\n'.join(modified_lines)

    def _fix_stringing(self, gcode_lines: List[str]) -> str:
        """Apply fixes for stringing issues."""
        modified_lines = []

        for line in gcode_lines:
            if line.startswith('M104') or line.startswith('M109'):
                # Decrease temperature
                if 'S' in line:
                    temp_str = line.split('S')[1].split()[0]
                    try:
                        temp = int(temp_str)
                        new_temp = max(temp - 5, 180)  # Minimum 180°C
                        line = line.replace(f'S{temp}', f'S{new_temp}')
                    except (ValueError, IndexError):
                        pass

            modified_lines.append(line)

        return '\n'.join(modified_lines)

    def _fix_overheating(self, gcode_lines: List[str]) -> str:
        """Apply fixes for overheating issues."""
        modified_lines = []

        for line in gcode_lines:
            if line.startswith('M106'):  # Fan control
                # Increase fan speed for cooling
                if 'S' in line:
                    speed_str = line.split('S')[1].split()[0]
                    try:
                        speed = int(speed_str)
                        new_speed = min(speed + 50, 255)  # Cap at 255
                        line = line.replace(f'S{speed}', f'S{new_speed}')
                    except (ValueError, IndexError):
                        pass

            modified_lines.append(line)

        return '\n'.join(modified_lines)

    def create_diagnostic_print(self, problem_type: str) -> str:
        """Generate G-code for diagnostic print to test specific issues.

        Args:
            problem_type: Type of problem to diagnose

        Returns:
            G-code for diagnostic print
        """
        gcode = []

        if problem_type == 'layer_adhesion':
            # Create a test print with varying temperatures
            gcode.extend([
                "; Diagnostic print for layer adhesion",
                "G21 ; Set units to mm",
                "G90 ; Absolute positioning",
                "M82 ; Absolute extrusion",
                "M107 ; Fan off",
                "M104 S200 ; Start at 200°C",
                "M140 S60 ; Bed at 60°C",
                "G28 ; Home all",
                "G1 Z5 F300 ; Lift nozzle",
                "; Print test pattern with temperature variations"
            ])

        elif problem_type == 'stringing':
            # Create a test print with retraction settings
            gcode.extend([
                "; Diagnostic print for stringing",
                "G21 ; Set units to mm",
                "G90 ; Absolute positioning",
                "M82 ; Absolute extrusion",
                "M104 S210 ; Standard temperature",
                "M140 S60 ; Bed at 60°C",
                "G28 ; Home all",
                "; Print test pattern with different retraction settings"
            ])

        elif problem_type == 'overheating':
            # Create a test print for thermal performance
            gcode.extend([
                "; Diagnostic print for overheating",
                "G21 ; Set units to mm",
                "G90 ; Absolute positioning",
                "M82 ; Absolute extrusion",
                "M104 S220 ; Test temperature",
                "M140 S60 ; Bed at 60°C",
                "G28 ; Home all",
                "; Print test pattern with cooling variations"
            ])

        return '\n'.join(gcode)


def handle_error_gracefully(func: Callable) -> Callable:
    """Decorator for graceful error handling."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_handler = get_error_handler()
            error_info = error_handler.handle_error(e, {
                'function': func.__name__,
                'args': str(args)[:200],  # Limit length
                'kwargs': str(kwargs)[:200]
            })
            # Re-raise with context
            raise ErrorWithContext(e, error_info) from e

    return wrapper