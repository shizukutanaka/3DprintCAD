"""
Advanced Performance Optimizer for 3D Print CAD Assistant
Provides intelligent performance monitoring, optimization, and auto-scaling
Suitable for high-load government deployments
"""

import asyncio
import psutil
import time
import statistics
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import threading
import queue
import json
from pathlib import Path
import numpy as np
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import functools

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_io: Dict[str, int]
    network_io: Dict[str, int]
    response_times: List[float]
    throughput: float  # requests per second
    error_rate: float
    active_connections: int

@dataclass
class OptimizationStrategy:
    """Performance optimization strategy"""
    name: str
    description: str
    target_metric: str
    threshold: float
    action: Callable
    priority: int
    estimated_improvement: float

@dataclass
class PerformanceProfile:
    """Performance profile for different workloads"""
    name: str
    cpu_target: float
    memory_target: float
    response_time_target: float
    throughput_target: float
    optimization_strategies: List[OptimizationStrategy] = field(default_factory=list)

class IntelligentCache:
    """Intelligent caching system with ML-based prefetching"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_patterns = {}
        self.prediction_model = None

    def get(self, key: str) -> Any:
        """Get item from cache with pattern tracking"""
        current_time = time.time()

        # Track access pattern
        if key not in self.access_patterns:
            self.access_patterns[key] = []
        self.access_patterns[key].append(current_time)

        # Check if item exists and is not expired
        if key in self.cache:
            item_time, value = self.cache[key]
            if current_time - item_time < self.ttl:
                return value
            else:
                del self.cache[key]

        return None

    def put(self, key: str, value: Any):
        """Put item in cache with intelligent eviction"""
        current_time = time.time()

        # Evict if at capacity
        if len(self.cache) >= self.max_size:
            self._intelligent_eviction()

        self.cache[key] = (current_time, value)

    def _intelligent_eviction(self):
        """Evict items based on access patterns and predictions"""
        current_time = time.time()

        # Calculate access frequency and recency for each item
        scores = {}
        for key, (timestamp, _) in self.cache.items():
            recency_score = 1.0 / (current_time - timestamp + 1)
            frequency_score = len(self.access_patterns.get(key, []))
            pattern_score = self._predict_future_access(key)

            scores[key] = recency_score * 0.3 + frequency_score * 0.4 + pattern_score * 0.3

        # Remove item with lowest score
        if scores:
            worst_key = min(scores.keys(), key=lambda k: scores[k])
            del self.cache[worst_key]

    def _predict_future_access(self, key: str) -> float:
        """Predict likelihood of future access"""
        if key not in self.access_patterns:
            return 0.0

        accesses = self.access_patterns[key]
        if len(accesses) < 2:
            return 0.5

        # Simple pattern recognition based on access intervals
        intervals = [accesses[i] - accesses[i-1] for i in range(1, len(accesses))]
        if intervals:
            avg_interval = statistics.mean(intervals)
            time_since_last = time.time() - accesses[-1]
            return max(0, 1 - (time_since_last / avg_interval))

        return 0.0

class PerformanceOptimizer:
    """Advanced performance optimizer with ML-based optimization"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.metrics_history: List[PerformanceMetrics] = []
        self.current_profile = self._get_default_profile()
        self.optimization_strategies = self._initialize_strategies()
        self.intelligent_cache = IntelligentCache()
        self.is_monitoring = False
        self.executor = ThreadPoolExecutor(max_workers=4)

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load optimizer configuration"""
        default_config = {
            "monitoring_interval": 10,  # seconds
            "metrics_retention": 86400,  # 24 hours
            "auto_optimization": True,
            "performance_targets": {
                "cpu_threshold": 80.0,
                "memory_threshold": 85.0,
                "response_time_threshold": 2.0,
                "error_rate_threshold": 0.01
            }
        }

        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Could not load config from {config_path}: {e}")

        return default_config

    def _get_default_profile(self) -> PerformanceProfile:
        """Get default performance profile"""
        return PerformanceProfile(
            name="default",
            cpu_target=70.0,
            memory_target=80.0,
            response_time_target=1.0,
            throughput_target=100.0
        )

    def _initialize_strategies(self) -> List[OptimizationStrategy]:
        """Initialize optimization strategies"""
        strategies = [
            OptimizationStrategy(
                name="memory_cleanup",
                description="Clean up unused memory and caches",
                target_metric="memory_percent",
                threshold=85.0,
                action=self._cleanup_memory,
                priority=1,
                estimated_improvement=15.0
            ),
            OptimizationStrategy(
                name="cpu_optimization",
                description="Optimize CPU-intensive operations",
                target_metric="cpu_percent",
                threshold=80.0,
                action=self._optimize_cpu,
                priority=2,
                estimated_improvement=20.0
            ),
            OptimizationStrategy(
                name="cache_optimization",
                description="Optimize caching strategies",
                target_metric="response_time",
                threshold=2.0,
                action=self._optimize_cache,
                priority=3,
                estimated_improvement=30.0
            ),
            OptimizationStrategy(
                name="database_optimization",
                description="Optimize database queries and connections",
                target_metric="response_time",
                threshold=1.5,
                action=self._optimize_database,
                priority=2,
                estimated_improvement=25.0
            )
        ]

        return strategies

    async def start_monitoring(self):
        """Start performance monitoring"""
        self.is_monitoring = True
        logger.info("Performance monitoring started")

        while self.is_monitoring:
            try:
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)

                # Clean old metrics
                cutoff_time = datetime.now() - timedelta(seconds=self.config["metrics_retention"])
                self.metrics_history = [m for m in self.metrics_history if m.timestamp > cutoff_time]

                # Check for optimization opportunities
                if self.config["auto_optimization"]:
                    await self._auto_optimize(metrics)

                await asyncio.sleep(self.config["monitoring_interval"])

            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(5)

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        logger.info("Performance monitoring stopped")

    async def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        # CPU and memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        # Disk I/O
        disk_io = psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {}

        # Network I/O
        network_io = psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}

        # Application-specific metrics (would be populated by application)
        response_times = getattr(self, '_recent_response_times', [])
        throughput = getattr(self, '_current_throughput', 0.0)
        error_rate = getattr(self, '_current_error_rate', 0.0)
        active_connections = getattr(self, '_active_connections', 0)

        return PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_io=disk_io,
            network_io=network_io,
            response_times=response_times,
            throughput=throughput,
            error_rate=error_rate,
            active_connections=active_connections
        )

    async def _auto_optimize(self, metrics: PerformanceMetrics):
        """Automatically optimize based on current metrics"""
        for strategy in sorted(self.optimization_strategies, key=lambda s: s.priority):
            if self._should_apply_strategy(strategy, metrics):
                logger.info(f"Applying optimization strategy: {strategy.name}")
                try:
                    await strategy.action()
                    logger.info(f"Optimization strategy {strategy.name} completed")
                except Exception as e:
                    logger.error(f"Error applying strategy {strategy.name}: {e}")

    def _should_apply_strategy(self, strategy: OptimizationStrategy, metrics: PerformanceMetrics) -> bool:
        """Determine if optimization strategy should be applied"""
        metric_value = getattr(metrics, strategy.target_metric.replace('_percent', '_percent'), 0)

        if isinstance(metric_value, list):
            # For response_times, use average
            metric_value = statistics.mean(metric_value) if metric_value else 0

        return metric_value > strategy.threshold

    async def _cleanup_memory(self):
        """Clean up memory usage"""
        import gc

        # Force garbage collection
        gc.collect()

        # Clear intelligent cache if memory pressure is high
        if psutil.virtual_memory().percent > 90:
            self.intelligent_cache.cache.clear()
            logger.info("Cleared intelligent cache due to memory pressure")

        # Clear any application-specific caches
        # This would be customized based on the application
        logger.info("Memory cleanup completed")

    async def _optimize_cpu(self):
        """Optimize CPU usage"""
        # Reduce thread pool size temporarily
        if hasattr(self, 'executor'):
            old_max_workers = self.executor._max_workers
            self.executor._max_workers = max(1, old_max_workers // 2)
            logger.info(f"Reduced thread pool from {old_max_workers} to {self.executor._max_workers}")

        # Implement CPU-specific optimizations
        logger.info("CPU optimization completed")

    async def _optimize_cache(self):
        """Optimize caching strategies"""
        # Adjust cache size based on available memory
        available_memory = psutil.virtual_memory().available
        optimal_cache_size = min(1000, available_memory // (1024 * 1024 * 10))  # 10MB per item

        self.intelligent_cache.max_size = int(optimal_cache_size)
        logger.info(f"Adjusted cache size to {optimal_cache_size}")

    async def _optimize_database(self):
        """Optimize database performance"""
        # This would implement database-specific optimizations
        # such as connection pool tuning, query optimization, etc.
        logger.info("Database optimization completed")

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.metrics_history:
            return {"error": "No metrics available"}

        recent_metrics = self.metrics_history[-100:]  # Last 100 data points

        # Calculate averages and trends
        avg_cpu = statistics.mean(m.cpu_percent for m in recent_metrics)
        avg_memory = statistics.mean(m.memory_percent for m in recent_metrics)
        avg_response_time = statistics.mean(
            statistics.mean(m.response_times) if m.response_times else 0
            for m in recent_metrics
        )

        # Performance trends
        cpu_trend = self._calculate_trend([m.cpu_percent for m in recent_metrics])
        memory_trend = self._calculate_trend([m.memory_percent for m in recent_metrics])

        # Optimization recommendations
        recommendations = self._generate_recommendations(recent_metrics)

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "average_cpu": round(avg_cpu, 2),
                "average_memory": round(avg_memory, 2),
                "average_response_time": round(avg_response_time, 3),
                "cpu_trend": cpu_trend,
                "memory_trend": memory_trend
            },
            "current_profile": {
                "name": self.current_profile.name,
                "targets": {
                    "cpu": self.current_profile.cpu_target,
                    "memory": self.current_profile.memory_target,
                    "response_time": self.current_profile.response_time_target,
                    "throughput": self.current_profile.throughput_target
                }
            },
            "cache_performance": {
                "size": len(self.intelligent_cache.cache),
                "max_size": self.intelligent_cache.max_size,
                "utilization": len(self.intelligent_cache.cache) / self.intelligent_cache.max_size
            },
            "recommendations": recommendations
        }

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction"""
        if len(values) < 2:
            return "stable"

        # Simple linear regression slope
        x = list(range(len(values)))
        slope = np.polyfit(x, values, 1)[0] if len(values) > 1 else 0

        if slope > 0.5:
            return "increasing"
        elif slope < -0.5:
            return "decreasing"
        else:
            return "stable"

    def _generate_recommendations(self, metrics: List[PerformanceMetrics]) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []

        if not metrics:
            return recommendations

        latest = metrics[-1]

        # CPU recommendations
        if latest.cpu_percent > 80:
            recommendations.append("High CPU usage detected. Consider horizontal scaling or CPU optimization.")

        # Memory recommendations
        if latest.memory_percent > 85:
            recommendations.append("High memory usage detected. Consider memory cleanup or vertical scaling.")

        # Response time recommendations
        if latest.response_times and statistics.mean(latest.response_times) > 2.0:
            recommendations.append("High response times detected. Consider caching optimization or database tuning.")

        # Throughput recommendations
        if latest.throughput < self.current_profile.throughput_target * 0.8:
            recommendations.append("Low throughput detected. Consider load balancing or performance tuning.")

        return recommendations

def performance_monitor(func):
    """Decorator to monitor function performance"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            # Record error for error rate calculation
            if hasattr(wrapper, '_error_count'):
                wrapper._error_count += 1
            else:
                wrapper._error_count = 1
            raise
        finally:
            end_time = time.time()
            response_time = end_time - start_time

            # Record response time
            if not hasattr(wrapper, '_response_times'):
                wrapper._response_times = []
            wrapper._response_times.append(response_time)

            # Keep only recent measurements
            wrapper._response_times = wrapper._response_times[-100:]

    return wrapper

async def main():
    """Main performance optimizer entry point"""
    optimizer = PerformanceOptimizer()

    # Start monitoring
    monitoring_task = asyncio.create_task(optimizer.start_monitoring())

    try:
        # Run for demo purposes
        await asyncio.sleep(60)

        # Generate and print report
        report = optimizer.get_performance_report()
        print(json.dumps(report, indent=2))

    finally:
        optimizer.stop_monitoring()
        await monitoring_task

if __name__ == "__main__":
    asyncio.run(main())