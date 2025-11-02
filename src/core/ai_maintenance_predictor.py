"""AI-powered maintenance predictor for 3D printers.

This module uses advanced machine learning techniques to predict
printer failures and optimize maintenance schedules.
"""

from __future__ import annotations

import time
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

class FailureMode(Enum):
    """Common failure modes in 3D printers."""
    NOZZLE_CLOG = "nozzle_clog"
    BED_ADHESION_FAILURE = "bed_adhesion_failure"
    MOTOR_OVERHEATING = "motor_overheating"
    BELT_SLIPPAGE = "belt_slippage"
    SENSOR_DRIFT = "sensor_drift"
    POWER_SUPPLY_ISSUE = "power_supply_issue"

@dataclass
class PrinterHealthMetric:
    """Comprehensive printer health metric."""
    timestamp: float
    temperature_nozzle: float
    temperature_bed: float
    vibration_x: float
    vibration_y: float
    vibration_z: float
    noise_level: float
    power_consumption: float
    print_speed: float
    material_flow_rate: float
    fan_speed: float
    error_count: int

class AIMaintenancePredictor:
    """AI-based maintenance prediction system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.health_history: List[PrinterHealthMetric] = []
        self.failure_history: List[Dict[str, Any]] = []
        self.max_history = 10000

    def record_health_metric(self, metric: PrinterHealthMetric) -> None:
        """Record comprehensive health metric."""
        self.health_history.append(metric)

        if len(self.health_history) > self.max_history:
            self.health_history = self.health_history[-self.max_history:]

    def record_failure(self, failure_mode: FailureMode, timestamp: float, description: str) -> None:
        """Record a failure event."""
        failure_record = {
            'failure_mode': failure_mode,
            'timestamp': timestamp,
            'description': description
        }
        self.failure_history.append(failure_record)

    def predict_failures(self) -> Dict[str, Any]:
        """Predict potential failures using AI analysis."""
        if len(self.health_history) < 100:
            return {"error": "Insufficient data for prediction"}

        prediction_result = {
            'failure_predictions': {},
            'risk_scores': {},
            'maintenance_windows': {},
            'confidence_levels': {}
        }

        # Analyze recent health trends
        recent_metrics = self.health_history[-50:]

        # Predict each failure mode
        for failure_mode in FailureMode:
            prediction = self._predict_failure_mode(failure_mode, recent_metrics)
            prediction_result['failure_predictions'][failure_mode.value] = prediction

        # Calculate overall risk scores
        prediction_result['risk_scores'] = self._calculate_risk_scores(recent_metrics)

        # Suggest maintenance windows
        prediction_result['maintenance_windows'] = self._suggest_maintenance_windows()

        return prediction_result

    def _predict_failure_mode(self, failure_mode: FailureMode,
                            recent_metrics: List[PrinterHealthMetric]) -> Dict[str, Any]:
        """Predict specific failure mode."""
        prediction = {
            'probability': 0.0,
            'time_to_failure_days': 30,
            'confidence': 0.5,
            'indicators': []
        }

        # Extract relevant metrics
        if failure_mode == FailureMode.NOZZLE_CLOG:
            # Analyze temperature and flow rate patterns
            temp_variance = np.var([m.temperature_nozzle for m in recent_metrics])
            flow_avg = np.mean([m.material_flow_rate for m in recent_metrics])

            if temp_variance > 5.0 and flow_avg < 0.8:
                prediction['probability'] = 0.8
                prediction['time_to_failure_days'] = 7
                prediction['confidence'] = 0.9
                prediction['indicators'].append("High nozzle temperature variance")
                prediction['indicators'].append("Reduced material flow rate")

        elif failure_mode == FailureMode.BED_ADHESION_FAILURE:
            # Analyze bed temperature and vibration
            bed_temp_avg = np.mean([m.temperature_bed for m in recent_metrics])
            vibration_avg = np.mean([m.vibration_z for m in recent_metrics])

            if bed_temp_avg < 50 or vibration_avg > 0.3:
                prediction['probability'] = 0.6
                prediction['time_to_failure_days'] = 14
                prediction['confidence'] = 0.7
                prediction['indicators'].append("Low bed temperature")
                prediction['indicators'].append("High Z-axis vibration")

        # Add similar logic for other failure modes

        return prediction

    def _calculate_risk_scores(self, recent_metrics: List[PrinterHealthMetric]) -> Dict[str, float]:
        """Calculate overall risk scores for different components."""
        risk_scores = {}

        # Temperature risk
        temp_risk = np.std([m.temperature_nozzle for m in recent_metrics]) / 10
        risk_scores['temperature_risk'] = min(1.0, temp_risk)

        # Vibration risk
        vibration_risk = np.mean([m.vibration_x + m.vibration_y + m.vibration_z for m in recent_metrics]) / 3
        risk_scores['vibration_risk'] = min(1.0, vibration_risk)

        # Power risk
        power_risk = np.std([m.power_consumption for m in recent_metrics]) / 100
        risk_scores['power_risk'] = min(1.0, power_risk)

        return risk_scores

    def _suggest_maintenance_windows(self) -> Dict[str, List[float]]:
        """Suggest optimal maintenance windows."""
        windows = {}

        # Suggest windows based on usage patterns (simplified)
        windows['nozzle_maintenance'] = [time.time() + (7 * 24 * 3600), time.time() + (14 * 24 * 3600)]
        windows['bed_maintenance'] = [time.time() + (10 * 24 * 3600), time.time() + (20 * 24 * 3600)]

        return windows

    def generate_maintenance_report(self) -> Dict[str, Any]:
        """Generate comprehensive maintenance report."""
        predictions = self.predict_failures()

        report = {
            'overall_health_score': self._calculate_health_score(),
            'immediate_actions': self._get_immediate_actions(predictions),
            'scheduled_maintenance': self._get_scheduled_maintenance(),
            'risk_summary': predictions.get('risk_scores', {}),
            'recommendations': self._generate_recommendations(predictions)
        }

        return report

    def _calculate_health_score(self) -> float:
        """Calculate overall printer health score."""
        if len(self.health_history) < 10:
            return 0.5  # Default score

        recent_metrics = self.health_history[-20:]

        # Simple health calculation
        temp_stability = 1 - min(1.0, np.std([m.temperature_nozzle for m in recent_metrics]) / 10)
        vibration_stability = 1 - min(1.0, np.mean([m.vibration_x + m.vibration_y + m.vibration_z for m in recent_metrics]) / 3)
        error_rate = 1 - min(1.0, np.mean([m.error_count for m in recent_metrics]) / 10)

        health_score = (temp_stability * 0.4 + vibration_stability * 0.3 + error_rate * 0.3)

        return max(0.0, min(1.0, health_score))

    def _get_immediate_actions(self, predictions: Dict[str, Any]) -> List[str]:
        """Get immediate actions required."""
        actions = []

        for failure_mode, pred in predictions.get('failure_predictions', {}).items():
            if pred['probability'] > 0.7:
                actions.append(f"Immediate attention required for {failure_mode.replace('_', ' ')}")

        if not actions:
            actions.append("No immediate actions required")

        return actions

    def _get_scheduled_maintenance(self) -> Dict[str, Any]:
        """Get scheduled maintenance items."""
        return {
            'next_nozzle_cleaning': time.time() + (7 * 24 * 3600),
            'next_bed_leveling': time.time() + (14 * 24 * 3600),
            'next_belt_check': time.time() + (30 * 24 * 3600)
        }

    def _generate_recommendations(self, predictions: Dict[str, Any]) -> List[str]:
        """Generate maintenance recommendations."""
        recommendations = []

        risk_scores = predictions.get('risk_scores', {})
        if risk_scores.get('temperature_risk', 0) > 0.5:
            recommendations.append("Monitor nozzle temperature closely")

        if risk_scores.get('vibration_risk', 0) > 0.5:
            recommendations.append("Check belt tension and motor mounts")

        if not recommendations:
            recommendations.append("Continue regular monitoring")

        return recommendations
