"""Cloud-native distributed processing system for scalable 3D model processing."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from datetime import datetime, timedelta
import threading
import queue
import multiprocessing

logger = logging.getLogger(__name__)


class ProcessingPriority(Enum):
    """Processing priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class ProcessingStatus(Enum):
    """Processing status enumeration."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ProcessingTask:
    """Represents a distributed processing task."""
    task_id: str
    operation: str  # 'validate', 'repair', 'slice', 'gcode'
    input_data: Dict[str, Any]
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    max_workers: int = 1
    timeout_seconds: float = 300.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: ProcessingStatus = ProcessingStatus.QUEUED
    worker_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            **asdict(self),
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class WorkerInfo:
    """Information about a processing worker."""
    worker_id: str
    hostname: str
    capabilities: List[str]
    max_concurrent_tasks: int
    current_tasks: int = 0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    status: str = "active"
    performance_metrics: Dict[str, float] = field(default_factory=dict)


class TaskQueue:
    """Priority-based task queue with thread safety."""

    def __init__(self):
        self._tasks: Dict[str, ProcessingTask] = {}
        self._priority_queues = {
            ProcessingPriority.URGENT: [],
            ProcessingPriority.HIGH: [],
            ProcessingPriority.NORMAL: [],
            ProcessingPriority.LOW: []
        }
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)

    def enqueue(self, task: ProcessingTask):
        """Add task to appropriate priority queue."""
        with self._lock:
            self._tasks[task.task_id] = task
            self._priority_queues[task.priority].append(task.task_id)

            # Notify waiting workers
            with self._condition:
                self._condition.notify()

    def dequeue(self, timeout: Optional[float] = None) -> Optional[ProcessingTask]:
        """Get highest priority available task."""
        with self._lock:
            # Check all priority levels in order
            for priority in [ProcessingPriority.URGENT, ProcessingPriority.HIGH,
                           ProcessingPriority.NORMAL, ProcessingPriority.LOW]:
                queue = self._priority_queues[priority]
                if queue:
                    task_id = queue.pop(0)
                    task = self._tasks[task_id]
                    del self._tasks[task_id]
                    return task

            # No tasks available, wait for notification
            if timeout is not None:
                with self._condition:
                    self._condition.wait(timeout)
                    # Try again after waiting
                    for priority in [ProcessingPriority.URGENT, ProcessingPriority.HIGH,
                                   ProcessingPriority.NORMAL, ProcessingPriority.LOW]:
                        queue = self._priority_queues[priority]
                        if queue:
                            task_id = queue.pop(0)
                            task = self._tasks[task_id]
                            del self._tasks[task_id]
                            return task

            return None

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self._lock:
            return {
                'total_tasks': len(self._tasks),
                'by_priority': {
                    priority.name: len(queue)
                    for priority, queue in self._priority_queues.items()
                },
                'by_status': {
                    status: len([t for t in self._tasks.values() if t.status == status])
                    for status in ProcessingStatus
                }
            }


class TaskProcessor(ABC):
    """Abstract base class for task processors."""

    @abstractmethod
    async def process_task(self, task: ProcessingTask) -> Dict[str, Any]:
        """Process a single task."""
        pass


class MeshProcessingTaskProcessor(TaskProcessor):
    """Task processor for 3D mesh operations."""

    def __init__(self):
        # Import here to avoid circular imports
        from ..core.analysis.mesh_validator import validate_mesh
        from ..core.analysis.mesh_repair import repair_mesh
        from ..core.slicing import SlicingEngine
        from ..adapters import load_mesh

        self.mesh_validator = validate_mesh
        self.mesh_repair = repair_mesh
        self.slicing_engine = SlicingEngine
        self.mesh_loader = load_mesh

    async def process_task(self, task: ProcessingTask) -> Dict[str, Any]:
        """Process mesh-related tasks."""
        operation = task.operation
        input_data = task.input_data

        try:
            # Load mesh data
            if 'mesh_data' in input_data:
                # For demo purposes, assume mesh_data is a file path or base64 data
                mesh_file = input_data['mesh_data']
                if isinstance(mesh_file, str) and mesh_file.startswith(('http', 'ftp')):
                    # Download from URL (simplified)
                    mesh = await self._download_mesh(mesh_file)
                else:
                    # Load from local path or base64
                    mesh = await self._load_mesh_data(mesh_file)
            else:
                raise ValueError("No mesh data provided")

            result = {'task_id': task.task_id, 'operation': operation}

            # Perform requested operation
            if operation == 'validate':
                validation_result = self.mesh_validator(mesh)
                result['validation'] = validation_result.as_dict()
                result['success'] = validation_result.success

            elif operation == 'repair':
                repaired_mesh, repair_summary = self.mesh_repair(mesh)
                result['repair_summary'] = {
                    'operations_performed': [op.operation.value for op in repair_summary.operations_performed],
                    'issues_fixed': repair_summary.issues_fixed,
                    'success': repair_summary.repair_success
                }
                result['success'] = repaired_mesh is not None

            elif operation == 'slice':
                slice_settings = input_data.get('slice_settings', {})
                slicer = SlicingEngine(slice_settings)
                slicing_result = slicer.slice_mesh(mesh)
                result['slicing'] = {
                    'layers': slicing_result.total_layers,
                    'print_time': slicing_result.total_print_time_seconds,
                    'material_usage': slicing_result.total_material_grams
                }
                result['success'] = True

            elif operation == 'gcode':
                # Would need G-code generation implementation
                result['gcode'] = "G-code generation not implemented in this demo"
                result['success'] = False

            else:
                raise ValueError(f"Unknown operation: {operation}")

            return result

        except Exception as e:
            logger.error(f"Task processing failed: {e}")
            return {
                'task_id': task.task_id,
                'operation': operation,
                'success': False,
                'error': str(e)
            }

    async def _download_mesh(self, url: str):
        """Download mesh from URL (simplified implementation)."""
        # This would implement actual HTTP download
        # For now, return a placeholder
        from ..adapters import load_mesh
        return load_mesh(Path("dummy_path"))  # Placeholder

    async def _load_mesh_data(self, mesh_data):
        """Load mesh from various data formats."""
        from ..adapters import load_mesh

        if isinstance(mesh_data, (str, Path)):
            # File path
            return load_mesh(Path(mesh_data))
        else:
            # Assume base64 or other format
            # This would implement actual data loading
            return load_mesh(Path("dummy_path"))  # Placeholder


class DistributedProcessingManager:
    """Cloud-native distributed processing manager."""

    def __init__(self, max_workers: int = 4, enable_cloud_scaling: bool = True):
        self.max_workers = max_workers
        self.enable_cloud_scaling = enable_cloud_scaling
        self.task_queue = TaskQueue()
        self.workers: Dict[str, WorkerInfo] = {}
        self.active_tasks: Dict[str, ProcessingTask] = {}
        self.processor = MeshProcessingTaskProcessor()

        # Worker management
        self._worker_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._shutdown_event = threading.Event()

        # Cloud scaling (simplified)
        self._cloud_workers: Dict[str, WorkerInfo] = {}
        self._auto_scaling_enabled = enable_cloud_scaling

        logger.info(f"Distributed processing manager initialized with {max_workers} workers")

    def start(self):
        """Start the distributed processing system."""
        # Start local workers
        for i in range(self.max_workers):
            worker_id = f"local_worker_{i+1}"
            self._start_worker(worker_id)

        # Start auto-scaling if enabled
        if self._auto_scaling_enabled:
            self._start_auto_scaler()

        logger.info("Distributed processing system started")

    def _start_worker(self, worker_id: str):
        """Start a processing worker."""
        worker_info = WorkerInfo(
            worker_id=worker_id,
            hostname="localhost",  # Would be actual hostname in cloud
            capabilities=["validate", "repair", "slice"],
            max_concurrent_tasks=2
        )
        self.workers[worker_id] = worker_info

        # Start worker thread
        def worker_loop():
            while not self._shutdown_event.is_set():
                try:
                    task = self.task_queue.dequeue(timeout=1.0)
                    if task:
                        self._execute_task(task, worker_id)
                    else:
                        time.sleep(0.1)  # Brief pause if no tasks
                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {e}")
                    time.sleep(1.0)

        thread = threading.Thread(target=worker_loop, daemon=True, name=f"Worker-{worker_id}")
        thread.start()

        logger.info(f"Started worker: {worker_id}")

    def _execute_task(self, task: ProcessingTask, worker_id: str):
        """Execute a processing task."""
        task.status = ProcessingStatus.RUNNING
        task.started_at = datetime.now()
        task.worker_id = worker_id
        self.active_tasks[task.task_id] = task

        try:
            # Update worker status
            if worker_id in self.workers:
                self.workers[worker_id].current_tasks += 1
                self.workers[worker_id].last_heartbeat = datetime.now()

            # Execute task based on operation type
            if task.operation in ['validate', 'repair', 'slice', 'gcode']:
                # Use asyncio for async processing
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(self.processor.process_task(task))
                finally:
                    loop.close()
            else:
                raise ValueError(f"Unsupported operation: {task.operation}")

            # Update task with results
            task.status = ProcessingStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            task.progress = 100.0

        except asyncio.TimeoutError:
            task.status = ProcessingStatus.TIMEOUT
            task.error = "Task timed out"
        except Exception as e:
            task.status = ProcessingStatus.FAILED
            task.error = str(e)
            logger.error(f"Task {task.task_id} failed: {e}")
        finally:
            # Update worker status
            if worker_id in self.workers:
                self.workers[worker_id].current_tasks -= 1

            # Remove from active tasks
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]

    def _start_auto_scaler(self):
        """Start automatic scaling based on queue length."""
        def auto_scaler_loop():
            while not self._shutdown_event.is_set():
                try:
                    stats = self.task_queue.get_queue_stats()

                    # Scale up if queue is growing
                    if stats['total_tasks'] > self.max_workers * 2:
                        self._scale_up()

                    # Scale down if queue is empty and workers are idle
                    elif stats['total_tasks'] == 0 and len(self.workers) > 1:
                        self._scale_down()

                except Exception as e:
                    logger.error(f"Auto-scaler error: {e}")

                time.sleep(30)  # Check every 30 seconds

        thread = threading.Thread(target=auto_scaler_loop, daemon=True, name="AutoScaler")
        thread.start()
        logger.info("Auto-scaler started")

    def _scale_up(self):
        """Scale up processing capacity."""
        if not self.enable_cloud_scaling:
            return

        # Add cloud worker (simplified)
        worker_id = f"cloud_worker_{len(self._cloud_workers) + 1}"
        worker_info = WorkerInfo(
            worker_id=worker_id,
            hostname=f"cloud-instance-{len(self._cloud_workers) + 1}",
            capabilities=["validate", "repair", "slice"],
            max_concurrent_tasks=4  # Cloud workers can handle more
        )

        self._cloud_workers[worker_id] = worker_info
        self._start_worker(worker_id)

        logger.info(f"Scaled up: added {worker_id}")

    def _scale_down(self):
        """Scale down processing capacity."""
        # Remove idle cloud workers
        for worker_id in list(self._cloud_workers.keys()):
            worker = self.workers.get(worker_id)
            if worker and worker.current_tasks == 0:
                # Stop worker thread (simplified)
                del self.workers[worker_id]
                del self._cloud_workers[worker_id]
                logger.info(f"Scaled down: removed {worker_id}")
                break

    def submit_task(self, operation: str, input_data: Dict[str, Any],
                   priority: ProcessingPriority = ProcessingPriority.NORMAL,
                   timeout_seconds: float = 300.0) -> str:
        """Submit a processing task."""
        task_id = str(uuid.uuid4())
        task = ProcessingTask(
            task_id=task_id,
            operation=operation,
            input_data=input_data,
            priority=priority,
            timeout_seconds=timeout_seconds
        )

        self.task_queue.enqueue(task)
        logger.info(f"Submitted task {task_id}: {operation}")
        return task_id

    def get_task_status(self, task_id: str) -> Optional[ProcessingTask]:
        """Get status of a processing task."""
        # Check active tasks first
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]

        # Check if task was completed and stored elsewhere
        # (In a real implementation, this would query a database)
        return None

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a processing task."""
        # Find task in queue or active tasks
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = ProcessingStatus.CANCELLED
            del self.active_tasks[task_id]
            return True

        # For queued tasks, this would be more complex
        # (Would need to find and remove from priority queues)
        return False

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        queue_stats = self.task_queue.get_queue_stats()

        worker_stats = {
            'total_workers': len(self.workers),
            'active_workers': len([w for w in self.workers.values() if w.current_tasks > 0]),
            'idle_workers': len([w for w in self.workers.values() if w.current_tasks == 0]),
            'local_workers': len([w for w in self.workers.values() if not w.worker_id.startswith('cloud')]),
            'cloud_workers': len(self._cloud_workers)
        }

        return {
            'queue': queue_stats,
            'workers': worker_stats,
            'active_tasks': len(self.active_tasks),
            'system_load': len(self.active_tasks) / max(len(self.workers), 1),
            'auto_scaling_enabled': self._auto_scaling_enabled,
            'cloud_scaling_enabled': self.enable_cloud_scaling
        }

    def shutdown(self):
        """Shutdown the distributed processing system."""
        logger.info("Shutting down distributed processing system...")

        # Signal shutdown
        self._shutdown_event.set()

        # Wait for active tasks to complete (with timeout)
        timeout = 30.0
        start_time = time.time()

        while self.active_tasks and (time.time() - start_time) < timeout:
            time.sleep(1.0)

        # Force shutdown remaining tasks
        for task in self.active_tasks.values():
            task.status = ProcessingStatus.CANCELLED

        # Shutdown worker pool
        self._worker_pool.shutdown(wait=True)

        logger.info("Distributed processing system shutdown complete")


# Global distributed processing manager
_distributed_manager: Optional[DistributedProcessingManager] = None


def get_distributed_manager() -> DistributedProcessingManager:
    """Get global distributed processing manager."""
    global _distributed_manager
    if _distributed_manager is None:
        _distributed_manager = DistributedProcessingManager()
    return _distributed_manager


def init_distributed_processing(max_workers: int = 4, enable_cloud_scaling: bool = True):
    """Initialize distributed processing system."""
    global _distributed_manager
    _distributed_manager = DistributedProcessingManager(
        max_workers=max_workers,
        enable_cloud_scaling=enable_cloud_scaling
    )
    _distributed_manager.start()
    logger.info("Distributed processing initialized")


def shutdown_distributed_processing():
    """Shutdown distributed processing system."""
    global _distributed_manager
    if _distributed_manager:
        _distributed_manager.shutdown()
        _distributed_manager = None
    logger.info("Distributed processing shutdown complete")
