"""Predictive maintenance system for 3D printers.

This module implements machine learning-based predictive maintenance
to forecast printer failures and optimize maintenance schedules.
"""

from __future__ import annotations

import time
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

class MaintenanceType(Enum):
    """Types of maintenance activities."""
    NOZZLE_CLEANING = "nozzle_cleaning"
    BED_LEVELING = "bed_leveling"
    BELT_TENSIONING = "belt_tensioning"
    LUBRICATION = "lubrication"
    COMPONENT_REPLACEMENT = "component_replacement"
    GENERAL_INSPECTION = "general_inspection"

@dataclass
class PrinterMetric:
    """Printer performance metric."""
    timestamp: float
    temperature: float
    vibration: float
    noise_level: float
    print_speed: float
    material_flow_rate: float
    power_consumption: float

@dataclass
class MaintenanceRecord:
    """Record of maintenance activity."""
    maintenance_type: MaintenanceType
    timestamp: float
    duration_minutes: float
    cost: float
    technician: str
    notes: str = ""

class PredictiveMaintenanceSystem:
    """AI-powered predictive maintenance for 3D printers."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics_history: List[PrinterMetric] = []
        self.maintenance_history: List[MaintenanceRecord] = []
        self.failure_patterns: Dict[str, List[float]] = {}
        self.max_history = 10000

    def record_printer_metric(self, metric: PrinterMetric) -> None:
        """Record a printer performance metric."""
        self.metrics_history.append(metric)

        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]

    def record_maintenance(self, record: MaintenanceRecord) -> None:
        """Record a maintenance activity."""
        self.maintenance_history.append(record)

    def predict_maintenance_needs(self) -> Dict[str, Any]:
        """Predict upcoming maintenance needs."""
        prediction_result = {
            'maintenance_predictions': {},
            'risk_assessment': {},
            'recommended_actions': []
        }

        # Analyze metrics for anomalies
        anomalies = self._detect_anomalies()

        # Predict maintenance for each type
        for maintenance_type in MaintenanceType:
            prediction = self._predict_maintenance_type(maintenance_type, anomalies)
            prediction_result['maintenance_predictions'][maintenance_type.value] = prediction

        # Assess overall risk
        prediction_result['risk_assessment'] = self._assess_overall_risk()

        # Generate recommendations
        prediction_result['recommended_actions'] = self._generate_maintenance_recommendations(
            prediction_result
        )

        return prediction_result

    def _detect_anomalies(self) -> Dict[str, List[str]]:
        """Detect anomalies in printer metrics."""
        anomalies = {}

        if len(self.metrics_history) < 50:
            return anomalies

        # Convert metrics to numpy array for analysis
        metrics_array = np.array([
            [m.temperature, m.vibration, m.noise_level, m.print_speed,
             m.material_flow_rate, m.power_consumption]
            for m in self.metrics_history[-100:]  # Last 100 readings
        ])

        # Calculate moving averages and standard deviations
        window_size = 20
        for i in range(len(metrics_array[0])):
            values = metrics_array[:, i]

            # Simple anomaly detection: values outside 2 standard deviations
            mean_val = np.mean(values[-window_size:])
            std_val = np.std(values[-window_size:])

            anomaly_indices = np.where(np.abs(values - mean_val) > 2 * std_val)[0]
            if len(anomaly_indices) > 0:
                anomalies[f"metric_{i}"] = anomaly_indices.tolist()

        return anomalies

    def _predict_maintenance_type(self, maintenance_type: MaintenanceType,
                                anomalies: Dict[str, List[str]]) -> Dict[str, Any]:
        """Predict maintenance needs for a specific type."""
        # Simplified prediction based on usage patterns
        prediction = {
            'urgency': 'low',
            'predicted_date': time.time() + (30 * 24 * 3600),  # 30 days from now
            'confidence': 0.8,
            'reasoning': []
        }

        # Check for specific failure patterns
        if maintenance_type == MaintenanceType.NOZZLE_CLEANING:
            # High temperature variance indicates nozzle issues
            temp_anomalies = anomalies.get('metric_0', [])
            if len(temp_anomalies) > 5:
                prediction['urgency'] = 'high'
                prediction['predicted_date'] = time.time() + (7 * 24 * 3600)  # 7 days
                prediction['reasoning'].append("High temperature variance detected")

        elif maintenance_type == MaintenanceType.BED_LEVELING:
            # High vibration indicates bed issues
            vibration_anomalies = anomalies.get('metric_1', [])
            if len(vibration_anomalies) > 3:
                prediction['urgency'] = 'medium'
                prediction['predicted_date'] = time.time() + (14 * 24 * 3600)  # 14 days
                prediction['reasoning'].append("Elevated vibration levels detected")

        return prediction

    def _assess_overall_risk(self) -> Dict[str, Any]:
        """Assess overall printer failure risk."""
        if len(self.metrics_history) < 100:
            return {'risk_level': 'unknown', 'confidence': 0.0}

        # Calculate risk score based on recent metrics
        recent_metrics = self.metrics_history[-50:]

        # Risk factors
        temp_variance = np.var([m.temperature for m in recent_metrics])
        vibration_avg = np.mean([m.vibration for m in recent_metrics])
        noise_avg = np.mean([m.noise_level for m in recent_metrics])

        # Simple risk calculation
        risk_score = (temp_variance * 0.3 + vibration_avg * 0.4 + noise_avg * 0.3) / 100

        risk_level = 'low'
        if risk_score > 0.7:
            risk_level = 'high'
        elif risk_score > 0.4:
            risk_level = 'medium'

        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'confidence': min(1.0, len(recent_metrics) / 100.0)
        }

    def _generate_maintenance_recommendations(self, prediction_result: Dict[str, Any]) -> List[str]:
        """Generate maintenance recommendations."""
        recommendations = []

        # Check risk assessment
        risk_level = prediction_result['risk_assessment']['risk_level']
        if risk_level == 'high':
            recommendations.append("Schedule immediate inspection due to high failure risk")
        elif risk_level == 'medium':
            recommendations.append("Consider scheduling maintenance within 2 weeks")

        # Check specific predictions
        for maintenance_type, prediction in prediction_result['maintenance_predictions'].items():
            if prediction['urgency'] == 'high':
                recommendations.append(f"High urgency for {maintenance_type.replace('_', ' ')}")

        if not recommendations:
            recommendations.append("No immediate maintenance required")

        return recommendations

    def optimize_maintenance_schedule(self, available_slots: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Optimize maintenance schedule based on predictions."""
        predictions = self.predict_maintenance_needs()

        # Sort maintenance by urgency
        maintenance_tasks = []
        for mt, pred in predictions['maintenance_predictions'].items():
            maintenance_tasks.append({
                'type': mt,
                'urgency': pred['urgency'],
                'predicted_date': pred['predicted_date'],
                'priority_score': self._calculate_priority_score(pred)
            })

        # Sort by priority
        maintenance_tasks.sort(key=lambda x: x['priority_score'], reverse=True)

        # Assign to available slots
        schedule = {}
        for task in maintenance_tasks:
            for slot_start, slot_end in available_slots:
                if slot_start <= task['predicted_date'] <= slot_end:
                    schedule[task['type']] = {
                        'scheduled_time': task['predicted_date'],
                        'estimated_duration': 60,  # minutes
                        'priority': task['priority_score']
                    }
                    break

        return {
            'optimized_schedule': schedule,
            'unassigned_tasks': [t for t in maintenance_tasks if t['type'] not in schedule],
            'total_maintenance_time': sum(t['estimated_duration'] for t in schedule.values())
        }

    def _calculate_priority_score(self, prediction: Dict[str, Any]) -> float:
        """Calculate priority score for maintenance task."""
        urgency_scores = {'low': 1, 'medium': 2, 'high': 3}
        urgency_score = urgency_scores.get(prediction['urgency'], 1)

        # Time factor: closer due date = higher priority
        days_until_due = (prediction['predicted_date'] - time.time()) / (24 * 3600)
        time_factor = max(0.1, min(2.0, 30 / max(days_until_due, 1)))

        return urgency_score * time_factor * prediction['confidence']
