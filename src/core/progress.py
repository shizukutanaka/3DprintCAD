"""Enhanced progress tracking and real-time reporting system."""

from typing import Optional, Callable, Dict, Any, List, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import time
import threading
from queue import Queue, Empty
import json
import uuid
from pathlib import Path
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProgressState(Enum):
    """Progress state enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ProgressLevel(Enum):
    """Progress reporting levels."""
    MINIMAL = 1  # Only major milestones
    NORMAL = 2   # Standard progress updates
    DETAILED = 3 # Detailed step-by-step progress
    VERBOSE = 4  # Maximum detail including internal operations


@dataclass
class ProgressStep:
    """Enhanced single step in progress tracking."""
    name: str
    weight: float = 1.0
    state: ProgressState = ProgressState.PENDING
    progress: float = 0.0
    message: str = ""
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    estimated_duration: Optional[float] = None
    current_operation: Optional[str] = None
    sub_steps: List['ProgressStep'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'weight': self.weight,
            'state': self.state.value,
            'progress': self.progress,
            'message': self.message,
            'error': self.error,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'estimated_duration': self.estimated_duration,
            'current_operation': self.current_operation,
            'sub_steps_count': len(self.sub_steps),
            'metadata': self.metadata
        }


@dataclass
class ProgressTask:
    """Enhanced task with comprehensive progress tracking."""
    task_id: str
    name: str
    steps: List[ProgressStep] = field(default_factory=list)
    current_step: int = 0
    state: ProgressState = ProgressState.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    progress_level: ProgressLevel = ProgressLevel.NORMAL
    update_interval: float = 0.5  # Update every 500ms
    real_time_updates: bool = True

    def add_step(self, name: str, weight: float = 1.0, estimated_duration: Optional[float] = None) -> ProgressStep:
        """Add a progress step."""
        step = ProgressStep(
            name=name,
            weight=weight,
            estimated_duration=estimated_duration
        )
        self.steps.append(step)
        return step

    def get_progress(self) -> float:
        """Calculate overall progress percentage."""
        if not self.steps:
            return 0.0

        total_weight = sum(step.weight for step in self.steps)
        if total_weight == 0:
            return 0.0

        completed_weight = sum(
            step.weight * (step.progress / 100.0)
            for step in self.steps
            if step.state in [ProgressState.COMPLETED, ProgressState.RUNNING]
        )

        return (completed_weight / total_weight) * 100.0

    def get_current_step(self) -> Optional[ProgressStep]:
        """Get currently active step."""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    def get_eta(self) -> Optional[float]:
        """Estimate time to completion."""
        if not self.started_at:
            return None

        elapsed = time.time() - self.started_at
        progress = self.get_progress() / 100.0

        if progress == 0 or progress >= 100:
            return None

        return elapsed * (1.0 - progress) / progress

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'state': self.state.value,
            'progress': self.get_progress(),
            'current_step': self.current_step,
            'total_steps': len(self.steps),
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'eta_seconds': self.get_eta(),
            'steps': [step.to_dict() for step in self.steps[:10]],  # Limit for performance
            'metadata': self.metadata
        }


class ProgressReporter:
    """Real-time progress reporting with multiple output formats."""

    def __init__(self):
        self.tasks: Dict[str, ProgressTask] = {}
        self.listeners: List[Callable[[ProgressTask], None]] = []
        self.update_queue: Queue = Queue()
        self._shutdown_event = threading.Event()
        self._reporter_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Start background reporter
        self._start_reporter()

    def _start_reporter(self):
        """Start background progress reporting thread."""
        def reporter_loop():
            while not self._shutdown_event.is_set():
                try:
                    # Process update queue
                    while True:
                        try:
                            update_data = self.update_queue.get_nowait()
                            self._process_update(update_data)
                        except Empty:
                            break

                    # Periodic cleanup of completed tasks
                    self._cleanup_completed_tasks()

                    time.sleep(0.1)  # Small delay to prevent busy waiting

                except Exception as e:
                    logger.error(f"Progress reporter error: {e}")
                    time.sleep(1.0)

        self._reporter_thread = threading.Thread(target=reporter_loop, daemon=True)
        self._reporter_thread.start()

    def _process_update(self, update_data: Dict[str, Any]):
        """Process a progress update."""
        task_id = update_data.get('task_id')
        if not task_id or task_id not in self.tasks:
            return

        task = self.tasks[task_id]

        # Update step progress
        step_index = update_data.get('step_index', task.current_step)
        if 0 <= step_index < len(task.steps):
            step = task.steps[step_index]

            # Update step fields
            if 'progress' in update_data:
                step.progress = update_data['progress']
            if 'message' in update_data:
                step.message = update_data['message']
            if 'current_operation' in update_data:
                step.current_operation = update_data['current_operation']

            # Auto-complete step if progress is 100%
            if step.progress >= 100.0 and step.state == ProgressState.RUNNING:
                step.state = ProgressState.COMPLETED
                step.completed_at = time.time()

                # Move to next step
                task.current_step += 1
                if task.current_step < len(task.steps):
                    next_step = task.steps[task.current_step]
                    next_step.state = ProgressState.RUNNING
                    next_step.started_at = time.time()

        # Update task state
        if 'state' in update_data:
            task.state = ProgressState(update_data['state'])

        # Update metadata
        if 'metadata' in update_data:
            task.metadata.update(update_data['metadata'])

        # Notify listeners
        for listener in self.listeners:
            try:
                listener(task)
            except Exception as e:
                logger.error(f"Progress listener error: {e}")

    def _cleanup_completed_tasks(self):
        """Remove old completed tasks to prevent memory leaks."""
        current_time = time.time()
        with self._lock:
            completed_tasks = [
                task_id for task_id, task in self.tasks.items()
                if task.state in [ProgressState.COMPLETED, ProgressState.FAILED, ProgressState.CANCELLED]
                and task.completed_at
                and current_time - task.completed_at > 3600  # Keep for 1 hour
            ]

            for task_id in completed_tasks:
                del self.tasks[task_id]

    def create_task(self, name: str, progress_level: ProgressLevel = ProgressLevel.NORMAL) -> str:
        """Create a new progress task."""
        task_id = str(uuid.uuid4())

        with self._lock:
            task = ProgressTask(
                task_id=task_id,
                name=name,
                progress_level=progress_level,
                started_at=time.time()
            )
            self.tasks[task_id] = task

        logger.debug(f"Created progress task: {task_id} - {name}")
        return task_id

    def update_task(self, task_id: str, **updates):
        """Update a progress task."""
        update_data = {'task_id': task_id, **updates}
        self.update_queue.put(update_data)

    def complete_task(self, task_id: str, success: bool = True, error: Optional[str] = None):
        """Mark a task as completed."""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.state = ProgressState.COMPLETED if success else ProgressState.FAILED
                task.completed_at = time.time()
                if error:
                    task.metadata['error'] = error

        logger.info(f"Task completed: {task_id} - {'success' if success else 'failed'}")

    def get_task(self, task_id: str) -> Optional[ProgressTask]:
        """Get a progress task."""
        return self.tasks.get(task_id)

    def add_listener(self, listener: Callable[[ProgressTask], None]):
        """Add a progress update listener."""
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[ProgressTask], None]):
        """Remove a progress update listener."""
        if listener in self.listeners:
            self.listeners.remove(listener)

    def get_active_tasks(self) -> List[ProgressTask]:
        """Get all active tasks."""
        with self._lock:
            return [
                task for task in self.tasks.values()
                if task.state in [ProgressState.PENDING, ProgressState.RUNNING]
            ]

    def export_progress_report(self, file_path: Path):
        """Export comprehensive progress report."""
        with self._lock:
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'total_tasks': len(self.tasks),
                'active_tasks': len(self.get_active_tasks()),
                'tasks': [task.to_dict() for task in self.tasks.values()]
            }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Progress report exported to: {file_path}")


class RealTimeProgressFormatter:
    """Format progress updates for real-time display."""

    def __init__(self, show_percentages: bool = True, show_eta: bool = True,
                 show_current_operation: bool = True, compact_mode: bool = False):
        self.show_percentages = show_percentages
        self.show_eta = show_eta
        self.show_current_operation = show_current_operation
        self.compact_mode = compact_mode

    def format_task(self, task: ProgressTask) -> str:
        """Format a task for display."""
        if self.compact_mode:
            return self._format_compact(task)
        else:
            return self._format_detailed(task)

    def _format_compact(self, task: ProgressTask) -> str:
        """Format in compact mode."""
        progress = task.get_progress()
        status_icon = self._get_status_icon(task.state)

        if self.show_percentages:
            return f"{status_icon} {task.name}: {progress:.1f}%"
        else:
            return f"{status_icon} {task.name}"

    def _format_detailed(self, task: ProgressTask) -> str:
        """Format in detailed mode."""
        progress = task.get_progress()
        status_icon = self._get_status_icon(task.state)

        parts = [f"{status_icon} {task.name}"]

        if self.show_percentages:
            parts.append(f"{progress:.1f}%")

        if self.show_eta and task.started_at:
            eta = task.get_eta()
            if eta:
                eta_str = self._format_duration(eta)
                parts.append(f"ETA: {eta_str}")

        current_step = task.get_current_step()
        if self.show_current_operation and current_step and current_step.current_operation:
            parts.append(f"[{current_step.current_operation}]")

        return " | ".join(parts)

    def _get_status_icon(self, state: ProgressState) -> str:
        """Get icon for progress state."""
        icons = {
            ProgressState.PENDING: "⏳",
            ProgressState.RUNNING: "🔄",
            ProgressState.COMPLETED: "✅",
            ProgressState.FAILED: "❌",
            ProgressState.CANCELLED: "⛔",
            ProgressState.PAUSED: "⏸️"
        }
        return icons.get(state, "❓")

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"


class ProgressManager:
    """Central progress management system."""

    def __init__(self):
        self.reporter = ProgressReporter()
        self.formatters = {
            'compact': RealTimeProgressFormatter(compact_mode=True),
            'detailed': RealTimeProgressFormatter(compact_mode=False),
            'minimal': RealTimeProgressFormatter(show_percentages=False, show_eta=False)
        }

    def create_task(self, name: str, steps: Optional[List[str]] = None,
                   progress_level: ProgressLevel = ProgressLevel.NORMAL) -> str:
        """Create a new progress task with optional steps."""
        task_id = self.reporter.create_task(name, progress_level)

        if steps:
            task = self.reporter.get_task(task_id)
            if task:
                for step_name in steps:
                    task.add_step(step_name)

        return task_id

    def update_progress(self, task_id: str, step_index: Optional[int] = None,
                       progress: Optional[float] = None, message: Optional[str] = None,
                       current_operation: Optional[str] = None):
        """Update progress for a task."""
        updates = {}

        if step_index is not None:
            updates['step_index'] = step_index
        if progress is not None:
            updates['progress'] = progress
        if message is not None:
            updates['message'] = message
        if current_operation is not None:
            updates['current_operation'] = current_operation

        self.reporter.update_task(task_id, **updates)

    def complete_task(self, task_id: str, success: bool = True, error: Optional[str] = None):
        """Complete a progress task."""
        self.reporter.complete_task(task_id, success, error)

    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get progress information for a task."""
        task = self.reporter.get_task(task_id)
        if task:
            return task.to_dict()
        return None

    def format_progress(self, task_id: str, format_type: str = 'detailed') -> str:
        """Format progress for display."""
        task = self.reporter.get_task(task_id)
        if not task:
            return f"Task {task_id} not found"

        formatter = self.formatters.get(format_type, self.formatters['detailed'])
        return formatter.format_task(task)

    def add_progress_listener(self, listener: Callable[[ProgressTask], None]):
        """Add a progress update listener."""
        self.reporter.add_listener(listener)

    def export_progress_report(self, file_path: Path):
        """Export comprehensive progress report."""
        self.reporter.export_progress_report(file_path)


# Global progress manager
_progress_manager: Optional[ProgressManager] = None


def get_progress_manager() -> ProgressManager:
    """Get global progress manager."""
    global _progress_manager
    if _progress_manager is None:
        _progress_manager = ProgressManager()
    return _progress_manager


@contextmanager
def progress_context(name: str, steps: Optional[List[str]] = None,
                    progress_level: ProgressLevel = ProgressLevel.NORMAL):
    """Context manager for automatic progress tracking."""
    manager = get_progress_manager()
    task_id = manager.create_task(name, steps, progress_level)

    try:
        yield task_id
    except Exception as e:
        manager.complete_task(task_id, success=False, error=str(e))
        raise
    else:
        manager.complete_task(task_id, success=True)


class ProgressState(Enum):
    """Progress state enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressStep:
    """Single step in progress tracking."""
    name: str
    weight: float = 1.0
    state: ProgressState = ProgressState.PENDING
    progress: float = 0.0
    message: str = ""
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class ProgressTask:
    """Complete task with multiple steps."""
    task_id: str
    name: str
    steps: List[ProgressStep] = field(default_factory=list)
    current_step: int = 0
    state: ProgressState = ProgressState.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_progress(self) -> float:
        """Calculate overall progress percentage."""
        if not self.steps:
            return 0.0

        total_weight = sum(step.weight for step in self.steps)
        if total_weight == 0:
            return 0.0

        weighted_progress = sum(
            step.progress * step.weight
            for step in self.steps
        )
        return min(100.0, weighted_progress / total_weight)

    def get_eta(self) -> Optional[float]:
        """Estimate time to completion."""
        if not self.started_at or self.state != ProgressState.RUNNING:
            return None

        progress = self.get_progress()
        if progress <= 0:
            return None

        elapsed = time.time() - self.started_at
        if progress >= 100:
            return 0.0

        # Simple linear estimation
        total_time = elapsed / (progress / 100)
        remaining = total_time - elapsed
        return max(0, remaining)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "state": self.state.value,
            "progress": self.get_progress(),
            "eta": self.get_eta(),
            "current_step": self.current_step,
            "steps": [
                {
                    "name": step.name,
                    "state": step.state.value,
                    "progress": step.progress,
                    "message": step.message,
                    "error": step.error
                }
                for step in self.steps
            ],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata
        }


class ProgressTracker:
    """Central progress tracking system."""

    def __init__(self):
        """Initialize progress tracker."""
        self.tasks: Dict[str, ProgressTask] = {}
        self.listeners: List[Callable[[ProgressTask], None]] = []
        self.lock = threading.RLock()
        self.update_queue = Queue()
        self.running = True

        # Start update thread
        self.update_thread = threading.Thread(target=self._process_updates, daemon=True)
        self.update_thread.start()

    def create_task(
        self,
        task_id: str,
        name: str,
        steps: List[str],
        weights: Optional[List[float]] = None
    ) -> ProgressTask:
        """Create a new progress task.

        Args:
            task_id: Unique task identifier
            name: Task name
            steps: List of step names
            weights: Optional weights for each step

        Returns:
            Created ProgressTask
        """
        if weights is None:
            weights = [1.0] * len(steps)

        progress_steps = [
            ProgressStep(name=step, weight=weight)
            for step, weight in zip(steps, weights)
        ]

        task = ProgressTask(
            task_id=task_id,
            name=name,
            steps=progress_steps
        )

        with self.lock:
            self.tasks[task_id] = task

        self._notify_listeners(task)
        return task

    def start_task(self, task_id: str) -> None:
        """Start a task."""
        with self.lock:
            if task_id not in self.tasks:
                return

            task = self.tasks[task_id]
            task.state = ProgressState.RUNNING
            task.started_at = time.time()

            if task.steps:
                task.steps[0].state = ProgressState.RUNNING
                task.steps[0].started_at = time.time()

        self._notify_listeners(task)

    def update_step(
        self,
        task_id: str,
        step_index: int,
        progress: Optional[float] = None,
        message: Optional[str] = None
    ) -> None:
        """Update progress for a specific step.

        Args:
            task_id: Task identifier
            step_index: Index of step to update
            progress: Progress percentage (0-100)
            message: Optional status message
        """
        with self.lock:
            if task_id not in self.tasks:
                return

            task = self.tasks[task_id]
            if step_index >= len(task.steps):
                return

            step = task.steps[step_index]

            if progress is not None:
                step.progress = min(100.0, max(0.0, progress))

            if message is not None:
                step.message = message

            if step.state == ProgressState.PENDING:
                step.state = ProgressState.RUNNING
                step.started_at = time.time()

        self._notify_listeners(task)

    def complete_step(self, task_id: str, step_index: int) -> None:
        """Mark a step as completed."""
        with self.lock:
            if task_id not in self.tasks:
                return

            task = self.tasks[task_id]
            if step_index >= len(task.steps):
                return

            step = task.steps[step_index]
            step.state = ProgressState.COMPLETED
            step.progress = 100.0
            step.completed_at = time.time()

            # Start next step if available
            next_index = step_index + 1
            if next_index < len(task.steps):
                task.current_step = next_index
                next_step = task.steps[next_index]
                next_step.state = ProgressState.RUNNING
                next_step.started_at = time.time()
            else:
                # All steps completed
                task.state = ProgressState.COMPLETED
                task.completed_at = time.time()

        self._notify_listeners(task)

    def fail_task(self, task_id: str, error: str) -> None:
        """Mark a task as failed."""
        with self.lock:
            if task_id not in self.tasks:
                return

            task = self.tasks[task_id]
            task.state = ProgressState.FAILED
            task.completed_at = time.time()

            # Mark current step as failed
            if task.current_step < len(task.steps):
                step = task.steps[task.current_step]
                step.state = ProgressState.FAILED
                step.error = error
                step.completed_at = time.time()

        self._notify_listeners(task)

    def cancel_task(self, task_id: str) -> None:
        """Cancel a task."""
        with self.lock:
            if task_id not in self.tasks:
                return

            task = self.tasks[task_id]
            task.state = ProgressState.CANCELLED
            task.completed_at = time.time()

            # Cancel current step
            if task.current_step < len(task.steps):
                step = task.steps[task.current_step]
                if step.state == ProgressState.RUNNING:
                    step.state = ProgressState.CANCELLED
                    step.completed_at = time.time()

        self._notify_listeners(task)

    def get_task(self, task_id: str) -> Optional[ProgressTask]:
        """Get task by ID."""
        with self.lock:
            return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[ProgressTask]:
        """Get all tasks."""
        with self.lock:
            return list(self.tasks.values())

    def get_active_tasks(self) -> List[ProgressTask]:
        """Get currently running tasks."""
        with self.lock:
            return [
                task for task in self.tasks.values()
                if task.state == ProgressState.RUNNING
            ]

    def add_listener(self, listener: Callable[[ProgressTask], None]) -> None:
        """Add a progress listener.

        Args:
            listener: Function to call on progress updates
        """
        with self.lock:
            self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[ProgressTask], None]) -> None:
        """Remove a progress listener."""
        with self.lock:
            if listener in self.listeners:
                self.listeners.remove(listener)

    def clear_completed(self) -> None:
        """Remove completed and failed tasks."""
        with self.lock:
            completed_ids = [
                task_id for task_id, task in self.tasks.items()
                if task.state in (ProgressState.COMPLETED, ProgressState.FAILED, ProgressState.CANCELLED)
            ]
            for task_id in completed_ids:
                del self.tasks[task_id]

    def _notify_listeners(self, task: ProgressTask) -> None:
        """Notify all listeners of progress update."""
        self.update_queue.put(task)

    def _process_updates(self) -> None:
        """Process update queue in background thread."""
        while self.running:
            try:
                task = self.update_queue.get(timeout=1.0)
                with self.lock:
                    listeners = self.listeners.copy()

                for listener in listeners:
                    try:
                        listener(task)
                    except Exception:
                        pass  # Ignore listener errors

            except:
                continue

    def shutdown(self) -> None:
        """Shutdown progress tracker."""
        self.running = False
        if self.update_thread.is_alive():
            self.update_thread.join(timeout=2.0)


# Global progress tracker instance
_tracker = ProgressTracker()


class ProgressContext:
    """Context manager for progress tracking."""

    def __init__(
        self,
        task_id: str,
        name: str,
        steps: List[str],
        weights: Optional[List[float]] = None
    ):
        """Initialize progress context.

        Args:
            task_id: Unique task identifier
            name: Task name
            steps: List of step names
            weights: Optional weights for each step
        """
        self.task_id = task_id
        self.name = name
        self.steps = steps
        self.weights = weights
        self.task = None
        self.current_step = 0

    def __enter__(self):
        """Enter context."""
        self.task = _tracker.create_task(
            self.task_id,
            self.name,
            self.steps,
            self.weights
        )
        _tracker.start_task(self.task_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if exc_type is not None:
            _tracker.fail_task(self.task_id, str(exc_val))
        elif self.task.state == ProgressState.RUNNING:
            # Complete remaining steps
            for i in range(self.current_step, len(self.steps)):
                _tracker.complete_step(self.task_id, i)

    def update(self, progress: float, message: str = "") -> None:
        """Update current step progress."""
        _tracker.update_step(
            self.task_id,
            self.current_step,
            progress,
            message
        )

    def next_step(self) -> None:
        """Move to next step."""
        _tracker.complete_step(self.task_id, self.current_step)
        self.current_step += 1


def get_progress_tracker() -> ProgressTracker:
    """Get global progress tracker instance."""
    return _tracker


def track_progress(
    task_id: str,
    name: str,
    steps: List[str],
    weights: Optional[List[float]] = None
) -> ProgressContext:
    """Create a progress tracking context.

    Args:
        task_id: Unique task identifier
        name: Task name
        steps: List of step names
        weights: Optional weights for each step

    Returns:
        ProgressContext for tracking progress
    """
    return ProgressContext(task_id, name, steps, weights)