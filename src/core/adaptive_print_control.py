"""Adaptive print control system based on environmental conditions.

This module provides intelligent print parameter adjustment based on
real-time environmental monitoring to optimize print quality and reliability.
"""

from __future__ import annotations

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

class AdaptationStrategy(Enum):
    """Strategies for adapting to environmental conditions."""
    SPEED_ADJUSTMENT = "speed_adjustment"
    TEMPERATURE_CONTROL = "temperature_control"
    FAN_CONTROL = "fan_control"
    RETRACTION_ADJUSTMENT = "retraction_adjustment"
    LAYER_HEIGHT_MODIFICATION = "layer_height_modification"

@dataclass
class AdaptiveRule:
    """Rule for adapting print settings."""
    condition: str
    threshold: float
    strategy: AdaptationStrategy
    adjustment_factor: float
    description: str

class AdaptivePrintController:
    """Controller for adaptive print parameter adjustment."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.adaptation_rules: List[AdaptiveRule] = []
        self.print_history: List[Dict[str, Any]] = []
        self.max_history = 1000

    def add_adaptation_rule(self, rule: AdaptiveRule) -> None:
        """Add an adaptation rule."""
        self.adaptation_rules.append(rule)
        self.logger.info(f"Added adaptation rule: {rule.description}")

    def get_adaptive_settings(self, base_settings: Dict[str, Any],
                            environmental_data: Dict[str, float]) -> Dict[str, Any]:
        """Get print settings adapted to current environment."""
        adapted_settings = base_settings.copy()

        # Apply each adaptation rule
        for rule in self.adaptation_rules:
            adapted_settings = self._apply_rule(rule, environmental_data, adapted_settings)

        # Record adaptation for analysis
        self._record_adaptation(base_settings, adapted_settings, environmental_data)

        return adapted_settings

    def _apply_rule(self, rule: AdaptiveRule, env_data: Dict[str, float],
                  settings: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a single adaptation rule."""
        current_value = env_data.get(rule.condition, 0.0)

        if self._check_condition(current_value, rule.condition, rule.threshold):
            settings = self._apply_strategy(rule.strategy, settings, rule.adjustment_factor)

        return settings

    def _check_condition(self, current_value: float, condition: str, threshold: float) -> bool:
        """Check if condition is met."""
        if "greater_than" in condition:
            return current_value > threshold
        elif "less_than" in condition:
            return current_value < threshold
        elif "equals" in condition:
            return abs(current_value - threshold) < 0.1
        else:
            return False

    def _apply_strategy(self, strategy: AdaptationStrategy, settings: Dict[str, Any],
                       factor: float) -> Dict[str, Any]:
        """Apply adaptation strategy."""
        if strategy == AdaptationStrategy.SPEED_ADJUSTMENT:
            settings['print_speed'] = settings.get('print_speed', 50) * factor
        elif strategy == AdaptationStrategy.TEMPERATURE_CONTROL:
            settings['nozzle_temperature'] = settings.get('nozzle_temperature', 200) * factor
        elif strategy == AdaptationStrategy.FAN_CONTROL:
            settings['fan_speed'] = min(255, settings.get('fan_speed', 128) * factor)
        elif strategy == AdaptationStrategy.RETRACTION_ADJUSTMENT:
            settings['retraction_distance'] = settings.get('retraction_distance', 2.0) * factor
        elif strategy == AdaptationStrategy.LAYER_HEIGHT_MODIFICATION:
            settings['layer_height'] = settings.get('layer_height', 0.2) * factor

        return settings

    def setup_default_rules(self) -> None:
        """Setup default adaptation rules for common conditions."""
        rules = [
            AdaptiveRule(
                condition="temperature_greater_than",
                threshold=30.0,
                strategy=AdaptationStrategy.SPEED_ADJUSTMENT,
                adjustment_factor=0.8,
                description="Reduce print speed in high temperature"
            ),
            AdaptiveRule(
                condition="humidity_greater_than",
                threshold=70.0,
                strategy=AdaptationStrategy.RETRACTION_ADJUSTMENT,
                adjustment_factor=1.2,
                description="Increase retraction in high humidity"
            ),
            AdaptiveRule(
                condition="vibration_greater_than",
                threshold=0.5,
                strategy=AdaptationStrategy.LAYER_HEIGHT_MODIFICATION,
                adjustment_factor=0.9,
                description="Reduce layer height with high vibration"
            )
        ]

        for rule in rules:
            self.add_adaptation_rule(rule)

    def _record_adaptation(self, original_settings: Dict[str, Any],
                         adapted_settings: Dict[str, Any],
                         env_data: Dict[str, float]) -> None:
        """Record adaptation for analysis."""
        record = {
            'timestamp': time.time(),
            'original_settings': original_settings,
            'adapted_settings': adapted_settings,
            'environmental_data': env_data
        }

        self.print_history.append(record)
        if len(self.print_history) > self.max_history:
            self.print_history = self.print_history[-self.max_history:]

    def analyze_adaptation_effectiveness(self) -> Dict[str, Any]:
        """Analyze the effectiveness of adaptations."""
        if len(self.print_history) < 10:
            return {"error": "Insufficient data for analysis"}

        analysis = {
            'total_adaptations': len(self.print_history),
            'adaptation_frequency': {},
            'effectiveness_metrics': {}
        }

        # Count adaptation types
        for record in self.print_history:
            for key in record['adapted_settings']:
                if record['adapted_settings'][key] != record['original_settings'].get(key):
                    adaptation_type = key
                    if adaptation_type not in analysis['adaptation_frequency']:
                        analysis['adaptation_frequency'][adaptation_type] = 0
                    analysis['adaptation_frequency'][adaptation_type] += 1

        return analysis
