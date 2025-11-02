"""Workflow optimizer for enhanced automation processes.

This module provides intelligent workflow optimization and scheduling
for maximum efficiency in 3D printing operations.
"""

from __future__ import annotations

import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

class OptimizationStrategy(Enum):
    """Strategies for workflow optimization."""
    PARALLEL_EXECUTION = "parallel_execution"
    RESOURCE_ALLOCATION = "resource_allocation"
    TIME_WINDOW_OPTIMIZATION = "time_window_optimization"
    DEPENDENCY_REDUCTION = "dependency_reduction"

@dataclass
class WorkflowNode:
    """Node in the workflow graph."""
    task_id: str
    stage: str
    duration: float
    dependencies: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)

class WorkflowOptimizer:
    """Optimizer for 3D printing workflows."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.optimization_strategies: List[OptimizationStrategy] = []
        self.workflow_graph: Dict[str, WorkflowNode] = {}

    def build_workflow_graph(self, tasks: List[Dict[str, Any]]) -> None:
        """Build workflow dependency graph."""
        self.workflow_graph.clear()

        for task in tasks:
            node = WorkflowNode(
                task_id=task['task_id'],
                stage=task['stage'],
                duration=task['duration'],
                dependencies=task.get('dependencies', []),
                resources=task.get('resources', [])
            )
            self.workflow_graph[task['task_id']] = node

        self.logger.info(f"Built workflow graph with {len(self.workflow_graph)} nodes")

    def optimize_workflow(self, optimization_goals: List[str]) -> Dict[str, Any]:
        """Optimize workflow based on specified goals."""
        optimization_result = {
            'original_duration': self._calculate_critical_path(),
            'optimized_duration': 0.0,
            'improvements': [],
            'resource_utilization': {},
            'bottlenecks': []
        }

        # Apply optimization strategies
        for strategy in self.optimization_strategies:
            if strategy == OptimizationStrategy.PARALLEL_EXECUTION:
                improvement = self._optimize_parallel_execution()
                optimization_result['improvements'].append(improvement)

            elif strategy == OptimizationStrategy.RESOURCE_ALLOCATION:
                utilization = self._optimize_resource_allocation()
                optimization_result['resource_utilization'] = utilization

        # Recalculate optimized duration
        optimization_result['optimized_duration'] = self._calculate_critical_path()

        # Identify bottlenecks
        optimization_result['bottlenecks'] = self._identify_bottlenecks()

        return optimization_result

    def _calculate_critical_path(self) -> float:
        """Calculate the critical path duration."""
        # Simplified critical path calculation
        if not self.workflow_graph:
            return 0.0

        # Use topological sort to find longest path
        durations = {}
        for node_id, node in self.workflow_graph.items():
            durations[node_id] = node.duration

        # Simple approximation for demonstration
        total_duration = sum(node.duration for node in self.workflow_graph.values())

        return total_duration

    def _optimize_parallel_execution(self) -> str:
        """Optimize for parallel execution."""
        # Identify tasks that can run in parallel
        parallel_candidates = []

        for node_id, node in self.workflow_graph.items():
            if len(node.dependencies) == 0:  # No dependencies
                parallel_candidates.append(node_id)

        return f"Identified {len(parallel_candidates)} tasks for parallel execution"

    def _optimize_resource_allocation(self) -> Dict[str, float]:
        """Optimize resource allocation."""
        resource_usage = {}

        for node in self.workflow_graph.values():
            for resource in node.resources:
                if resource not in resource_usage:
                    resource_usage[resource] = 0.0
                resource_usage[resource] += node.duration

        # Normalize to utilization percentage
        max_usage = max(resource_usage.values()) if resource_usage else 1.0
        for resource in resource_usage:
            resource_usage[resource] = (resource_usage[resource] / max_usage) * 100

        return resource_usage

    def _identify_bottlenecks(self) -> List[str]:
        """Identify workflow bottlenecks."""
        bottlenecks = []

        # Find tasks with many dependencies (simplified)
        for node_id, node in self.workflow_graph.items():
            if len(node.dependencies) > 2:
                bottlenecks.append(f"Task '{node_id}' has {len(node.dependencies)} dependencies")

        return bottlenecks

    def add_optimization_strategy(self, strategy: OptimizationStrategy) -> None:
        """Add optimization strategy."""
        if strategy not in self.optimization_strategies:
            self.optimization_strategies.append(strategy)
            self.logger.info(f"Added optimization strategy: {strategy.value}")

    def generate_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        report = {
            'workflow_efficiency': self._assess_workflow_efficiency(),
            'resource_efficiency': self._assess_resource_efficiency(),
            'automation_potential': self._assess_automation_potential(),
            'recommendations': self._generate_optimization_recommendations()
        }

        return report

    def _assess_workflow_efficiency(self) -> Dict[str, float]:
        """Assess overall workflow efficiency."""
        if not self.workflow_graph:
            return {'efficiency_score': 0.0}

        # Simple efficiency metrics
        total_duration = sum(node.duration for node in self.workflow_graph.values())
        num_tasks = len(self.workflow_graph)

        # Efficiency based on duration per task
        efficiency_score = min(1.0, 100 / (total_duration / max(num_tasks, 1)))

        return {
            'efficiency_score': efficiency_score,
            'total_duration': total_duration,
            'average_task_duration': total_duration / num_tasks
        }

    def _assess_resource_efficiency(self) -> Dict[str, float]:
        """Assess resource utilization efficiency."""
        resource_usage = self._optimize_resource_allocation()

        # Calculate average utilization
        if resource_usage:
            avg_utilization = sum(resource_usage.values()) / len(resource_usage)
        else:
            avg_utilization = 0.0

        return {
            'average_utilization': avg_utilization,
            'resource_usage': resource_usage
        }

    def _assess_automation_potential(self) -> Dict[str, Any]:
        """Assess potential for automation."""
        # Count tasks that can be automated
        automatable_tasks = 0
        total_tasks = len(self.workflow_graph)

        for node in self.workflow_graph.values():
            # Simple heuristic: tasks with no human resources can be automated
            if not any("human" in resource.lower() for resource in node.resources):
                automatable_tasks += 1

        automation_potential = (automatable_tasks / total_tasks) * 100 if total_tasks > 0 else 0.0

        return {
            'automation_potential_percent': automation_potential,
            'automatable_tasks': automatable_tasks,
            'total_tasks': total_tasks
        }

    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []

        efficiency = self._assess_workflow_efficiency()
        if efficiency['efficiency_score'] < 0.5:
            recommendations.append("Consider reducing task dependencies to improve parallelization")

        resource_eff = self._assess_resource_efficiency()
        if resource_eff['average_utilization'] < 50:
            recommendations.append("Optimize resource allocation for better utilization")

        automation = self._assess_automation_potential()
        if automation['automation_potential_percent'] < 70:
            recommendations.append("Increase automation potential by reducing manual tasks")

        if not recommendations:
            recommendations.append("Workflow is well-optimized")

        return recommendations
