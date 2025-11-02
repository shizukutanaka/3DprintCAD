"""Edge computing integration for low-latency 3D printing operations.

This module enables edge computing capabilities for real-time processing,
reducing latency and improving responsiveness in distributed 3D printing workflows.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

class EdgeNodeType(Enum):
    """Types of edge computing nodes."""
    PRINTER_CONTROLLER = "printer_controller"
    LOCAL_SERVER = "local_server"
    GATEWAY_DEVICE = "gateway_device"
    MOBILE_DEVICE = "mobile_device"

@dataclass
class EdgeNode:
    """Represents an edge computing node."""
    node_id: str
    node_type: EdgeNodeType
    capabilities: List[str] = field(default_factory=list)
    location: str = "unknown"
    status: str = "active"

@dataclass
class EdgeTask:
    """Task to be executed on edge nodes."""
    task_id: str
    task_type: str
    data: Dict[str, Any]
    priority: int = 1
    timeout_seconds: float = 30.0

class EdgeComputingManager:
    """Manages edge computing operations for 3D printing."""

    def __init__(self):
        self.edge_nodes: Dict[str, EdgeNode] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.logger = logging.getLogger(__name__)

    def register_edge_node(self, node: EdgeNode) -> None:
        """Register an edge computing node."""
        self.edge_nodes[node.node_id] = node
        self.logger.info(f"Registered edge node: {node.node_id}")

    async def submit_task(self, task: EdgeTask) -> Any:
        """Submit a task for edge execution."""
        # Find suitable edge node
        suitable_nodes = self._find_suitable_nodes(task)

        if not suitable_nodes:
            self.logger.warning(f"No suitable edge nodes for task: {task.task_id}")
            return None

        # Select best node (simplified)
        target_node = suitable_nodes[0]

        # Execute task on node
        result = await self._execute_task_on_node(target_node, task)
        return result

    def _find_suitable_nodes(self, task: EdgeTask) -> List[EdgeNode]:
        """Find edge nodes suitable for the task."""
        suitable = []

        for node in self.edge_nodes.values():
            if node.status == "active" and task.task_type in node.capabilities:
                suitable.append(node)

        return suitable

    async def _execute_task_on_node(self, node: EdgeNode, task: EdgeTask) -> Any:
        """Execute task on specified edge node."""
        try:
            # Simulate task execution
            await asyncio.sleep(0.1)  # Simulate processing time

            # Execute based on task type
            if task.task_type == "mesh_validation":
                result = self._execute_mesh_validation(task.data)
            elif task.task_type == "gcode_optimization":
                result = self._execute_gcode_optimization(task.data)
            elif task.task_type == "real_time_monitoring":
                result = self._execute_real_time_monitoring(task.data)
            else:
                result = {"status": "unknown_task"}

            self.logger.info(f"Task {task.task_id} completed on node {node.node_id}")
            return result

        except asyncio.TimeoutError:
            self.logger.error(f"Task {task.task_id} timed out on node {node.node_id}")
            return {"status": "timeout"}
        except Exception as e:
            self.logger.error(f"Task {task.task_id} failed on node {node.node_id}: {e}")
            return {"status": "error", "error": str(e)}

    def _execute_mesh_validation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute mesh validation on edge node."""
        # Simplified validation
        return {
            "status": "valid",
            "vertex_count": data.get("vertex_count", 0),
            "face_count": data.get("face_count", 0),
            "watertight": data.get("watertight", False)
        }

    def _execute_gcode_optimization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute G-code optimization on edge node."""
        # Simplified optimization
        return {
            "status": "optimized",
            "original_size": data.get("size", 0),
            "optimized_size": data.get("size", 0) * 0.95,  # 5% reduction
            "print_time_saved": 10  # seconds
        }

    def _execute_real_time_monitoring(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute real-time monitoring on edge node."""
        # Simplified monitoring
        return {
            "status": "monitoring",
            "temperature": data.get("temperature", 25.0),
            "humidity": data.get("humidity", 50.0),
            "print_progress": data.get("progress", 0.0)
        }

    async def start_edge_orchestrator(self):
        """Start the edge computing orchestrator."""
        self.logger.info("Starting edge computing orchestrator")

        while True:
            try:
                # Process tasks from queue
                if not self.task_queue.empty():
                    task = await self.task_queue.get()
                    asyncio.create_task(self.submit_task(task))

                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

            except Exception as e:
                self.logger.error(f"Error in edge orchestrator: {e}")
                await asyncio.sleep(1)

    def get_edge_statistics(self) -> Dict[str, Any]:
        """Get statistics about edge computing operations."""
        return {
            "active_nodes": len([n for n in self.edge_nodes.values() if n.status == "active"]),
            "total_nodes": len(self.edge_nodes),
            "running_tasks": len(self.running_tasks),
            "queued_tasks": self.task_queue.qsize()
        }
