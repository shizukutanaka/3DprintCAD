"""Structured logging system for 3D print CAD assistant."""
from __future__ import annotations

import json
import logging
import logging.handlers
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union
import threading
from enum import Enum

from .config import get_config


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogContext:
    """Context information for structured logging."""
    session_id: str
    operation: str
    file_path: Optional[str] = None
    file_count: Optional[int] = None
    worker_id: Optional[str] = None
    batch_mode: bool = False
    parallel_mode: bool = False


@dataclass
class PerformanceMetrics:
    """Performance metrics for logging."""
    operation: str
    start_time: float
    end_time: float
    duration: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    file_size_mb: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ValidationLogEntry:
    """Validation result log entry."""
    file_path: str
    success: bool
    issue_count: int
    error_count: int
    warning_count: int
    processing_time: float
    validation_settings: Dict[str, Any]
    mesh_metrics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""

    def __init__(self, include_context: bool = True):
        super().__init__()
        self.include_context = include_context

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add context if available
        if self.include_context and hasattr(record, 'context'):
            log_entry["context"] = asdict(record.context)

        # Add performance metrics if available
        if hasattr(record, 'metrics'):
            log_entry["metrics"] = record.metrics.to_dict()

        # Add validation data if available
        if hasattr(record, 'validation_data'):
            log_entry["validation_data"] = record.validation_data.to_dict()

        # Add exception information
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class ContextualLogger:
    """Logger with automatic context injection."""

    def __init__(self, name: str, context: Optional[LogContext] = None):
        self.logger = logging.getLogger(name)
        self.context = context
        self._local = threading.local()

    def set_context(self, context: LogContext):
        """Set context for current thread."""
        self._local.context = context

    def get_context(self) -> Optional[LogContext]:
        """Get context for current thread."""
        return getattr(self._local, 'context', self.context)

    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with context."""
        extra = {}
        context = self.get_context()
        if context:
            extra['context'] = context

        # Add any additional data
        for key, value in kwargs.items():
            extra[key] = value

        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log_with_context(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)

    def log_performance(self, metrics: PerformanceMetrics):
        """Log performance metrics."""
        self._log_with_context(
            logging.INFO,
            f"Performance: {metrics.operation} completed in {metrics.duration:.2f}s",
            metrics=metrics
        )

    def log_validation(self, validation_data: ValidationLogEntry):
        """Log validation results."""
        status = "PASSED" if validation_data.success else "FAILED"
        self._log_with_context(
            logging.INFO,
            f"Validation {status}: {validation_data.file_path} "
            f"({validation_data.issue_count} issues in {validation_data.processing_time:.2f}s)",
            validation_data=validation_data
        )


class LoggingManager:
    """Central logging configuration and management."""

    def __init__(self):
        self.configured = False
        self.loggers = {}

    def configure_logging(
        self,
        level: Union[str, LogLevel] = LogLevel.INFO,
        enable_file_logging: bool = True,
        enable_json_logging: bool = True,
        log_directory: Optional[Path] = None,
        max_file_size_mb: int = 50,
        backup_count: int = 5
    ):
        """Configure structured logging system."""
        if self.configured:
            return

        # Convert level if needed
        if isinstance(level, LogLevel):
            level = level.value

        # Set root logger level
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper()))

        # Clear existing handlers
        root_logger.handlers.clear()

        # Console handler with readable format
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        if enable_file_logging:
            # Determine log directory
            if log_directory is None:
                config = get_config()
                log_directory = config.config_directory / "logs"

            log_directory.mkdir(parents=True, exist_ok=True)

            # Structured JSON log file
            if enable_json_logging:
                json_log_file = log_directory / "printcad_structured.log"
                json_handler = logging.handlers.RotatingFileHandler(
                    json_log_file,
                    maxBytes=max_file_size_mb * 1024 * 1024,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                json_handler.setFormatter(StructuredFormatter())
                root_logger.addHandler(json_handler)

            # Human-readable log file
            readable_log_file = log_directory / "printcad.log"
            file_handler = logging.handlers.RotatingFileHandler(
                readable_log_file,
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

        self.configured = True

    def get_logger(
        self,
        name: str,
        context: Optional[LogContext] = None
    ) -> ContextualLogger:
        """Get or create a contextual logger."""
        if name not in self.loggers:
            self.loggers[name] = ContextualLogger(name, context)
        return self.loggers[name]

    def create_context(
        self,
        session_id: str,
        operation: str,
        file_path: Optional[str] = None,
        file_count: Optional[int] = None,
        worker_id: Optional[str] = None,
        batch_mode: bool = False,
        parallel_mode: bool = False
    ) -> LogContext:
        """Create logging context."""
        return LogContext(
            session_id=session_id,
            operation=operation,
            file_path=file_path,
            file_count=file_count,
            worker_id=worker_id,
            batch_mode=batch_mode,
            parallel_mode=parallel_mode
        )


# Global logging manager instance
_logging_manager = LoggingManager()


def configure_logging(**kwargs):
    """Configure the global logging system."""
    _logging_manager.configure_logging(**kwargs)


def get_logger(name: str, context: Optional[LogContext] = None) -> ContextualLogger:
    """Get a contextual logger."""
    return _logging_manager.get_logger(name, context)


def create_context(**kwargs) -> LogContext:
    """Create a logging context."""
    return _logging_manager.create_context(**kwargs)


def measure_performance(operation: str):
    """Decorator for measuring and logging performance."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger = get_logger(func.__module__)

            try:
                result = func(*args, **kwargs)
                end_time = time.time()

                metrics = PerformanceMetrics(
                    operation=operation,
                    start_time=start_time,
                    end_time=end_time,
                    duration=end_time - start_time
                )

                logger.log_performance(metrics)
                return result

            except Exception as e:
                end_time = time.time()
                logger.error(
                    f"Performance: {operation} failed after {end_time - start_time:.2f}s: {str(e)}"
                )
                raise

        return wrapper
    return decorator


# Performance tracking utilities
def track_validation_performance(
    file_path: str,
    success: bool,
    issues: list,
    processing_time: float,
    settings: dict,
    metrics: Optional[dict] = None
):
    """Track validation performance and results."""
    logger = get_logger(__name__)

    error_count = len([i for i in issues if i.get('severity') == 'error'])
    warning_count = len([i for i in issues if i.get('severity') == 'warning'])

    validation_data = ValidationLogEntry(
        file_path=file_path,
        success=success,
        issue_count=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        processing_time=processing_time,
        validation_settings=settings,
        mesh_metrics=metrics
    )

    logger.log_validation(validation_data)


def setup_logging_from_config() -> None:
    """Setup logging configuration based on application config."""
    config = get_config()
    log_level = config.application.log_level.upper()
    log_to_file = config.application.log_to_file
    log_file_path = config.application.log_file_path

    # Create logger
    logger = logging.getLogger('printcad')
    logger.setLevel(getattr(logging, log_level))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_to_file:
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(getattr(logging, log_level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Set root logger level
def set_log_level(level: str) -> None:
    """Dynamically set the log level for all handlers."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger('printcad')
    logger.setLevel(numeric_level)
    
    for handler in logger.handlers:
        handler.setLevel(numeric_level)
    
    logging.getLogger().setLevel(numeric_level)