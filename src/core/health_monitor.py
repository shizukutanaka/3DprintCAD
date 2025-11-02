"""
Comprehensive health monitoring system for production deployment.

This module provides detailed health checks for all system components
including database, cache, storage, and application resources.
"""

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

import psutil

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "duration_ms": round(self.duration_ms, 2)
        }


@dataclass
class SystemHealth:
    """Overall system health status."""
    status: HealthStatus
    checks: List[HealthCheckResult]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    uptime_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "uptime_seconds": round(self.uptime_seconds, 2),
            "checks": [check.to_dict() for check in self.checks],
            "summary": {
                "healthy": sum(1 for c in self.checks if c.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for c in self.checks if c.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for c in self.checks if c.status == HealthStatus.UNHEALTHY),
                "unknown": sum(1 for c in self.checks if c.status == HealthStatus.UNKNOWN),
                "total": len(self.checks)
            }
        }


class HealthMonitor:
    """
    Comprehensive health monitoring system.

    Performs periodic health checks on all system components and provides
    detailed status information for monitoring and alerting.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize health monitor with configuration."""
        self.config = config or {}
        self.check_interval = self.config.get('health_check_interval', 30)  # seconds
        self.last_check = 0
        self.cache = {}
        self.cache_ttl = 60  # seconds
        self.start_time = time.time()
        self.checks: Dict[str, Callable[[], HealthCheckResult]] = {}
        self._register_default_checks()

    def _register_default_checks(self):
        """Register default health checks."""
        self.register_check("cpu", self.check_cpu)
        self.register_check("memory", self.check_memory)
        self.register_check("disk", self.check_disk)
        self.register_check("processes", self.check_processes)

    def register_check(self, name: str, check_func: Callable[[], HealthCheckResult]):
        """
        Register a custom health check.

        Args:
            name: Unique name for the health check
            check_func: Function that returns HealthCheckResult
        """
        self.checks[name] = check_func

    def check_cpu(self) -> HealthCheckResult:
        """Check CPU usage."""
        start = time.perf_counter()
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)

            if cpu_percent < 70:
                status = HealthStatus.HEALTHY
                message = "CPU usage is normal"
            elif cpu_percent < 90:
                status = HealthStatus.DEGRADED
                message = "CPU usage is elevated"
            else:
                status = HealthStatus.UNHEALTHY
                message = "CPU usage is critical"

            return HealthCheckResult(
                name="cpu",
                status=status,
                message=message,
                details={
                    "cpu_percent": round(cpu_percent, 2),
                    "cpu_count": psutil.cpu_count(),
                    "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
                },
                duration_ms=(time.perf_counter() - start) * 1000
            )
        except Exception as exc:
            logger.exception("CPU health check failed")
            return HealthCheckResult(
                name="cpu",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check CPU: {exc}",
                duration_ms=(time.perf_counter() - start) * 1000
            )

    def check_memory(self) -> HealthCheckResult:
        """Check memory usage."""
        start = time.perf_counter()
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            if memory.percent < 80:
                status = HealthStatus.HEALTHY
                message = "Memory usage is normal"
            elif memory.percent < 90:
                status = HealthStatus.DEGRADED
                message = "Memory usage is elevated"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Memory usage is critical"

            return HealthCheckResult(
                name="memory",
                status=status,
                message=message,
                details={
                    "memory_percent": round(memory.percent, 2),
                    "memory_used_gb": round(memory.used / (1024**3), 2),
                    "memory_total_gb": round(memory.total / (1024**3), 2),
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "swap_percent": round(swap.percent, 2),
                    "swap_used_gb": round(swap.used / (1024**3), 2)
                },
                duration_ms=(time.perf_counter() - start) * 1000
            )
        except Exception as exc:
            logger.exception("Memory health check failed")
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check memory: {exc}",
                duration_ms=(time.perf_counter() - start) * 1000
            )

    def check_disk(self) -> HealthCheckResult:
        """Check disk usage."""
        start = time.perf_counter()
        try:
            # Check all mounted partitions
            partitions_info = []
            max_usage_percent = 0.0
            critical_partitions = []

            for partition in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partition_data = {
                        "mountpoint": partition.mountpoint,
                        "device": partition.device,
                        "fstype": partition.fstype,
                        "percent": round(usage.percent, 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "total_gb": round(usage.total / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2)
                    }
                    partitions_info.append(partition_data)

                    if usage.percent > max_usage_percent:
                        max_usage_percent = usage.percent

                    if usage.percent >= 90:
                        critical_partitions.append(partition.mountpoint)
                except (PermissionError, OSError):
                    continue

            if max_usage_percent < 80:
                status = HealthStatus.HEALTHY
                message = "Disk usage is normal"
            elif max_usage_percent < 90:
                status = HealthStatus.DEGRADED
                message = "Disk usage is elevated"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Disk usage is critical on: {', '.join(critical_partitions)}"

            return HealthCheckResult(
                name="disk",
                status=status,
                message=message,
                details={
                    "max_usage_percent": round(max_usage_percent, 2),
                    "partitions": partitions_info,
                    "critical_partitions": critical_partitions
                },
                duration_ms=(time.perf_counter() - start) * 1000
            )
        except Exception as exc:
            logger.exception("Disk health check failed")
            return HealthCheckResult(
                name="disk",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check disk: {exc}",
                duration_ms=(time.perf_counter() - start) * 1000
            )

    def check_processes(self) -> HealthCheckResult:
        """Check process information."""
        start = time.perf_counter()
        try:
            current_process = psutil.Process()
            process_info = {
                "pid": current_process.pid,
                "memory_percent": round(current_process.memory_percent(), 2),
                "memory_rss_mb": round(current_process.memory_info().rss / (1024**2), 2),
                "num_threads": current_process.num_threads(),
                "num_fds": current_process.num_fds() if hasattr(current_process, 'num_fds') else None,
                "cpu_percent": round(current_process.cpu_percent(interval=0.1), 2),
                "create_time": datetime.fromtimestamp(
                    current_process.create_time(), tz=timezone.utc
                ).isoformat()
            }

            # Check for resource exhaustion
            if process_info["memory_percent"] < 80:
                status = HealthStatus.HEALTHY
                message = "Process resources are normal"
            elif process_info["memory_percent"] < 90:
                status = HealthStatus.DEGRADED
                message = "Process memory usage is elevated"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Process memory usage is critical"

            return HealthCheckResult(
                name="processes",
                status=status,
                message=message,
                details=process_info,
                duration_ms=(time.perf_counter() - start) * 1000
            )
        except Exception as exc:
            logger.exception("Process health check failed")
            return HealthCheckResult(
                name="processes",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check processes: {exc}",
                duration_ms=(time.perf_counter() - start) * 1000
            )

    def check_database(self, connection_func: Callable[[], bool]) -> HealthCheckResult:
        """
        Check database connectivity.

        Args:
            connection_func: Function that returns True if database is accessible
        """
        start = time.perf_counter()
        try:
            if connection_func():
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Database is accessible",
                    duration_ms=(time.perf_counter() - start) * 1000
                )
            else:
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message="Database is not accessible",
                    duration_ms=(time.perf_counter() - start) * 1000
                )
        except Exception as exc:
            logger.exception("Database health check failed")
            return HealthCheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database check failed: {exc}",
                duration_ms=(time.perf_counter() - start) * 1000
            )

    def check_cache(self, ping_func: Callable[[], bool]) -> HealthCheckResult:
        """
        Check cache (Redis) connectivity.

        Args:
            ping_func: Function that returns True if cache is accessible
        """
        start = time.perf_counter()
        try:
            if ping_func():
                return HealthCheckResult(
                    name="cache",
                    status=HealthStatus.HEALTHY,
                    message="Cache is accessible",
                    duration_ms=(time.perf_counter() - start) * 1000
                )
            else:
                return HealthCheckResult(
                    name="cache",
                    status=HealthStatus.UNHEALTHY,
                    message="Cache is not accessible",
                    duration_ms=(time.perf_counter() - start) * 1000
                )
        except Exception as exc:
            logger.exception("Cache health check failed")
            return HealthCheckResult(
                name="cache",
                status=HealthStatus.UNHEALTHY,
                message=f"Cache check failed: {exc}",
                duration_ms=(time.perf_counter() - start) * 1000
            )

    def check_storage(self, directories: List[Path]) -> HealthCheckResult:
        """
        Check storage directories availability and permissions.

        Args:
            directories: List of directories to check
        """
        start = time.perf_counter()
        try:
            issues = []
            for directory in directories:
                if not directory.exists():
                    issues.append(f"{directory} does not exist")
                elif not directory.is_dir():
                    issues.append(f"{directory} is not a directory")
                elif not os.access(directory, os.W_OK):
                    issues.append(f"{directory} is not writable")

            if not issues:
                return HealthCheckResult(
                    name="storage",
                    status=HealthStatus.HEALTHY,
                    message="All storage directories are accessible",
                    details={"directories": [str(d) for d in directories]},
                    duration_ms=(time.perf_counter() - start) * 1000
                )
            else:
                return HealthCheckResult(
                    name="storage",
                    status=HealthStatus.UNHEALTHY,
                    message="Storage issues detected",
                    details={"issues": issues},
                    duration_ms=(time.perf_counter() - start) * 1000
                )
        except Exception as exc:
            logger.exception("Storage health check failed")
            return HealthCheckResult(
                name="storage",
                status=HealthStatus.UNKNOWN,
                message=f"Storage check failed: {exc}",
                duration_ms=(time.perf_counter() - start) * 1000
            )

    def run_all_checks(self) -> SystemHealth:
        """
        Run all registered health checks.

        Returns:
            SystemHealth object with all check results
        """
        results = []

        for name, check_func in self.checks.items():
            try:
                result = check_func()
                results.append(result)
            except Exception as exc:
                logger.exception(f"Health check '{name}' raised an exception")
                results.append(HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Check failed with exception: {exc}"
                ))

        # Determine overall status
        if all(r.status == HealthStatus.HEALTHY for r in results):
            overall_status = HealthStatus.HEALTHY
        elif any(r.status == HealthStatus.UNHEALTHY for r in results):
            overall_status = HealthStatus.UNHEALTHY
        elif any(r.status == HealthStatus.DEGRADED for r in results):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNKNOWN

        return SystemHealth(
            status=overall_status,
            checks=results,
            uptime_seconds=time.time() - self.start_time
        )


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get or create global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor
