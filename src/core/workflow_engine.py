"""Professional workflow automation engine for 3D printing."""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import uuid
import threading
import queue
from datetime import datetime, timedelta

class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(Enum):
    """Types of workflow tasks."""
    FILE_IMPORT = "file_import"
    MESH_ANALYSIS = "mesh_analysis"
    MESH_REPAIR = "mesh_repair"
    ORIENTATION_OPTIMIZATION = "orientation_optimization"
    SUPPORT_GENERATION = "support_generation"
    SLICING = "slicing"
    GCODE_OPTIMIZATION = "gcode_optimization"
    POST_PROCESSING = "post_processing"
    QUALITY_CHECK = "quality_check"
    FILE_EXPORT = "file_export"
    NOTIFICATION = "notification"

class TaskPriority(Enum):
    """Task execution priority."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

@dataclass
class WorkflowTask:
    """Individual workflow task."""
    id: str
    type: TaskType
    name: str
    description: str
    function: str  # Function name to execute
    parameters: Dict[str, Any]
    dependencies: List[str] = None  # Task IDs this task depends on
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: float = 300.0  # seconds
    retry_count: int = 0
    max_retries: int = 3
    status: WorkflowStatus = WorkflowStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    progress: float = 0.0

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if not self.id:
            self.id = str(uuid.uuid4())

@dataclass
class WorkflowTemplate:
    """Reusable workflow template."""
    id: str
    name: str
    description: str
    category: str
    tasks: List[WorkflowTask]
    estimated_time: float  # minutes
    success_rate: float
    usage_count: int = 0
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

@dataclass
class WorkflowInstance:
    """Active workflow instance."""
    id: str
    template_id: str
    name: str
    status: WorkflowStatus
    tasks: List[WorkflowTask]
    current_task_index: int = 0
    progress: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_estimated_time: float = 0.0
    actual_time: float = 0.0
    success_rate: float = 0.0
    error_log: List[str] = None
    context: Dict[str, Any] = None  # Shared data between tasks

    def __post_init__(self):
        if self.error_log is None:
            self.error_log = []
        if self.context is None:
            self.context = {}
        if not self.id:
            self.id = str(uuid.uuid4())

class WorkflowEngine:
    """Professional workflow automation engine."""

    def __init__(self):
        self.templates = {}
        self.active_workflows = {}
        self.completed_workflows = {}
        self.task_functions = {}
        self.task_queue = queue.PriorityQueue()
        self.worker_threads = []
        self.running = False
        self.max_workers = 4

        self._init_default_templates()
        self._register_task_functions()

    def _init_default_templates(self):
        """Initialize default workflow templates."""

        # Complete 3D printing workflow
        complete_workflow = WorkflowTemplate(
            id="complete_3d_workflow",
            name="Complete 3D Printing Workflow",
            description="Full automated workflow from STL to G-code",
            category="Production",
            estimated_time=25.0,
            success_rate=0.95,
            tasks=[
                WorkflowTask(
                    id="import_model",
                    type=TaskType.FILE_IMPORT,
                    name="Import 3D Model",
                    description="Import and validate 3D model file",
                    function="import_3d_model",
                    parameters={"validate": True, "repair_basic": True}
                ),
                WorkflowTask(
                    id="analyze_mesh",
                    type=TaskType.MESH_ANALYSIS,
                    name="Analyze Mesh Quality",
                    description="Comprehensive mesh analysis",
                    function="analyze_mesh_quality",
                    parameters={"detailed": True, "printability": True},
                    dependencies=["import_model"]
                ),
                WorkflowTask(
                    id="repair_mesh",
                    type=TaskType.MESH_REPAIR,
                    name="Repair Mesh Issues",
                    description="Automatically repair mesh defects",
                    function="repair_mesh_defects",
                    parameters={"auto_repair": True, "preserve_features": True},
                    dependencies=["analyze_mesh"]
                ),
                WorkflowTask(
                    id="optimize_orientation",
                    type=TaskType.ORIENTATION_OPTIMIZATION,
                    name="Optimize Print Orientation",
                    description="Find optimal printing orientation",
                    function="optimize_print_orientation",
                    parameters={"algorithm": "genetic", "iterations": 100},
                    dependencies=["repair_mesh"]
                ),
                WorkflowTask(
                    id="generate_supports",
                    type=TaskType.SUPPORT_GENERATION,
                    name="Generate Support Structures",
                    description="Automatically generate support structures",
                    function="generate_support_structures",
                    parameters={"type": "tree", "density": 15, "overhang_angle": 45},
                    dependencies=["optimize_orientation"]
                ),
                WorkflowTask(
                    id="slice_model",
                    type=TaskType.SLICING,
                    name="Slice Model",
                    description="Generate toolpaths and G-code",
                    function="slice_3d_model",
                    parameters={"quality": "standard", "adaptive_layers": True},
                    dependencies=["generate_supports"]
                ),
                WorkflowTask(
                    id="optimize_gcode",
                    type=TaskType.GCODE_OPTIMIZATION,
                    name="Optimize G-code",
                    description="Optimize G-code for speed and quality",
                    function="optimize_gcode",
                    parameters={"travel_optimization": True, "retraction_optimization": True},
                    dependencies=["slice_model"]
                ),
                WorkflowTask(
                    id="quality_check",
                    type=TaskType.QUALITY_CHECK,
                    name="Final Quality Check",
                    description="Validate final output quality",
                    function="final_quality_check",
                    parameters={"validate_gcode": True, "estimate_time": True},
                    dependencies=["optimize_gcode"]
                )
            ]
        )

        # Quick print workflow
        quick_workflow = WorkflowTemplate(
            id="quick_print_workflow",
            name="Quick Print Workflow",
            description="Fast workflow for simple models",
            category="Quick",
            estimated_time=8.0,
            success_rate=0.90,
            tasks=[
                WorkflowTask(
                    id="quick_import",
                    type=TaskType.FILE_IMPORT,
                    name="Quick Import",
                    description="Quick model import with basic validation",
                    function="import_3d_model",
                    parameters={"validate": False, "repair_basic": False}
                ),
                WorkflowTask(
                    id="quick_slice",
                    type=TaskType.SLICING,
                    name="Quick Slice",
                    description="Fast slicing with default settings",
                    function="slice_3d_model",
                    parameters={"quality": "draft", "adaptive_layers": False},
                    dependencies=["quick_import"]
                )
            ]
        )

        # High quality workflow
        quality_workflow = WorkflowTemplate(
            id="high_quality_workflow",
            name="High Quality Workflow",
            description="Maximum quality workflow for critical parts",
            category="Quality",
            estimated_time=45.0,
            success_rate=0.98,
            tasks=[
                WorkflowTask(
                    id="detailed_import",
                    type=TaskType.FILE_IMPORT,
                    name="Detailed Import",
                    description="Thorough model import and validation",
                    function="import_3d_model",
                    parameters={"validate": True, "repair_basic": True, "detailed_analysis": True}
                ),
                WorkflowTask(
                    id="comprehensive_analysis",
                    type=TaskType.MESH_ANALYSIS,
                    name="Comprehensive Analysis",
                    description="Detailed mesh and printability analysis",
                    function="analyze_mesh_quality",
                    parameters={"detailed": True, "printability": True, "stress_analysis": True},
                    dependencies=["detailed_import"]
                ),
                WorkflowTask(
                    id="professional_repair",
                    type=TaskType.MESH_REPAIR,
                    name="Professional Repair",
                    description="Advanced mesh repair with feature preservation",
                    function="repair_mesh_defects",
                    parameters={"auto_repair": True, "preserve_features": True, "advanced_algorithms": True},
                    dependencies=["comprehensive_analysis"]
                ),
                WorkflowTask(
                    id="multi_objective_orientation",
                    type=TaskType.ORIENTATION_OPTIMIZATION,
                    name="Multi-Objective Orientation",
                    description="Advanced orientation optimization",
                    function="optimize_print_orientation",
                    parameters={"algorithm": "multi_objective", "iterations": 500, "objectives": ["quality", "speed", "support"]},
                    dependencies=["professional_repair"]
                ),
                WorkflowTask(
                    id="smart_supports",
                    type=TaskType.SUPPORT_GENERATION,
                    name="Smart Support Generation",
                    description="Intelligent support structure generation",
                    function="generate_support_structures",
                    parameters={"type": "organic", "density": 12, "overhang_angle": 40, "interface_layers": 3},
                    dependencies=["multi_objective_orientation"]
                ),
                WorkflowTask(
                    id="precision_slicing",
                    type=TaskType.SLICING,
                    name="Precision Slicing",
                    description="High-precision slicing with quality optimization",
                    function="slice_3d_model",
                    parameters={"quality": "high", "adaptive_layers": True, "variable_width": True},
                    dependencies=["smart_supports"]
                ),
                WorkflowTask(
                    id="advanced_post_processing",
                    type=TaskType.POST_PROCESSING,
                    name="Advanced Post-Processing",
                    description="Apply post-processing optimizations",
                    function="apply_post_processing",
                    parameters={"surface_smoothing": True, "dimensional_correction": True},
                    dependencies=["precision_slicing"]
                ),
                WorkflowTask(
                    id="comprehensive_quality_check",
                    type=TaskType.QUALITY_CHECK,
                    name="Comprehensive Quality Check",
                    description="Thorough quality validation and reporting",
                    function="comprehensive_quality_check",
                    parameters={"validate_gcode": True, "simulate_print": True, "generate_report": True},
                    dependencies=["advanced_post_processing"]
                )
            ]
        )

        self.templates = {
            complete_workflow.id: complete_workflow,
            quick_workflow.id: quick_workflow,
            quality_workflow.id: quality_workflow
        }

    def _register_task_functions(self):
        """Register available task functions."""

        self.task_functions = {
            "import_3d_model": self._import_3d_model,
            "analyze_mesh_quality": self._analyze_mesh_quality,
            "repair_mesh_defects": self._repair_mesh_defects,
            "optimize_print_orientation": self._optimize_print_orientation,
            "generate_support_structures": self._generate_support_structures,
            "slice_3d_model": self._slice_3d_model,
            "optimize_gcode": self._optimize_gcode,
            "apply_post_processing": self._apply_post_processing,
            "final_quality_check": self._final_quality_check,
            "comprehensive_quality_check": self._comprehensive_quality_check
        }

    def start_engine(self):
        """Start the workflow engine."""

        if self.running:
            return

        self.running = True

        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_thread, args=(i,))
            worker.daemon = True
            worker.start()
            self.worker_threads.append(worker)

    def stop_engine(self):
        """Stop the workflow engine."""

        self.running = False

        # Wait for workers to finish
        for worker in self.worker_threads:
            worker.join(timeout=5.0)

        self.worker_threads.clear()

    def create_workflow(self, template_id: str, name: str = None, parameters: Dict = None) -> str:
        """Create new workflow instance from template."""

        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        workflow_id = str(uuid.uuid4())

        # Create workflow instance
        workflow = WorkflowInstance(
            id=workflow_id,
            template_id=template_id,
            name=name or f"{template.name} - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            status=WorkflowStatus.PENDING,
            tasks=[task for task in template.tasks],  # Deep copy tasks
            total_estimated_time=template.estimated_time
        )

        # Apply parameter overrides
        if parameters:
            for task in workflow.tasks:
                if task.id in parameters:
                    task.parameters.update(parameters[task.id])

        self.active_workflows[workflow_id] = workflow

        return workflow_id

    def start_workflow(self, workflow_id: str):
        """Start workflow execution."""

        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        if workflow.status != WorkflowStatus.PENDING:
            raise ValueError(f"Workflow {workflow_id} is not in pending state")

        workflow.status = WorkflowStatus.RUNNING
        workflow.start_time = datetime.now()

        # Queue ready tasks
        self._queue_ready_tasks(workflow)

    def pause_workflow(self, workflow_id: str):
        """Pause workflow execution."""

        workflow = self.active_workflows.get(workflow_id)
        if workflow and workflow.status == WorkflowStatus.RUNNING:
            workflow.status = WorkflowStatus.PAUSED

    def resume_workflow(self, workflow_id: str):
        """Resume paused workflow."""

        workflow = self.active_workflows.get(workflow_id)
        if workflow and workflow.status == WorkflowStatus.PAUSED:
            workflow.status = WorkflowStatus.RUNNING
            self._queue_ready_tasks(workflow)

    def cancel_workflow(self, workflow_id: str):
        """Cancel workflow execution."""

        workflow = self.active_workflows.get(workflow_id)
        if workflow:
            workflow.status = WorkflowStatus.CANCELLED
            workflow.end_time = datetime.now()

            # Move to completed workflows
            self.completed_workflows[workflow_id] = workflow
            del self.active_workflows[workflow_id]

    def get_workflow_status(self, workflow_id: str) -> Dict:
        """Get workflow status and progress."""

        workflow = self.active_workflows.get(workflow_id) or self.completed_workflows.get(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        completed_tasks = sum(1 for task in workflow.tasks if task.status == WorkflowStatus.COMPLETED)
        total_tasks = len(workflow.tasks)
        progress = completed_tasks / total_tasks if total_tasks > 0 else 0.0

        return {
            "id": workflow.id,
            "name": workflow.name,
            "status": workflow.status.value,
            "progress": progress,
            "completed_tasks": completed_tasks,
            "total_tasks": total_tasks,
            "current_task": self._get_current_task_info(workflow),
            "estimated_time_remaining": self._estimate_time_remaining(workflow),
            "actual_time": self._calculate_actual_time(workflow),
            "errors": workflow.error_log
        }

    def _queue_ready_tasks(self, workflow: WorkflowInstance):
        """Queue tasks that are ready to execute."""

        for task in workflow.tasks:
            if task.status == WorkflowStatus.PENDING and self._are_dependencies_met(task, workflow):
                # Queue task with priority
                priority = -task.priority.value  # Negative for max priority queue
                self.task_queue.put((priority, time.time(), workflow.id, task.id))
                task.status = WorkflowStatus.RUNNING

    def _are_dependencies_met(self, task: WorkflowTask, workflow: WorkflowInstance) -> bool:
        """Check if task dependencies are satisfied."""

        if not task.dependencies:
            return True

        for dep_id in task.dependencies:
            dep_task = next((t for t in workflow.tasks if t.id == dep_id), None)
            if not dep_task or dep_task.status != WorkflowStatus.COMPLETED:
                return False

        return True

    def _worker_thread(self, worker_id: int):
        """Worker thread for executing tasks."""

        while self.running:
            try:
                # Get task from queue (timeout to allow checking running flag)
                priority, timestamp, workflow_id, task_id = self.task_queue.get(timeout=1.0)

                workflow = self.active_workflows.get(workflow_id)
                if not workflow or workflow.status != WorkflowStatus.RUNNING:
                    continue

                task = next((t for t in workflow.tasks if t.id == task_id), None)
                if not task:
                    continue

                # Execute task
                self._execute_task(workflow, task, worker_id)

                # Check if workflow is complete
                self._check_workflow_completion(workflow)

                # Queue next ready tasks
                if workflow.status == WorkflowStatus.RUNNING:
                    self._queue_ready_tasks(workflow)

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker {worker_id} error: {e}")

    def _execute_task(self, workflow: WorkflowInstance, task: WorkflowTask, worker_id: int):
        """Execute individual task."""

        task.start_time = datetime.now()

        try:
            # Get task function
            task_function = self.task_functions.get(task.function)
            if not task_function:
                raise ValueError(f"Task function {task.function} not found")

            # Execute task with timeout
            result = self._execute_with_timeout(
                task_function,
                args=(workflow.context, task.parameters),
                timeout=task.timeout
            )

            task.result = result
            task.status = WorkflowStatus.COMPLETED
            task.end_time = datetime.now()

            # Update workflow context with result
            workflow.context[task.id] = result

        except Exception as e:
            task.error = str(e)
            task.retry_count += 1

            if task.retry_count <= task.max_retries:
                # Retry task
                task.status = WorkflowStatus.PENDING
                workflow.error_log.append(f"Task {task.name} failed, retrying ({task.retry_count}/{task.max_retries}): {e}")
            else:
                # Task failed permanently
                task.status = WorkflowStatus.FAILED
                task.end_time = datetime.now()
                workflow.status = WorkflowStatus.FAILED
                workflow.error_log.append(f"Task {task.name} failed permanently: {e}")

    def _execute_with_timeout(self, func: Callable, args: tuple, timeout: float):
        """Execute function with timeout."""

        result = [None]
        exception = [None]

        def target():
            try:
                result[0] = func(*args)
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            # Timeout occurred
            thread.join(0)  # Clean up
            raise TimeoutError(f"Task execution timed out after {timeout} seconds")

        if exception[0]:
            raise exception[0]

        return result[0]

    def _check_workflow_completion(self, workflow: WorkflowInstance):
        """Check if workflow is complete."""

        if workflow.status != WorkflowStatus.RUNNING:
            return

        # Check if all tasks are complete or failed
        all_done = all(task.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED] for task in workflow.tasks)

        if all_done:
            failed_tasks = [task for task in workflow.tasks if task.status == WorkflowStatus.FAILED]

            if failed_tasks:
                workflow.status = WorkflowStatus.FAILED
            else:
                workflow.status = WorkflowStatus.COMPLETED

            workflow.end_time = datetime.now()
            workflow.actual_time = (workflow.end_time - workflow.start_time).total_seconds() / 60

            # Calculate success rate
            completed_tasks = sum(1 for task in workflow.tasks if task.status == WorkflowStatus.COMPLETED)
            workflow.success_rate = completed_tasks / len(workflow.tasks)

            # Move to completed workflows
            self.completed_workflows[workflow.id] = workflow
            del self.active_workflows[workflow.id]

    def _get_current_task_info(self, workflow: WorkflowInstance) -> Dict:
        """Get information about current task."""

        running_task = next((task for task in workflow.tasks if task.status == WorkflowStatus.RUNNING), None)

        if running_task:
            return {
                "name": running_task.name,
                "description": running_task.description,
                "progress": running_task.progress,
                "start_time": running_task.start_time.isoformat() if running_task.start_time else None
            }

        return {}

    def _estimate_time_remaining(self, workflow: WorkflowInstance) -> float:
        """Estimate remaining time in minutes."""

        if workflow.status != WorkflowStatus.RUNNING:
            return 0.0

        completed_tasks = sum(1 for task in workflow.tasks if task.status == WorkflowStatus.COMPLETED)
        total_tasks = len(workflow.tasks)

        if completed_tasks == 0:
            return workflow.total_estimated_time

        progress = completed_tasks / total_tasks
        elapsed_time = (datetime.now() - workflow.start_time).total_seconds() / 60

        estimated_total = elapsed_time / progress
        remaining = max(0, estimated_total - elapsed_time)

        return remaining

    def _calculate_actual_time(self, workflow: WorkflowInstance) -> float:
        """Calculate actual elapsed time in minutes."""

        if not workflow.start_time:
            return 0.0

        end_time = workflow.end_time or datetime.now()
        elapsed = (end_time - workflow.start_time).total_seconds() / 60

        return elapsed

    # Task function implementations
    def _import_3d_model(self, context: Dict, parameters: Dict) -> Dict:
        """Import 3D model task."""

        time.sleep(2)  # Simulate processing
        return {
            "file_path": parameters.get("file_path", "model.stl"),
            "format": "STL",
            "vertices": 10000,
            "faces": 20000,
            "valid": True
        }

    def _analyze_mesh_quality(self, context: Dict, parameters: Dict) -> Dict:
        """Analyze mesh quality task."""

        time.sleep(3)  # Simulate processing
        return {
            "quality_score": 0.85,
            "manifold": True,
            "watertight": True,
            "issues": [],
            "printability_score": 0.90
        }

    def _repair_mesh_defects(self, context: Dict, parameters: Dict) -> Dict:
        """Repair mesh defects task."""

        time.sleep(4)  # Simulate processing
        return {
            "repairs_applied": ["fill_holes", "fix_normals"],
            "quality_improvement": 0.05,
            "repaired": True
        }

    def _optimize_print_orientation(self, context: Dict, parameters: Dict) -> Dict:
        """Optimize print orientation task."""

        time.sleep(5)  # Simulate processing
        return {
            "rotation": {"x": 15, "y": 0, "z": 30},
            "support_volume": 0.15,
            "surface_quality": 0.88,
            "overhang_area": 0.05
        }

    def _generate_support_structures(self, context: Dict, parameters: Dict) -> Dict:
        """Generate support structures task."""

        time.sleep(4)  # Simulate processing
        return {
            "support_type": parameters.get("type", "tree"),
            "support_volume": 12.5,
            "support_points": 156,
            "estimated_removal_time": 8.5
        }

    def _slice_3d_model(self, context: Dict, parameters: Dict) -> Dict:
        """Slice 3D model task."""

        time.sleep(6)  # Simulate processing
        return {
            "layer_count": 450,
            "gcode_size": "2.5 MB",
            "estimated_print_time": 185.5,
            "material_usage": 28.7,
            "quality": parameters.get("quality", "standard")
        }

    def _optimize_gcode(self, context: Dict, parameters: Dict) -> Dict:
        """Optimize G-code task."""

        time.sleep(2)  # Simulate processing
        return {
            "time_saved": 12.3,
            "travel_optimized": True,
            "retraction_optimized": True,
            "size_reduction": 0.08
        }

    def _apply_post_processing(self, context: Dict, parameters: Dict) -> Dict:
        """Apply post-processing task."""

        time.sleep(5)  # Simulate processing
        return {
            "operations_applied": ["surface_smoothing", "dimensional_correction"],
            "quality_improvement": 0.12,
            "surface_roughness_reduction": 0.25
        }

    def _final_quality_check(self, context: Dict, parameters: Dict) -> Dict:
        """Final quality check task."""

        time.sleep(3)  # Simulate processing
        return {
            "overall_quality": 0.92,
            "gcode_valid": True,
            "estimated_success_rate": 0.95,
            "ready_for_print": True
        }

    def _comprehensive_quality_check(self, context: Dict, parameters: Dict) -> Dict:
        """Comprehensive quality check task."""

        time.sleep(8)  # Simulate processing
        return {
            "overall_quality": 0.96,
            "detailed_analysis": True,
            "simulation_completed": True,
            "report_generated": True,
            "estimated_success_rate": 0.98
        }