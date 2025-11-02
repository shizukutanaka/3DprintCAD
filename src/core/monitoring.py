"""Enterprise monitoring and health check system."""
from __future__ import annotations

import time
import psutil
import asyncio
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import json
import logging
import statistics

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"


@dataclass
class HealthCheck:
    """Health check definition."""
    name: str
    check_fn: Callable[[], bool]
    interval_seconds: int = 60
    timeout_seconds: int = 10
    critical: bool = False
    last_check: Optional[datetime] = None
    last_status: Optional[bool] = None
    consecutive_failures: int = 0


@dataclass
class Metric:
    """Performance metric."""
    name: str
    type: MetricType
    value: float
    unit: str
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class Alert:
    """System alert."""
    id: str
    severity: str
    title: str
    message: str
    timestamp: datetime
    source: str
    resolved: bool = False
    acknowledged: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class SystemMonitor:
    """Comprehensive system monitoring and health management."""

    def __init__(self):
        """Initialize system monitor."""
        self.health_checks: Dict[str, HealthCheck] = {}
        self.metrics: Dict[str, List[Metric]] = {}
        self.alerts: List[Alert] = []
        self.alert_handlers: List[Callable[[Alert], None]] = []

        # Monitoring state
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Performance tracking
        self.request_times: List[float] = []
        self.error_counts: Dict[str, int] = {}

        # System info cache
        self._system_info_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None

        # Initialize default health checks
        self._setup_default_health_checks()

    def _setup_default_health_checks(self):
        """Setup default system health checks."""

        # CPU health check
        self.register_health_check(
            name="cpu_usage",
            check_fn=lambda: psutil.cpu_percent(interval=1) < 90,
            interval_seconds=30,
            critical=True
        )

        # Memory health check
        self.register_health_check(
            name="memory_usage",
            check_fn=lambda: psutil.virtual_memory().percent < 85,
            interval_seconds=30,
            critical=True
        )

        # Disk space health check
        self.register_health_check(
            name="disk_space",
            check_fn=lambda: psutil.disk_usage('/').percent < 90,
            interval_seconds=60
        )

        # Database connectivity (placeholder)
        self.register_health_check(
            name="database",
            check_fn=self._check_database,
            interval_seconds=30,
            critical=True
        )

        # API response time
        self.register_health_check(
            name="api_latency",
            check_fn=lambda: self.get_average_response_time() < 1000,  # < 1 second
            interval_seconds=60
        )

    def register_health_check(
        self,
        name: str,
        check_fn: Callable[[], bool],
        interval_seconds: int = 60,
        timeout_seconds: int = 10,
        critical: bool = False
    ):
        """Register a health check.

        Args:
            name: Health check name
            check_fn: Function that returns True if healthy
            interval_seconds: Check interval
            timeout_seconds: Check timeout
            critical: Whether this is a critical check
        """
        self.health_checks[name] = HealthCheck(
            name=name,
            check_fn=check_fn,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
            critical=critical
        )

    def start_monitoring(self):
        """Start monitoring system."""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("System monitoring started")

    def stop_monitoring(self):
        """Stop monitoring system."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("System monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Run health checks
                self._run_health_checks()

                # Collect metrics
                self._collect_system_metrics()

                # Check for alert conditions
                self._check_alert_conditions()

                # Cleanup old data
                self._cleanup_old_data()

                # Sleep before next iteration
                time.sleep(10)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

    def _run_health_checks(self):
        """Run all registered health checks."""
        current_time = datetime.now()

        for name, check in self.health_checks.items():
            # Check if it's time to run this check
            if check.last_check:
                time_since_last = (current_time - check.last_check).total_seconds()
                if time_since_last < check.interval_seconds:
                    continue

            # Run check with timeout
            try:
                result = self._run_with_timeout(
                    check.check_fn,
                    check.timeout_seconds
                )

                # Update check status
                check.last_check = current_time
                check.last_status = result

                if result:
                    check.consecutive_failures = 0
                else:
                    check.consecutive_failures += 1

                    # Create alert if needed
                    if check.consecutive_failures >= 3:
                        self._create_health_alert(check)

            except Exception as e:
                logger.error(f"Health check '{name}' failed: {e}")
                check.consecutive_failures += 1

    def _run_with_timeout(self, func: Callable, timeout: int) -> Any:
        """Run function with timeout."""
        result = [None]
        exception = [None]

        def wrapper():
            try:
                result[0] = func()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=wrapper)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            raise TimeoutError(f"Function timed out after {timeout} seconds")

        if exception[0]:
            raise exception[0]

        return result[0]

    def _collect_system_metrics(self):
        """Collect system performance metrics."""
        timestamp = datetime.now()

        # CPU metrics
        self.record_metric(
            name="system.cpu.usage",
            type=MetricType.GAUGE,
            value=psutil.cpu_percent(interval=1),
            unit="percent",
            description="CPU usage percentage"
        )

        # Memory metrics
        memory = psutil.virtual_memory()
        self.record_metric(
            name="system.memory.usage",
            type=MetricType.GAUGE,
            value=memory.percent,
            unit="percent",
            description="Memory usage percentage"
        )
        self.record_metric(
            name="system.memory.available",
            type=MetricType.GAUGE,
            value=memory.available / (1024 * 1024 * 1024),
            unit="GB",
            description="Available memory"
        )

        # Disk metrics
        disk = psutil.disk_usage('/')
        self.record_metric(
            name="system.disk.usage",
            type=MetricType.GAUGE,
            value=disk.percent,
            unit="percent",
            description="Disk usage percentage"
        )
        self.record_metric(
            name="system.disk.free",
            type=MetricType.GAUGE,
            value=disk.free / (1024 * 1024 * 1024),
            unit="GB",
            description="Free disk space"
        )

        # Network metrics
        net_io = psutil.net_io_counters()
        self.record_metric(
            name="system.network.bytes_sent",
            type=MetricType.COUNTER,
            value=net_io.bytes_sent,
            unit="bytes",
            description="Total bytes sent"
        )
        self.record_metric(
            name="system.network.bytes_recv",
            type=MetricType.COUNTER,
            value=net_io.bytes_recv,
            unit="bytes",
            description="Total bytes received"
        )

        # Process metrics
        process = psutil.Process()
        self.record_metric(
            name="process.cpu.percent",
            type=MetricType.GAUGE,
            value=process.cpu_percent(),
            unit="percent",
            description="Process CPU usage"
        )
        self.record_metric(
            name="process.memory.rss",
            type=MetricType.GAUGE,
            value=process.memory_info().rss / (1024 * 1024),
            unit="MB",
            description="Process memory usage"
        )
        self.record_metric(
            name="process.threads",
            type=MetricType.GAUGE,
            value=process.num_threads(),
            unit="count",
            description="Number of threads"
        )

    def record_metric(
        self,
        name: str,
        type: MetricType,
        value: float,
        unit: str = "",
        labels: Optional[Dict[str, str]] = None,
        description: str = ""
    ):
        """Record a metric value.

        Args:
            name: Metric name
            type: Metric type
            value: Metric value
            unit: Unit of measurement
            labels: Metric labels
            description: Metric description
        """
        metric = Metric(
            name=name,
            type=type,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            labels=labels or {},
            description=description
        )

        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append(metric)

        # Keep only recent metrics (last hour)
        cutoff = datetime.now() - timedelta(hours=1)
        self.metrics[name] = [
            m for m in self.metrics[name]
            if m.timestamp > cutoff
        ]

    def record_request(self, duration_ms: float):
        """Record API request duration.

        Args:
            duration_ms: Request duration in milliseconds
        """
        self.request_times.append(duration_ms)

        # Keep only last 1000 requests
        if len(self.request_times) > 1000:
            self.request_times = self.request_times[-1000:]

        self.record_metric(
            name="api.request.duration",
            type=MetricType.HISTOGRAM,
            value=duration_ms,
            unit="ms",
            description="API request duration"
        )

    def record_error(self, error_type: str):
        """Record an error occurrence.

        Args:
            error_type: Type of error
        """
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1

        self.record_metric(
            name="errors.count",
            type=MetricType.COUNTER,
            value=1,
            unit="count",
            labels={"type": error_type},
            description="Error count"
        )

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status.

        Returns:
            Health status dictionary
        """
        # Check all health checks
        all_healthy = True
        degraded = False
        critical_failure = False

        check_results = {}
        for name, check in self.health_checks.items():
            if check.last_status is False:
                all_healthy = False
                if check.critical:
                    critical_failure = True
                else:
                    degraded = True

            check_results[name] = {
                "status": "healthy" if check.last_status else "unhealthy",
                "last_check": check.last_check.isoformat() if check.last_check else None,
                "consecutive_failures": check.consecutive_failures
            }

        # Determine overall status
        if critical_failure:
            overall_status = HealthStatus.CRITICAL
        elif not all_healthy and degraded:
            overall_status = HealthStatus.DEGRADED
        elif not all_healthy:
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "checks": check_results,
            "metrics": self._get_current_metrics(),
            "alerts": self._get_active_alerts()
        }

    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current metric values."""
        current_metrics = {}

        for name, metric_list in self.metrics.items():
            if metric_list:
                latest = metric_list[-1]
                current_metrics[name] = {
                    "value": latest.value,
                    "unit": latest.unit,
                    "timestamp": latest.timestamp.isoformat()
                }

        # Add computed metrics
        current_metrics["api.request.avg_duration"] = {
            "value": self.get_average_response_time(),
            "unit": "ms",
            "timestamp": datetime.now().isoformat()
        }

        current_metrics["errors.total"] = {
            "value": sum(self.error_counts.values()),
            "unit": "count",
            "timestamp": datetime.now().isoformat()
        }

        return current_metrics

    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active (unresolved) alerts."""
        active_alerts = [
            {
                "id": alert.id,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "acknowledged": alert.acknowledged
            }
            for alert in self.alerts
            if not alert.resolved
        ]

        return active_alerts

    def get_average_response_time(self) -> float:
        """Get average API response time.

        Returns:
            Average response time in milliseconds
        """
        if not self.request_times:
            return 0.0
        return statistics.mean(self.request_times)

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information.

        Returns:
            System information dictionary
        """
        # Cache system info for 5 minutes
        if self._system_info_cache and self._cache_timestamp:
            if (datetime.now() - self._cache_timestamp).seconds < 300:
                return self._system_info_cache

        import platform

        system_info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "total_memory_gb": psutil.virtual_memory().total / (1024 ** 3),
            "total_disk_gb": psutil.disk_usage('/').total / (1024 ** 3),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }

        self._system_info_cache = system_info
        self._cache_timestamp = datetime.now()

        return system_info

    def create_alert(
        self,
        severity: str,
        title: str,
        message: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a system alert.

        Args:
            severity: Alert severity (info/warning/error/critical)
            title: Alert title
            message: Alert message
            source: Alert source
            metadata: Additional metadata

        Returns:
            Alert ID
        """
        import uuid

        alert = Alert(
            id=str(uuid.uuid4()),
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.now(),
            source=source,
            metadata=metadata or {}
        )

        self.alerts.append(alert)

        # Trigger alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

        # Keep only last 1000 alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]

        return alert.id

    def _create_health_alert(self, check: HealthCheck):
        """Create alert for failed health check."""
        severity = "critical" if check.critical else "warning"

        self.create_alert(
            severity=severity,
            title=f"Health check '{check.name}' failed",
            message=f"Health check has failed {check.consecutive_failures} consecutive times",
            source="health_monitor",
            metadata={
                "check_name": check.name,
                "consecutive_failures": check.consecutive_failures,
                "critical": check.critical
            }
        )

    def _check_alert_conditions(self):
        """Check for alert conditions."""
        # High CPU usage
        cpu_metrics = self.metrics.get("system.cpu.usage", [])
        if cpu_metrics:
            recent_cpu = [m.value for m in cpu_metrics[-5:]]
            if recent_cpu and all(v > 90 for v in recent_cpu):
                self.create_alert(
                    severity="warning",
                    title="High CPU usage",
                    message=f"CPU usage has been above 90% for the last 5 checks",
                    source="monitoring"
                )

        # High memory usage
        mem_metrics = self.metrics.get("system.memory.usage", [])
        if mem_metrics:
            recent_mem = [m.value for m in mem_metrics[-5:]]
            if recent_mem and all(v > 85 for v in recent_mem):
                self.create_alert(
                    severity="warning",
                    title="High memory usage",
                    message=f"Memory usage has been above 85% for the last 5 checks",
                    source="monitoring"
                )

        # High error rate
        error_rate = self._calculate_error_rate()
        if error_rate > 0.05:  # 5% error rate
            self.create_alert(
                severity="error",
                title="High error rate",
                message=f"Error rate is {error_rate:.1%}",
                source="monitoring"
            )

    def _calculate_error_rate(self) -> float:
        """Calculate current error rate."""
        total_requests = len(self.request_times)
        total_errors = sum(self.error_counts.values())

        if total_requests == 0:
            return 0.0

        return total_errors / (total_requests + total_errors)

    def _check_database(self) -> bool:
        """Check database connectivity."""
        # Placeholder - would check actual database connection
        return True

    def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        cutoff = datetime.now() - timedelta(hours=24)

        # Clean old alerts
        self.alerts = [
            alert for alert in self.alerts
            if alert.timestamp > cutoff or not alert.resolved
        ]

    def register_alert_handler(self, handler: Callable[[Alert], None]):
        """Register an alert handler.

        Args:
            handler: Function to handle alerts
        """
        self.alert_handlers.append(handler)

    def export_metrics(self, format: str = "prometheus") -> str:
        """Export metrics in specified format.

        Args:
            format: Export format (prometheus/json)

        Returns:
            Exported metrics string
        """
        if format == "prometheus":
            lines = []
            for name, metric_list in self.metrics.items():
                if metric_list:
                    latest = metric_list[-1]
                    # Convert metric name to Prometheus format
                    prom_name = name.replace(".", "_")
                    lines.append(f"# HELP {prom_name} {latest.description}")
                    lines.append(f"# TYPE {prom_name} {latest.type.value}")

                    if latest.labels:
                        label_str = ",".join(f'{k}="{v}"' for k, v in latest.labels.items())
                        lines.append(f"{prom_name}{{{label_str}}} {latest.value}")
                    else:
                        lines.append(f"{prom_name} {latest.value}")

            return "\n".join(lines)

        elif format == "json":
            export_data = {}
            for name, metric_list in self.metrics.items():
                export_data[name] = [
                    {
                        "value": m.value,
                        "timestamp": m.timestamp.isoformat(),
                        "labels": m.labels
                    }
                    for m in metric_list
                ]
            return json.dumps(export_data, indent=2)

        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global monitor instance
_system_monitor: Optional[SystemMonitor] = None


def get_system_monitor() -> SystemMonitor:
    """Get global system monitor instance."""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = AdvancedSystemMonitor()  # Use AdvancedSystemMonitor instead
        _system_monitor.start_monitoring()
    return _system_monitor


class LiveCameraMonitor:
    """Live camera streaming and print quality assessment."""

    def __init__(self, system_monitor: SystemMonitor):
        self.system_monitor = system_monitor
        self.logger = logging.getLogger(__name__)
        self.active_streams = {}
        self.camera_settings = {
            'resolution': '640x480',
            'fps': 10,
            'quality': 80,
            'detection_enabled': True
        }

    # ... (rest of the LiveCameraMonitor class remains the same)


class AdvancedErrorDetection:
    """Advanced error detection system for 3D printing."""

    def __init__(self, system_monitor: SystemMonitor):
        self.system_monitor = system_monitor
        self.logger = logging.getLogger(__name__)
        self.detection_models = self._initialize_detection_models()
        self.error_patterns = self._initialize_error_patterns()

    # ... (rest of the AdvancedErrorDetection class remains the same)


# Enhanced SystemMonitor with camera and error detection
class AdvancedSystemMonitor(SystemMonitor):
    """Advanced system monitor with camera and error detection capabilities."""

    def __init__(self):
        super().__init__()
        self.camera_monitor = LiveCameraMonitor(self)
        self.error_detector = AdvancedErrorDetection(self)

    def start_camera_monitoring(self, job_id: str, camera_url: str = None) -> bool:
        """Start camera monitoring for a job."""
        return self.camera_monitor.start_camera_stream(job_id, camera_url)

    def stop_camera_monitoring(self, job_id: str) -> Dict[str, Any]:
        """Stop camera monitoring for a job."""
        return self.camera_monitor.stop_camera_stream(job_id)

    def analyze_print_errors(self, job_id: str, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze print data for errors."""
        return self.error_detector.analyze_print_data(job_id, sensor_data)

    def get_camera_quality_history(self, job_id: str, count: int = 50) -> List[float]:
        """Get camera quality history for a job."""
        return self.camera_monitor.get_stream_quality_history(job_id, count)


class PrintJobMonitor:
    """Monitor specific print jobs for errors and anomalies."""

    def __init__(self, system_monitor: SystemMonitor):
        self.system_monitor = system_monitor
        self.logger = logging.getLogger(__name__)
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.job_anomalies: Dict[str, List[Dict[str, Any]]] = {}

    def start_job_monitoring(self, job_id: str, job_info: Dict[str, Any]) -> bool:
        """Start monitoring a specific print job."""
        try:
            self.active_jobs[job_id] = {
                'start_time': time.time(),
                'job_info': job_info,
                'last_progress': 0.0,
                'anomalies_detected': 0,
                'status': 'active',
                'last_update_time': time.time()
            }

            self.job_anomalies[job_id] = []

            self.logger.info(f"Started monitoring print job {job_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start job monitoring: {e}")
            return False

    def update_job_progress(self, job_id: str, progress: float, status: str = None) -> bool:
        """Update print job progress and check for anomalies."""
        if job_id not in self.active_jobs:
            return False

        try:
            job_data = self.active_jobs[job_id]
            job_data['last_progress'] = progress

            if status:
                job_data['status'] = status

            # Check for anomalies
            self._check_job_anomalies(job_id, progress, status)

            return True

        except Exception as e:
            self.logger.error(f"Failed to update job progress: {e}")
            return False

    def stop_job_monitoring(self, job_id: str, final_status: str = 'completed') -> Dict[str, Any]:
        """Stop monitoring a print job and return summary."""
        if job_id not in self.active_jobs:
            return {}

        try:
            job_data = self.active_jobs[job_id]
            job_data['end_time'] = time.time()
            job_data['status'] = final_status

            # Calculate job statistics
            duration = job_data['end_time'] - job_data['start_time']
            anomalies = self.job_anomalies.get(job_id, [])

            summary = {
                'job_id': job_id,
                'duration': duration,
                'final_progress': job_data['last_progress'],
                'final_status': final_status,
                'anomalies_detected': len(anomalies),
                'anomaly_details': anomalies,
                'average_progress_rate': job_data['last_progress'] / max(duration / 3600, 0.001)  # per hour
            }

            # Clean up
            del self.active_jobs[job_id]
            if job_id in self.job_anomalies:
                del self.job_anomalies[job_id]

            self.logger.info(f"Stopped monitoring print job {job_id}")
            return summary

        except Exception as e:
            self.logger.error(f"Failed to stop job monitoring: {e}")
            return {}

    def _check_job_anomalies(self, job_id: str, progress: float, status: str):
        """Check for anomalies in print job progress."""
        try:
            job_data = self.active_jobs[job_id]

            # Check for stalled progress
            current_time = time.time()
            time_since_update = current_time - job_data.get('last_update_time', current_time)

            if time_since_update > 300 and progress == job_data['last_progress']:  # 5 minutes no progress
                anomaly = {
                    'type': 'stalled_progress',
                    'timestamp': current_time,
                    'progress': progress,
                    'message': 'No progress detected for 5+ minutes'
                }
                self._record_anomaly(job_id, anomaly)

            # Check for rapid progress changes (potential issue)
            progress_diff = progress - job_data['last_progress']
            if progress_diff > 50:  # More than 50% progress in one update
                anomaly = {
                    'type': 'rapid_progress',
                    'timestamp': current_time,
                    'progress': progress,
                    'progress_diff': progress_diff,
                    'message': f'Sudden progress increase of {progress_diff:.1f}%'
                }
                self._record_anomaly(job_id, anomaly)

            # Update last progress time
            job_data['last_update_time'] = current_time

        except Exception as e:
            self.logger.warning(f"Anomaly check failed: {e}")

    def _record_anomaly(self, job_id: str, anomaly: Dict[str, Any]):
        """Record an anomaly for a print job."""
        if job_id not in self.job_anomalies:
            self.job_anomalies[job_id] = []

        self.job_anomalies[job_id].append(anomaly)

        # Update job data
        if job_id in self.active_jobs:
            self.active_jobs[job_id]['anomalies_detected'] += 1

        # Create system alert for significant anomalies
        if anomaly['type'] in ['stalled_progress', 'rapid_progress']:
            alert = Alert(
                id=f"job_anomaly_{job_id}_{int(time.time())}",
                severity="warning",
                title=f"Print Job Anomaly: {anomaly['type']}",
                message=f"Print job {job_id}: {anomaly['message']}",
                timestamp=datetime.now(),
                source=f"print_job_{job_id}",
                metadata={'job_id': job_id, 'anomaly': anomaly}
            )

            # Add to system monitor alerts
            self.system_monitor.alerts.append(alert)

        self.logger.warning(f"Anomaly in job {job_id}: {anomaly['message']}")

    def get_job_anomalies(self, job_id: str) -> List[Dict[str, Any]]:
        """Get anomalies for a specific job."""
        return self.job_anomalies.get(job_id, [])

    def get_active_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active print jobs."""
        return self.active_jobs.copy()


class RecoveryManager:
    """Automatic recovery system for print failures."""

    def __init__(self, system_monitor: SystemMonitor, job_monitor: PrintJobMonitor):
        self.system_monitor = system_monitor
        self.job_monitor = job_monitor
        self.logger = logging.getLogger(__name__)
        self.recovery_strategies: Dict[str, Callable] = {}

        # Initialize recovery strategies
        self._initialize_recovery_strategies()

    def _initialize_recovery_strategies(self):
        """Initialize recovery strategies for common issues."""
        self.recovery_strategies = {
            'printer_not_responding': self._recover_printer_connection,
            'thermal_runaway': self._recover_thermal_issues,
            'filament_jam': self._recover_filament_issues,
            'power_loss': self._recover_power_issues,
            'network_timeout': self._recover_network_issues
        }

    def attempt_recovery(self, failure_type: str, job_id: str, context: Dict[str, Any] = None) -> bool:
        """Attempt automatic recovery from failure."""
        context = context or {}

        if failure_type not in self.recovery_strategies:
            self.logger.warning(f"No recovery strategy for failure type: {failure_type}")
            return False

        try:
            self.logger.info(f"Attempting recovery for {failure_type} in job {job_id}")

            # Execute recovery strategy
            success = self.recovery_strategies[failure_type](job_id, context)

            if success:
                self.logger.info(f"Successfully recovered from {failure_type}")
                return True
            else:
                self.logger.error(f"Recovery failed for {failure_type}")
                return False

        except Exception as e:
            self.logger.error(f"Recovery attempt failed: {e}")
            return False

    def _recover_printer_connection(self, job_id: str, context: Dict[str, Any]) -> bool:
        """Recover from printer connection issues."""
        try:
            # Simulate connection recovery
            time.sleep(2)  # Wait for reconnection attempt

            # Update job status
            if job_id in self.job_monitor.active_jobs:
                self.job_monitor.active_jobs[job_id]['status'] = 'recovering'

            return True  # Assume recovery successful for demo

        except Exception as e:
            self.logger.error(f"Printer connection recovery failed: {e}")
            return False

    def _recover_thermal_issues(self, job_id: str, context: Dict[str, Any]) -> bool:
        """Recover from thermal runaway or temperature issues."""
        try:
            # Cool down printer
            time.sleep(5)

            # Reset temperature controls
            # In real implementation, would send G-code commands

            return True

        except Exception as e:
            self.logger.error(f"Thermal recovery failed: {e}")
            return False

    def _recover_filament_issues(self, job_id: str, context: Dict[str, Any]) -> bool:
        """Recover from filament jams or feed issues."""
        try:
            # Attempt filament purge
            time.sleep(3)

            # Resume printing
            return True

        except Exception as e:
            self.logger.error(f"Filament recovery failed: {e}")
            return False

    def _recover_power_issues(self, job_id: str, context: Dict[str, Any]) -> bool:
        """Recover from power loss."""
        try:
            # Wait for power restoration
            time.sleep(10)

            # Attempt resume from last position
            return True

        except Exception as e:
            self.logger.error(f"Power recovery failed: {e}")
            return False

    def _recover_network_issues(self, job_id: str, context: Dict[str, Any]) -> bool:
        """Recover from network connectivity issues."""
        try:
            # Wait for network restoration
            time.sleep(5)

            # Re-establish connection
            return True

        except Exception as e:
            self.logger.error(f"Network recovery failed: {e}")
            return False


# Enhanced SystemMonitor with print monitoring
class EnhancedSystemMonitor(SystemMonitor):
    """Enhanced system monitor with print job monitoring capabilities."""

    def __init__(self):
        super().__init__()
        self.print_job_monitor = PrintJobMonitor(self)
        self.recovery_manager = RecoveryManager(self, self.print_job_monitor)

    def start_print_job_monitoring(self, job_id: str, job_info: Dict[str, Any]) -> bool:
        """Start monitoring a print job."""
        return self.print_job_monitor.start_job_monitoring(job_id, job_info)

    def update_print_progress(self, job_id: str, progress: float, status: str = None) -> bool:
        """Update print job progress."""
        return self.print_job_monitor.update_job_progress(job_id, progress, status)

    def stop_print_job_monitoring(self, job_id: str, final_status: str = 'completed') -> Dict[str, Any]:
        """Stop monitoring a print job."""
        return self.print_job_monitor.stop_job_monitoring(job_id, final_status)

    def attempt_print_recovery(self, failure_type: str, job_id: str) -> bool:
        """Attempt recovery from print failure."""
        return self.recovery_manager.attempt_recovery(failure_type, job_id)