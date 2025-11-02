"""Advanced monitoring and alerting system for 3D Print CAD Assistant."""

import time
import threading
import logging
import psutil
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import requests


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert notification channels."""
    LOG = "log"
    EMAIL = "email"
    WEBHOOK = "webhook"
    FILE = "file"


@dataclass
class Alert:
    """Alert notification."""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class MetricValue:
    """Single metric measurement."""
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricCollector:
    """Collects and stores system metrics."""

    def __init__(self, max_samples: int = 1000):
        """Initialize metric collector.

        Args:
            max_samples: Maximum number of samples to keep per metric
        """
        self.max_samples = max_samples
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self._lock = threading.RLock()

    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels for the metric
        """
        with self._lock:
            metric_value = MetricValue(
                value=value,
                timestamp=time.time(),
                labels=labels or {}
            )
            self._metrics[name].append(metric_value)

    def get_metric_history(self, name: str, limit: Optional[int] = None) -> List[MetricValue]:
        """Get metric history.

        Args:
            name: Metric name
            limit: Maximum number of samples to return

        Returns:
            List of metric values
        """
        with self._lock:
            values = list(self._metrics[name])
            if limit:
                return values[-limit:]
            return values

    def get_latest_value(self, name: str) -> Optional[float]:
        """Get the latest value for a metric.

        Args:
            name: Metric name

        Returns:
            Latest metric value or None if no data
        """
        with self._lock:
            values = self._metrics[name]
            if values:
                return values[-1].value
            return None

    def clear_metrics(self, name: Optional[str] = None):
        """Clear metric data.

        Args:
            name: Specific metric name to clear, or None to clear all
        """
        with self._lock:
            if name:
                self._metrics[name].clear()
            else:
                self._metrics.clear()


class SystemMonitor:
    """Monitors system resources and performance."""

    def __init__(self, collection_interval: float = 5.0):
        """Initialize system monitor.

        Args:
            collection_interval: Interval between metric collections in seconds
        """
        self.logger = logging.getLogger(__name__)
        self.collection_interval = collection_interval
        self.collector = MetricCollector()
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start_monitoring(self):
        """Start system monitoring."""
        if self._monitoring_thread:
            return

        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="SystemMonitor"
        )
        self._monitoring_thread.start()
        self.logger.info("System monitoring started")

    def stop_monitoring(self):
        """Stop system monitoring."""
        if self._monitoring_thread:
            self._stop_event.set()
            self._monitoring_thread.join(timeout=5.0)
            self._monitoring_thread = None
            self.logger.info("System monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                self._collect_system_metrics()
                self._stop_event.wait(self.collection_interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(1.0)

    def _collect_system_metrics(self):
        """Collect current system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            self.collector.record_metric('cpu.usage_percent', cpu_percent)

            # Memory metrics
            memory = psutil.virtual_memory()
            self.collector.record_metric('memory.usage_percent', memory.percent)
            self.collector.record_metric('memory.used_gb', memory.used / (1024**3))
            self.collector.record_metric('memory.available_gb', memory.available / (1024**3))

            # Disk metrics
            disk = psutil.disk_usage('/')
            self.collector.record_metric('disk.usage_percent', disk.percent)
            self.collector.record_metric('disk.used_gb', disk.used / (1024**3))

            # Network metrics (if available)
            try:
                network = psutil.net_io_counters()
                self.collector.record_metric('network.bytes_sent', network.bytes_sent)
                self.collector.record_metric('network.bytes_recv', network.bytes_recv)
            except:
                pass

            # Process metrics
            process = psutil.Process()
            self.collector.record_metric('process.memory_mb', process.memory_info().rss / (1024**2))
            self.collector.record_metric('process.cpu_percent', process.cpu_percent())
            self.collector.record_metric('process.threads', process.num_threads())

        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")


class AlertManager:
    """Manages alert notifications and channels."""

    def __init__(self):
        """Initialize alert manager."""
        self.logger = logging.getLogger(__name__)
        self.alerts: List[Alert] = []
        self.channels: Dict[AlertChannel, Callable] = {}
        self._lock = threading.RLock()
        self.max_alerts = 10000

        # Register default channels
        self.register_channel(AlertChannel.LOG, self._log_alert)
        self.register_channel(AlertChannel.FILE, self._file_alert)

    def register_channel(self, channel: AlertChannel, handler: Callable):
        """Register an alert notification channel.

        Args:
            channel: Alert channel type
            handler: Handler function for the channel
        """
        self.channels[channel] = handler
        self.logger.info(f"Registered alert channel: {channel.value}")

    def send_alert(self, severity: AlertSeverity, title: str, message: str,
                   source: str, metadata: Optional[Dict[str, Any]] = None):
        """Send an alert notification.

        Args:
            severity: Alert severity level
            title: Alert title
            message: Alert message
            source: Source of the alert
            metadata: Additional metadata
        """
        alert = Alert(
            id=f"alert_{int(time.time() * 1000)}",
            severity=severity,
            title=title,
            message=message,
            timestamp=time.time(),
            source=source,
            metadata=metadata or {}
        )

        with self._lock:
            self.alerts.append(alert)

            # Remove old alerts if limit exceeded
            if len(self.alerts) > self.max_alerts:
                self.alerts = self.alerts[-self.max_alerts:]

        # Send through registered channels
        for channel, handler in self.channels.items():
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Failed to send alert via {channel.value}: {e}")

    def get_alerts(self, limit: int = 100, severity: Optional[AlertSeverity] = None,
                   source: Optional[str] = None) -> List[Alert]:
        """Get recent alerts.

        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity level
            source: Filter by source

        Returns:
            List of alerts
        """
        with self._lock:
            filtered_alerts = self.alerts

            if severity:
                filtered_alerts = [a for a in filtered_alerts if a.severity == severity]

            if source:
                filtered_alerts = [a for a in filtered_alerts if a.source == source]

            return filtered_alerts[-limit:]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert.

        Args:
            alert_id: Alert ID to acknowledge

        Returns:
            True if alert was found and acknowledged
        """
        with self._lock:
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    return True
            return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved.

        Args:
            alert_id: Alert ID to resolve

        Returns:
            True if alert was found and resolved
        """
        with self._lock:
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.resolved = True
                    alert.acknowledged = True
                    return True
            return False

    def _log_alert(self, alert: Alert):
        """Send alert to logging system."""
        log_method = getattr(self.logger, alert.severity.value.lower(), self.logger.info)
        log_method(f"[{alert.source}] {alert.title}: {alert.message}")

    def _file_alert(self, alert: Alert):
        """Write alert to file."""
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)

            log_file = log_dir / "alerts.jsonl"

            with open(log_file, 'a', encoding='utf-8') as f:
                json.dump({
                    'id': alert.id,
                    'severity': alert.severity.value,
                    'title': alert.title,
                    'message': alert.message,
                    'timestamp': alert.timestamp,
                    'source': alert.source,
                    'metadata': alert.metadata
                }, f, ensure_ascii=False)
                f.write('\n')

        except Exception as e:
            self.logger.error(f"Failed to write alert to file: {e}")


class MonitoringDashboard:
    """Web dashboard for monitoring system status."""

    def __init__(self, host: str = 'localhost', port: int = 8080):
        """Initialize monitoring dashboard.

        Args:
            host: Dashboard host
            port: Dashboard port
        """
        self.logger = logging.getLogger(__name__)
        self.host = host
        self.port = port
        self.app = None

    def start_dashboard(self):
        """Start the monitoring dashboard web server."""
        try:
            from flask import Flask, jsonify, render_template_string

            self.app = Flask(__name__)

            @self.app.route('/')
            def index():
                return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>3D Print CAD Assistant - Monitoring</title>
                    <meta http-equiv="refresh" content="30">
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        .metric { background: #f5f5f5; padding: 10px; margin: 5px; border-radius: 5px; }
                        .alert { padding: 10px; margin: 5px; border-radius: 5px; }
                        .critical { background: #ffebee; border-left: 4px solid #f44336; }
                        .error { background: #fff3e0; border-left: 4px solid #ff9800; }
                        .warning { background: #fffde7; border-left: 4px solid #ffc107; }
                        .info { background: #e3f2fd; border-left: 4px solid #2196f3; }
                    </style>
                </head>
                <body>
                    <h1>3D Print CAD Assistant - System Monitor</h1>
                    <div id="content">
                        <p>Loading...</p>
                    </div>
                    <script>
                        async function updateData() {
                            try {
                                const response = await fetch('/api/status');
                                const data = await response.json();
                                updateDisplay(data);
                            } catch (error) {
                                console.error('Failed to fetch data:', error);
                            }
                        }

                        function updateDisplay(data) {
                            const content = document.getElementById('content');
                            content.innerHTML = `
                                <h2>System Status</h2>
                                <div class="metric">
                                    <strong>CPU Usage:</strong> ${data.system.cpu_percent}%
                                </div>
                                <div class="metric">
                                    <strong>Memory Usage:</strong> ${data.system.memory_percent}%
                                </div>
                                <div class="metric">
                                    <strong>Active Alerts:</strong> ${data.alerts.active}
                                </div>

                                <h2>Recent Alerts</h2>
                                ${data.alerts.recent.map(alert => `
                                    <div class="alert ${alert.severity}">
                                        <strong>${alert.title}</strong><br>
                                        ${alert.message}<br>
                                        <small>${new Date(alert.timestamp * 1000).toLocaleString()} - ${alert.source}</small>
                                    </div>
                                `).join('')}
                            `;
                        }

                        // Update every 30 seconds
                        setInterval(updateData, 30000);
                        updateData(); // Initial load
                    </script>
                </body>
                </html>
                """)

            @self.app.route('/api/status')
            def api_status():
                return jsonify(self._get_system_status())

            self.app.run(host=self.host, port=self.port, debug=False, threaded=True)
            self.logger.info(f"Monitoring dashboard started at http://{self.host}:{self.port}")

        except ImportError:
            self.logger.warning("Flask not available, dashboard disabled")
        except Exception as e:
            self.logger.error(f"Failed to start monitoring dashboard: {e}")

    def _get_system_status(self) -> Dict[str, Any]:
        """Get current system status for dashboard."""
        try:
            # This would integrate with the actual monitoring system
            return {
                'system': {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'uptime': time.time() - psutil.boot_time()
                },
                'alerts': {
                    'active': 0,
                    'recent': []
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get system status: {e}")
            return {'error': str(e)}


class AdvancedMonitoringSystem:
    """Complete monitoring and alerting system."""

    def __init__(self):
        """Initialize the advanced monitoring system."""
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.system_monitor = SystemMonitor()
        self.alert_manager = AlertManager()
        self.dashboard = MonitoringDashboard()

        # Alert thresholds
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0,
            'error_rate': 0.1
        }

    def start_monitoring(self):
        """Start all monitoring components."""
        self.system_monitor.start_monitoring()
        self.dashboard.start_dashboard()
        self.logger.info("Advanced monitoring system started")

    def stop_monitoring(self):
        """Stop all monitoring components."""
        self.system_monitor.stop_monitoring()
        self.logger.info("Advanced monitoring system stopped")

    def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health.

        Returns:
            Health status dictionary
        """
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            health_status = {
                'healthy': True,
                'issues': [],
                'timestamp': time.time()
            }

            # Check thresholds
            if cpu_percent > self.thresholds['cpu_percent']:
                health_status['issues'].append(f"High CPU usage: {cpu_percent}%")
                health_status['healthy'] = False

            if memory.percent > self.thresholds['memory_percent']:
                health_status['issues'].append(f"High memory usage: {memory.percent}%")
                health_status['healthy'] = False

            if disk.percent > self.thresholds['disk_percent']:
                health_status['issues'].append(f"High disk usage: {disk.percent}%")
                health_status['healthy'] = False

            return health_status

        except Exception as e:
            self.logger.error(f"Failed to check system health: {e}")
            return {'healthy': False, 'error': str(e)}

    def send_alert(self, severity: AlertSeverity, title: str, message: str,
                   source: str = 'system', metadata: Optional[Dict[str, Any]] = None):
        """Send an alert notification.

        Args:
            severity: Alert severity
            title: Alert title
            message: Alert message
            source: Alert source
            metadata: Additional metadata
        """
        self.alert_manager.send_alert(severity, title, message, source, metadata)

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring system statistics.

        Returns:
            Dictionary with monitoring statistics
        """
        return {
            'alerts_total': len(self.alert_manager.alerts),
            'alerts_active': len([a for a in self.alert_manager.alerts if not a.acknowledged]),
            'system_health': self.check_system_health(),
            'monitoring_uptime': time.time() - (self.system_monitor._monitoring_thread.start_time if self.system_monitor._monitoring_thread else time.time())
        }


# Global monitoring system instance
monitoring_system = AdvancedMonitoringSystem()
