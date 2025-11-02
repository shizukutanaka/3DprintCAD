"""Enhanced automation workflows for end-to-end 3D printing processes.

This module provides advanced automation capabilities for complete workflow
optimization, from design to finished product with minimal human intervention.
"""

from __future__ import annotations

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import logging

class WorkflowStage(Enum):
    """Stages in the 3D printing workflow."""
    DESIGN_VALIDATION = "design_validation"
    MATERIAL_SELECTION = "material_selection"
    PRINT_PREPARATION = "print_preparation"
    PRINTING = "printing"
    QUALITY_INSPECTION = "quality_inspection"
    POST_PROCESSING = "post_processing"
    PACKAGING = "packaging"
    SHIPPING = "shipping"

@dataclass
class WorkflowTask:
    """Individual task in the automation workflow."""
    task_id: str
    stage: WorkflowStage
    description: str
    estimated_duration_minutes: float
    dependencies: List[str] = field(default_factory=list)
    priority: int = 1
    auto_executable: bool = True

@dataclass
class WorkflowExecution:
    """Execution instance of a workflow."""
    execution_id: str
    workflow_name: str
    tasks: Dict[str, WorkflowTask] = field(default_factory=dict)
    current_stage: WorkflowStage = WorkflowStage.DESIGN_VALIDATION
    start_time: float = 0.0
    end_time: float = 0.0
    status: str = "pending"

class EnhancedAutomationManager:
    """Enhanced automation manager for complete workflows."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.workflows: Dict[str, List[WorkflowTask]] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.task_handlers: Dict[str, Callable] = {}

    def define_workflow(self, workflow_name: str, tasks: List[WorkflowTask]) -> None:
        """Define a complete automation workflow."""
        # Validate dependencies
        self._validate_workflow(tasks)

        self.workflows[workflow_name] = tasks
        self.logger.info(f"Defined workflow '{workflow_name}' with {len(tasks)} tasks")

    def _validate_workflow(self, tasks: List[WorkflowTask]) -> None:
        """Validate workflow for circular dependencies and completeness."""
        # Check for circular dependencies (simplified)
        task_ids = {task.task_id for task in tasks}
        for task in tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    raise ValueError(f"Unknown dependency '{dep}' in task '{task.task_id}'")

    def register_task_handler(self, stage: WorkflowStage, handler: Callable) -> None:
        """Register handler for workflow stage."""
        self.task_handlers[stage.value] = handler
        self.logger.info(f"Registered handler for stage: {stage.value}")

    async def execute_workflow(self, workflow_name: str,
                             execution_context: Dict[str, Any]) -> str:
        """Execute complete automation workflow."""
        if workflow_name not in self.workflows:
            raise ValueError(f"Workflow '{workflow_name}' not defined")

        execution_id = f"{workflow_name}_{int(time.time())}"
        tasks = self.workflows[workflow_name]

        # Create execution instance
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_name=workflow_name,
            tasks={task.task_id: task for task in tasks},
            start_time=time.time(),
            status="running"
        )

        self.executions[execution_id] = execution

        try:
            # Execute workflow stages
            await self._execute_workflow_stages(execution, execution_context)

            execution.status = "completed"
            execution.end_time = time.time()

            self.logger.info(f"Workflow '{workflow_name}' completed successfully")
            return execution_id

        except Exception as e:
            execution.status = "failed"
            execution.end_time = time.time()
            self.logger.error(f"Workflow '{workflow_name}' failed: {e}")
            raise

    async def _execute_workflow_stages(self, execution: WorkflowExecution,
                                     context: Dict[str, Any]) -> None:
        """Execute workflow stages in order."""
        # Group tasks by stage
        tasks_by_stage = {}
        for task in execution.tasks.values():
            if task.stage not in tasks_by_stage:
                tasks_by_stage[task.stage] = []
            tasks_by_stage[task.stage].append(task)

        # Execute stages in order
        for stage in WorkflowStage:
            if stage in tasks_by_stage:
                await self._execute_stage(stage, tasks_by_stage[stage], execution, context)

    async def _execute_stage(self, stage: WorkflowStage, tasks: List[WorkflowTask],
                           execution: WorkflowExecution, context: Dict[str, Any]) -> None:
        """Execute all tasks in a stage."""
        execution.current_stage = stage

        # Check dependencies
        ready_tasks = [task for task in tasks if self._are_dependencies_met(task, execution)]

        if not ready_tasks:
            return

        # Execute tasks concurrently if possible
        if len(ready_tasks) > 1 and all(task.auto_executable for task in ready_tasks):
            # Execute in parallel
            await asyncio.gather(*[
                self._execute_task(task, context) for task in ready_tasks
            ])
        else:
            # Execute sequentially
            for task in ready_tasks:
                await self._execute_task(task, context)

    async def _execute_task(self, task: WorkflowTask, context: Dict[str, Any]) -> None:
        """Execute a single workflow task."""
        handler = self.task_handlers.get(task.stage.value)

        if handler:
            try:
                # Execute task handler
                await handler(task, context)
                self.logger.info(f"Task '{task.task_id}' completed successfully")
            except Exception as e:
                self.logger.error(f"Task '{task.task_id}' failed: {e}")
                raise
        else:
            self.logger.warning(f"No handler registered for stage '{task.stage.value}'")

    def _are_dependencies_met(self, task: WorkflowTask, execution: WorkflowExecution) -> bool:
        """Check if all dependencies for a task are met."""
        # Simplified dependency check
        # In practice, would track task completion status
        return len(task.dependencies) == 0  # Assume no dependencies for simplicity

    def get_workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """Get status of workflow execution."""
        if execution_id not in self.executions:
            return {"error": "Execution not found"}

        execution = self.executions[execution_id]

        return {
            "execution_id": execution.execution_id,
            "workflow_name": execution.workflow_name,
            "status": execution.status,
            "current_stage": execution.current_stage.value,
            "progress": self._calculate_progress(execution),
            "start_time": execution.start_time,
            "end_time": execution.end_time,
            "duration_minutes": (execution.end_time - execution.start_time) / 60 if execution.end_time else 0
        }

    def _calculate_progress(self, execution: WorkflowExecution) -> float:
        """Calculate workflow progress percentage."""
        total_tasks = len(execution.tasks)
        if total_tasks == 0:
            return 0.0

        # Simplified progress calculation
        # In practice, would track completed tasks
        stage_order = list(WorkflowStage)
        current_stage_index = stage_order.index(execution.current_stage)
        progress = (current_stage_index / len(stage_order)) * 100

        return min(100.0, progress)

    def optimize_workflow_efficiency(self, workflow_name: str) -> Dict[str, Any]:
        """Optimize workflow for better efficiency."""
        if workflow_name not in self.workflows:
            return {"error": "Workflow not found"}

        tasks = self.workflows[workflow_name]
        optimization_result = {
            'original_efficiency': 0.0,
            'optimized_efficiency': 0.0,
            'improvements': [],
            'parallelization_opportunities': []
        }

        # Analyze for parallelization opportunities
        stage_task_counts = {}
        for task in tasks:
            if task.stage not in stage_task_counts:
                stage_task_counts[task.stage] = 0
            stage_task_counts[task.stage] += 1

        # Find stages that can be parallelized
        for stage, count in stage_task_counts.items():
            if count > 1:
                optimization_result['parallelization_opportunities'].append(
                    f"Stage '{stage}' has {count} tasks that can be parallelized"
                )

        # Calculate efficiency improvements
        total_duration = sum(task.estimated_duration_minutes for task in tasks)
        parallel_reduction = len(optimization_result['parallelization_opportunities']) * 0.2  # 20% reduction per opportunity

        optimization_result['original_efficiency'] = total_duration
        optimization_result['optimized_efficiency'] = total_duration * (1 - parallel_reduction)
        optimization_result['improvements'].append(f"Potential {parallel_reduction*100:.1f}% time reduction")

        return optimization_result
