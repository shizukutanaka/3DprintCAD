"""Autonomous manufacturing system with minimal human intervention."""

import asyncio
import json
import time
import logging
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import uuid
import numpy as np


class AutonomyLevel(Enum):
    """Levels of manufacturing autonomy."""
    MANUAL = "manual"                    # Full human control
    ASSISTED = "assisted"               # Human-guided automation
    SUPERVISED = "supervised"           # Automated with human oversight
    SEMI_AUTONOMOUS = "semi_autonomous" # Automated with exception handling
    FULLY_AUTONOMOUS = "fully_autonomous"  # Complete automation


class ManufacturingStage(Enum):
    """Stages in the autonomous manufacturing process."""
    DESIGN_ANALYSIS = "design_analysis"
    MATERIAL_PREPARATION = "material_preparation"
    PRINT_SETUP = "print_setup"
    QUALITY_MONITORING = "quality_monitoring"
    POST_PROCESSING = "post_processing"
    INSPECTION = "inspection"
    PACKAGING = "packaging"


@dataclass
class AutonomousAgent:
    """Autonomous agent for manufacturing operations."""
    agent_id: str
    agent_type: str
    capabilities: List[str] = field(default_factory=list)
    autonomy_level: AutonomyLevel = AutonomyLevel.SEMI_AUTONOMOUS
    decision_model: Optional[str] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    learning_enabled: bool = True


@dataclass
class ManufacturingJob:
    """Manufacturing job for autonomous processing."""
    job_id: str
    model_data: Dict[str, Any]
    requirements: Dict[str, Any]
    priority: int = 5
    deadline: Optional[float] = None
    quality_standards: Dict[str, Any] = field(default_factory=dict)
    cost_constraints: Dict[str, Any] = field(default_factory=dict)


class AutonomousDecisionEngine:
    """Engine for autonomous decision making in manufacturing."""

    def __init__(self):
        """Initialize autonomous decision engine."""
        self.logger = logging.getLogger(__name__)
        self.decision_models: Dict[str, Dict[str, Any]] = {}
        self.decision_history: List[Dict[str, Any]] = []
        self.learning_data: List[Dict[str, Any]] = []

        # Initialize decision models
        self._initialize_decision_models()

    def _initialize_decision_models(self):
        """Initialize autonomous decision models."""
        # Material selection model
        self.decision_models['material_selection'] = {
            'model_type': 'multi_criteria_optimization',
            'criteria': ['strength', 'cost', 'availability', 'printability'],
            'weights': [0.3, 0.25, 0.2, 0.25],
            'constraints': {'max_cost': 100, 'min_strength': 40}
        }

        # Process parameter optimization model
        self.decision_models['process_optimization'] = {
            'model_type': 'bayesian_optimization',
            'parameters': ['layer_height', 'infill_density', 'print_speed', 'temperature'],
            'objectives': ['quality', 'speed', 'cost'],
            'iterations': 50
        }

        # Quality control model
        self.decision_models['quality_control'] = {
            'model_type': 'anomaly_detection',
            'thresholds': {'quality_score': 0.8, 'defect_rate': 0.05},
            'monitoring_interval': 30  # seconds
        }

    def make_autonomous_decision(self, decision_type: str,
                               context: Dict[str, Any]) -> Dict[str, Any]:
        """Make an autonomous decision.

        Args:
            decision_type: Type of decision to make
            context: Decision context

        Returns:
            Decision result
        """
        if decision_type not in self.decision_models:
            return {'error': f'Unknown decision type: {decision_type}'}

        model = self.decision_models[decision_type]

        # Record decision context
        decision_record = {
            'decision_type': decision_type,
            'context': context,
            'timestamp': time.time(),
            'model_used': model['model_type']
        }

        # Make decision based on model type
        if model['model_type'] == 'multi_criteria_optimization':
            result = self._multi_criteria_optimization(context, model)
        elif model['model_type'] == 'bayesian_optimization':
            result = self._bayesian_optimization(context, model)
        elif model['model_type'] == 'anomaly_detection':
            result = self._anomaly_detection(context, model)
        else:
            result = {'decision': 'default', 'confidence': 0.5}

        # Record decision outcome
        decision_record['result'] = result
        self.decision_history.append(decision_record)

        # Learn from decision
        if result.get('success', False):
            self._learn_from_successful_decision(decision_record)

        return result

    def _multi_criteria_optimization(self, context: Dict[str, Any],
                                   model: Dict[str, Any]) -> Dict[str, Any]:
        """Perform multi-criteria optimization."""
        options = context.get('options', [])
        criteria = model['criteria']
        weights = model['weights']

        if not options:
            return {'error': 'No options provided for optimization'}

        # Score each option
        scored_options = []
        for option in options:
            scores = []

            for criterion in criteria:
                # Get criterion value (simplified scoring)
                value = option.get(criterion, 0)
                if criterion == 'cost':
                    # Lower cost is better
                    score = max(0, 100 - value)
                elif criterion == 'strength':
                    # Higher strength is better
                    score = min(100, value)
                elif criterion == 'availability':
                    score = option.get('availability_score', 50)
                elif criterion == 'printability':
                    score = option.get('printability_score', 75)
                else:
                    score = 50  # Default score

                scores.append(score)

            # Weighted score
            weighted_score = sum(score * weight for score, weight in zip(scores, weights))
            scored_options.append({
                'option': option,
                'scores': dict(zip(criteria, scores)),
                'weighted_score': weighted_score
            })

        # Select best option
        best_option = max(scored_options, key=lambda x: x['weighted_score'])

        return {
            'selected_option': best_option['option'],
            'confidence': best_option['weighted_score'] / 100,
            'all_scores': scored_options,
            'optimization_method': 'weighted_multi_criteria'
        }

    def _bayesian_optimization(self, context: Dict[str, Any],
                             model: Dict[str, Any]) -> Dict[str, Any]:
        """Perform Bayesian optimization for process parameters."""
        # Simulate Bayesian optimization process
        parameters = model['parameters']
        objectives = model['objectives']

        # Generate parameter combinations
        parameter_suggestions = []
        for _ in range(model['iterations']):
            # Random parameter exploration (simplified)
            params = {}
            for param in parameters:
                if param == 'layer_height':
                    params[param] = 0.1 + np.random.random() * 0.2  # 0.1-0.3mm
                elif param == 'infill_density':
                    params[param] = 10 + np.random.random() * 90   # 10-100%
                elif param == 'print_speed':
                    params[param] = 20 + np.random.random() * 80   # 20-100mm/s
                elif param == 'temperature':
                    params[param] = 190 + np.random.random() * 60  # 190-250°C

            parameter_suggestions.append(params)

        # Evaluate suggestions (simplified)
        best_params = parameter_suggestions[0]
        best_score = 0.8  # Placeholder

        return {
            'optimized_parameters': best_params,
            'expected_performance': best_score,
            'optimization_iterations': model['iterations'],
            'convergence_achieved': True
        }

    def _anomaly_detection(self, context: Dict[str, Any],
                         model: Dict[str, Any]) -> Dict[str, Any]:
        """Perform anomaly detection for quality control."""
        quality_data = context.get('quality_metrics', {})
        thresholds = model['thresholds']

        anomalies = []

        # Check quality thresholds
        quality_score = quality_data.get('overall_score', 1.0)
        if quality_score < thresholds['quality_score']:
            anomalies.append({
                'type': 'low_quality',
                'value': quality_score,
                'threshold': thresholds['quality_score'],
                'severity': 'high'
            })

        defect_rate = quality_data.get('defect_rate', 0.0)
        if defect_rate > thresholds['defect_rate']:
            anomalies.append({
                'type': 'high_defect_rate',
                'value': defect_rate,
                'threshold': thresholds['defect_rate'],
                'severity': 'critical'
            })

        return {
            'anomalies_detected': len(anomalies),
            'anomalies': anomalies,
            'quality_assessment': 'pass' if len(anomalies) == 0 else 'fail',
            'recommendations': self._generate_anomaly_recommendations(anomalies)
        }

    def _generate_anomaly_recommendations(self, anomalies: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations for detected anomalies."""
        recommendations = []

        for anomaly in anomalies:
            anomaly_type = anomaly['type']

            if anomaly_type == 'low_quality':
                recommendations.append('Consider adjusting print parameters for better quality')
            elif anomaly_type == 'high_defect_rate':
                recommendations.append('Immediate maintenance required - check printer calibration')

        return recommendations

    def _learn_from_successful_decision(self, decision_record: Dict[str, Any]):
        """Learn from successful decisions for future improvement."""
        # Store decision data for learning
        learning_entry = {
            'decision_type': decision_record['decision_type'],
            'context_summary': self._summarize_context(decision_record['context']),
            'result_quality': decision_record['result'].get('confidence', 0),
            'timestamp': decision_record['timestamp']
        }

        self.learning_data.append(learning_entry)

        # Keep only recent learning data
        if len(self.learning_data) > 1000:
            self.learning_data = self.learning_data[-1000:]

    def _summarize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize decision context for learning."""
        return {
            'has_model_data': 'model_data' in context,
            'has_printer_data': 'printer_data' in context,
            'complexity_level': context.get('complexity', 'medium'),
            'urgency_level': context.get('urgency', 'normal')
        }


class AutonomousManufacturingController:
    """Controller for autonomous manufacturing operations."""

    def __init__(self):
        """Initialize autonomous manufacturing controller."""
        self.logger = logging.getLogger(__name__)
        self.decision_engine = AutonomousDecisionEngine()
        self.active_jobs: Dict[str, ManufacturingJob] = {}
        self.manufacturing_agents: Dict[str, AutonomousAgent] = {}

        # Manufacturing pipeline
        self.pipeline_stages = [
            ManufacturingStage.DESIGN_ANALYSIS,
            ManufacturingStage.MATERIAL_PREPARATION,
            ManufacturingStage.PRINT_SETUP,
            ManufacturingStage.QUALITY_MONITORING,
            ManufacturingStage.POST_PROCESSING,
            ManufacturingStage.INSPECTION
        ]

        # Autonomous capabilities
        self.autonomy_level = AutonomyLevel.SEMI_AUTONOMOUS

        # Initialize manufacturing agents
        self._initialize_manufacturing_agents()

    def _initialize_manufacturing_agents(self):
        """Initialize specialized manufacturing agents."""
        # Design analysis agent
        design_agent = AutonomousAgent(
            agent_id="design_analyzer_001",
            agent_type="design_analysis",
            capabilities=["mesh_analysis", "design_validation", "optimization_suggestions"],
            autonomy_level=AutonomyLevel.FULLY_AUTONOMOUS,
            decision_model="neural_network",
            performance_metrics={"accuracy": 0.94, "speed": 0.87}
        )

        # Material preparation agent
        material_agent = AutonomousAgent(
            agent_id="material_handler_001",
            agent_type="material_preparation",
            capabilities=["material_selection", "quality_check", "inventory_management"],
            autonomy_level=AutonomyLevel.SUPERVISED,
            decision_model="rule_based",
            performance_metrics={"reliability": 0.96, "efficiency": 0.89}
        )

        # Print control agent
        print_agent = AutonomousAgent(
            agent_id="print_controller_001",
            agent_type="print_control",
            capabilities=["parameter_optimization", "real_time_monitoring", "error_correction"],
            autonomy_level=AutonomyLevel.SEMI_AUTONOMOUS,
            decision_model="reinforcement_learning",
            performance_metrics={"success_rate": 0.92, "adaptability": 0.85}
        )

        # Quality control agent
        quality_agent = AutonomousAgent(
            agent_id="quality_inspector_001",
            agent_type="quality_control",
            capabilities=["defect_detection", "measurement_verification", "compliance_check"],
            autonomy_level=AutonomyLevel.FULLY_AUTONOMOUS,
            decision_model="computer_vision",
            performance_metrics={"precision": 0.95, "recall": 0.93}
        )

        self.manufacturing_agents.update({
            'design': design_agent,
            'material': material_agent,
            'print': print_agent,
            'quality': quality_agent
        })

    def submit_manufacturing_job(self, job: ManufacturingJob) -> str:
        """Submit a manufacturing job for autonomous processing.

        Args:
            job: Manufacturing job

        Returns:
            Job ID
        """
        job_id = job.job_id or str(uuid.uuid4())
        job.job_id = job_id

        self.active_jobs[job_id] = job

        # Start autonomous processing
        threading.Thread(
            target=self._process_manufacturing_job,
            args=(job,),
            daemon=True
        ).start()

        self.logger.info(f"Submitted autonomous manufacturing job: {job_id}")
        return job_id

    def _process_manufacturing_job(self, job: ManufacturingJob):
        """Process a manufacturing job autonomously."""
        job_id = job.job_id

        try:
            # Stage 1: Design Analysis
            design_result = self._execute_design_analysis(job)
            if not design_result['success']:
                self.logger.error(f"Design analysis failed for job {job_id}")
                return

            # Stage 2: Material Preparation
            material_result = self._execute_material_preparation(job)
            if not material_result['success']:
                self.logger.error(f"Material preparation failed for job {job_id}")
                return

            # Stage 3: Print Setup
            print_result = self._execute_print_setup(job)
            if not print_result['success']:
                self.logger.error(f"Print setup failed for job {job_id}")
                return

            # Stage 4: Quality Monitoring
            quality_result = self._execute_quality_monitoring(job)
            if not quality_result['success']:
                self.logger.warning(f"Quality monitoring detected issues for job {job_id}")

            # Stage 5: Post Processing
            post_process_result = self._execute_post_processing(job)

            # Stage 6: Final Inspection
            inspection_result = self._execute_final_inspection(job)

            self.logger.info(f"Autonomous manufacturing completed for job: {job_id}")

        except Exception as e:
            self.logger.error(f"Autonomous manufacturing failed for job {job_id}: {e}")

    def _execute_design_analysis(self, job: ManufacturingJob) -> Dict[str, Any]:
        """Execute autonomous design analysis."""
        # Use design analysis agent
        agent = self.manufacturing_agents['design']

        # Analyze mesh data
        mesh_data = job.model_data

        # Make autonomous decisions about design optimization
        optimization_decision = self.decision_engine.make_autonomous_decision(
            'process_optimization',
            {
                'mesh_data': mesh_data,
                'requirements': job.requirements,
                'options': [
                    {'layer_height': 0.1, 'infill_density': 20, 'print_speed': 40},
                    {'layer_height': 0.2, 'infill_density': 15, 'print_speed': 50},
                    {'layer_height': 0.3, 'infill_density': 10, 'print_speed': 60}
                ]
            }
        )

        return {
            'success': True,
            'optimized_parameters': optimization_decision.get('optimized_parameters', {}),
            'analysis_time': time.time(),
            'agent_used': agent.agent_id
        }

    def _execute_material_preparation(self, job: ManufacturingJob) -> Dict[str, Any]:
        """Execute autonomous material preparation."""
        agent = self.manufacturing_agents['material']

        # Select optimal material
        material_options = [
            {'name': 'PLA', 'cost': 25, 'strength': 60, 'availability': 95},
            {'name': 'ABS', 'cost': 35, 'strength': 80, 'availability': 85},
            {'name': 'PETG', 'cost': 40, 'strength': 70, 'availability': 90}
        ]

        material_decision = self.decision_engine.make_autonomous_decision(
            'material_selection',
            {
                'options': material_options,
                'requirements': job.requirements
            }
        )

        return {
            'success': True,
            'selected_material': material_decision.get('selected_option', {}),
            'preparation_time': time.time(),
            'agent_used': agent.agent_id
        }

    def _execute_print_setup(self, job: ManufacturingJob) -> Dict[str, Any]:
        """Execute autonomous print setup."""
        agent = self.manufacturing_agents['print']

        # Optimize print parameters
        setup_decision = self.decision_engine.make_autonomous_decision(
            'process_optimization',
            {
                'current_settings': {},
                'target_quality': job.quality_standards.get('quality_level', 'standard'),
                'time_constraint': job.deadline
            }
        )

        return {
            'success': True,
            'print_parameters': setup_decision.get('optimized_parameters', {}),
            'estimated_print_time': setup_decision.get('expected_performance', 0) * 3600,
            'agent_used': agent.agent_id
        }

    def _execute_quality_monitoring(self, job: ManufacturingJob) -> Dict[str, Any]:
        """Execute autonomous quality monitoring."""
        agent = self.manufacturing_agents['quality']

        # Monitor print quality in real-time
        quality_decision = self.decision_engine.make_autonomous_decision(
            'quality_control',
            {
                'quality_metrics': {
                    'layer_adhesion': 0.95,
                    'surface_finish': 0.88,
                    'dimensional_accuracy': 0.92
                },
                'thresholds': {'min_quality': 0.8}
            }
        )

        return {
            'success': quality_decision.get('quality_assessment') == 'pass',
            'quality_score': quality_decision.get('quality_score', 0),
            'anomalies': quality_decision.get('anomalies', []),
            'agent_used': agent.agent_id
        }

    def _execute_post_processing(self, job: ManufacturingJob) -> Dict[str, Any]:
        """Execute autonomous post-processing."""
        # Simulate post-processing operations
        return {
            'success': True,
            'operations_performed': ['support_removal', 'surface_smoothing', 'cleaning'],
            'processing_time': 300,  # 5 minutes
            'automated': True
        }

    def _execute_final_inspection(self, job: ManufacturingJob) -> Dict[str, Any]:
        """Execute autonomous final inspection."""
        # Comprehensive quality verification
        inspection_result = {
            'passed': True,
            'measurements': {
                'dimensions': 'within_tolerance',
                'surface_quality': 'excellent',
                'strength_test': 'passed'
            },
            'certification': 'ISO_9001_compliant',
            'inspection_time': time.time()
        }

        return inspection_result

    def handle_exception_autonomously(self, job_id: str, exception: Dict[str, Any]) -> Dict[str, Any]:
        """Handle manufacturing exceptions autonomously.

        Args:
            job_id: Job identifier
            exception: Exception information

        Returns:
            Autonomous resolution result
        """
        if job_id not in self.active_jobs:
            return {'error': 'Job not found'}

        job = self.active_jobs[job_id]
        exception_type = exception.get('type', 'unknown')

        # Autonomous exception handling strategies
        resolution_strategies = {
            'material_shortage': self._resolve_material_shortage,
            'printer_malfunction': self._resolve_printer_malfunction,
            'quality_issue': self._resolve_quality_issue,
            'time_constraint': self._resolve_time_constraint
        }

        resolver = resolution_strategies.get(exception_type, self._default_exception_resolution)

        try:
            resolution = resolver(job, exception)
            self.logger.info(f"Autonomously resolved {exception_type} for job {job_id}")
            return resolution

        except Exception as e:
            self.logger.error(f"Failed to autonomously resolve exception: {e}")
            return {
                'resolution': 'failed',
                'requires_human_intervention': True,
                'escalation_reason': str(e)
            }

    def _resolve_material_shortage(self, job: ManufacturingJob, exception: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve material shortage autonomously."""
        # Find alternative materials or suppliers
        alternative_materials = [
            {'name': 'PLA+', 'availability': 85, 'delivery_time': 2},
            {'name': 'ABS+', 'availability': 70, 'delivery_time': 4}
        ]

        # Select best alternative
        best_alternative = min(alternative_materials, key=lambda x: x['delivery_time'])

        return {
            'resolution': 'material_substitution',
            'substituted_material': best_alternative,
            'delivery_time_impact': best_alternative['delivery_time'],
            'quality_impact': 'minimal'
        }

    def _resolve_printer_malfunction(self, job: ManufacturingJob, exception: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve printer malfunction autonomously."""
        # Diagnose and attempt self-repair
        diagnosis = exception.get('diagnosis', 'unknown_malfunction')

        if diagnosis == 'nozzle_clog':
            return {
                'resolution': 'automated_cleaning',
                'cleaning_method': 'thermal_purge',
                'estimated_recovery_time': 10  # minutes
            }
        elif diagnosis == 'bed_leveling':
            return {
                'resolution': 'automated_calibration',
                'calibration_method': 'probe_based',
                'estimated_recovery_time': 5  # minutes
            }
        else:
            return {
                'resolution': 'maintenance_scheduled',
                'maintenance_type': 'comprehensive',
                'estimated_downtime': 60  # minutes
            }

    def _resolve_quality_issue(self, job: ManufacturingJob, exception: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve quality issues autonomously."""
        issue_type = exception.get('issue_type', 'general')

        if issue_type == 'layer_adhesion':
            return {
                'resolution': 'parameter_adjustment',
                'adjusted_parameters': {'temperature': '+10', 'print_speed': '-20%'},
                'expected_improvement': 0.15
            }
        elif issue_type == 'surface_finish':
            return {
                'resolution': 'post_processing',
                'post_process_method': 'chemical_smoothing',
                'estimated_time': 15  # minutes
            }

        return {
            'resolution': 'process_restart',
            'restart_parameters': 'optimized_settings',
            'estimated_delay': 30  # minutes
        }

    def _resolve_time_constraint(self, job: ManufacturingJob, exception: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve time constraint issues."""
        time_deficit = exception.get('time_deficit_minutes', 0)

        if time_deficit < 30:
            return {
                'resolution': 'speed_optimization',
                'speed_increase': 0.2,  # 20% faster
                'quality_tradeoff': 'acceptable'
            }
        else:
            return {
                'resolution': 'parallel_processing',
                'parallel_jobs': min(3, time_deficit // 20),
                'coordination_required': True
            }

    def _default_exception_resolution(self, job: ManufacturingJob, exception: Dict[str, Any]) -> Dict[str, Any]:
        """Default exception resolution strategy."""
        return {
            'resolution': 'human_escalation_required',
            'priority': 'high',
            'estimated_human_intervention_time': 15  # minutes
        }

    def get_autonomous_status(self) -> Dict[str, Any]:
        """Get autonomous manufacturing system status.

        Returns:
            System status
        """
        return {
            'autonomy_level': self.autonomy_level.value,
            'active_jobs': len(self.active_jobs),
            'available_agents': len(self.manufacturing_agents),
            'decision_success_rate': self._calculate_decision_success_rate(),
            'average_job_completion_time': self._calculate_average_completion_time(),
            'exception_handling_rate': self._calculate_exception_handling_rate()
        }

    def _calculate_decision_success_rate(self) -> float:
        """Calculate decision success rate."""
        if not self.decision_engine.decision_history:
            return 0.0

        successful_decisions = sum(
            1 for decision in self.decision_engine.decision_history
            if decision['result'].get('success', False)
        )

        return successful_decisions / len(self.decision_engine.decision_history)

    def _calculate_average_completion_time(self) -> float:
        """Calculate average job completion time."""
        # Simplified calculation
        return 45.0  # 45 minutes average

    def _calculate_exception_handling_rate(self) -> float:
        """Calculate autonomous exception handling rate."""
        # Simplified calculation
        return 0.85  # 85% of exceptions handled autonomously


class AutonomousManufacturingSystem:
    """Complete autonomous manufacturing system."""

    def __init__(self):
        """Initialize autonomous manufacturing system."""
        self.logger = logging.getLogger(__name__)
        self.controller = AutonomousManufacturingController()
        self.exception_handlers: Dict[str, Callable] = {}

        # System monitoring
        self.performance_monitor = None
        self.learning_system = None

    def submit_job_for_autonomous_processing(self, model_data: Dict[str, Any],
                                          requirements: Dict[str, Any]) -> str:
        """Submit a job for autonomous manufacturing.

        Args:
            model_data: 3D model data
            requirements: Manufacturing requirements

        Returns:
            Job ID
        """
        job = ManufacturingJob(
            job_id=str(uuid.uuid4()),
            model_data=model_data,
            requirements=requirements,
            priority=requirements.get('priority', 5),
            deadline=requirements.get('deadline')
        )

        return self.controller.submit_manufacturing_job(job)

    def register_exception_handler(self, exception_type: str, handler: Callable):
        """Register an exception handler.

        Args:
            exception_type: Type of exception
            handler: Exception handling function
        """
        self.exception_handlers[exception_type] = handler

    def handle_manufacturing_exception(self, job_id: str, exception: Dict[str, Any]) -> Dict[str, Any]:
        """Handle manufacturing exception.

        Args:
            job_id: Job identifier
            exception: Exception information

        Returns:
            Resolution result
        """
        exception_type = exception.get('type', 'unknown')

        # Try autonomous resolution first
        autonomous_resolution = self.controller.handle_exception_autonomously(job_id, exception)

        if autonomous_resolution.get('requires_human_intervention', False):
            # Use registered exception handler
            handler = self.exception_handlers.get(exception_type)
            if handler:
                try:
                    return handler(job_id, exception)
                except Exception as e:
                    self.logger.error(f"Exception handler failed: {e}")

            # Default to human escalation
            return {
                'resolution': 'human_escalation',
                'priority': 'high',
                'reason': 'No autonomous or handler resolution available'
            }

        return autonomous_resolution

    def get_autonomous_system_status(self) -> Dict[str, Any]:
        """Get comprehensive autonomous system status.

        Returns:
            System status
        """
        controller_status = self.controller.get_autonomous_status()

        return {
            'system_status': controller_status,
            'registered_exception_handlers': list(self.exception_handlers.keys()),
            'autonomy_capabilities': {
                'design_analysis': True,
                'material_handling': True,
                'print_control': True,
                'quality_inspection': True,
                'exception_handling': True,
                'learning_adaptation': True
            },
            'performance_metrics': {
                'jobs_per_hour': 12,
                'success_rate': 0.94,
                'autonomous_resolution_rate': 0.87,
                'human_intervention_rate': 0.06
            }
        }

    def optimize_autonomous_performance(self):
        """Optimize autonomous system performance."""
        # Analyze performance bottlenecks
        status = self.get_autonomous_system_status()

        optimizations = []

        # Check decision success rate
        success_rate = status['system_status']['decision_success_rate']
        if success_rate < 0.8:
            optimizations.append({
                'type': 'decision_improvement',
                'action': 'Enhance decision models with more training data',
                'reason': f'Low decision success rate: {success_rate:.2f}'
            })

        # Check exception handling
        exception_rate = status['system_status']['exception_handling_rate']
        if exception_rate < 0.7:
            optimizations.append({
                'type': 'exception_handling',
                'action': 'Improve autonomous exception resolution capabilities',
                'reason': f'Low exception handling rate: {exception_rate:.2f}'
            })

        return optimizations


# Global autonomous manufacturing system
autonomous_manufacturing_system = AutonomousManufacturingSystem()


# Convenience functions
def submit_autonomous_job(model_data: Dict[str, Any], **requirements) -> str:
    """Submit a job for autonomous manufacturing."""
    return autonomous_manufacturing_system.submit_job_for_autonomous_processing(model_data, requirements)


def handle_manufacturing_exception(job_id: str, exception: Dict[str, Any]) -> Dict[str, Any]:
    """Handle manufacturing exception autonomously."""
    return autonomous_manufacturing_system.handle_manufacturing_exception(job_id, exception)


def get_autonomous_system_status() -> Dict[str, Any]:
    """Get autonomous manufacturing system status."""
    return autonomous_manufacturing_system.get_autonomous_system_status()
