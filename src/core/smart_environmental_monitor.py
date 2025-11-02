"""Smart environmental monitoring for adaptive 3D printing control.

This module provides intelligent environmental monitoring and adaptive control systems
for optimizing print quality based on temperature, humidity, and other factors.
"""

from __future__ import annotations

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

class SensorType(Enum):
    """Types of environmental sensors."""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    AIR_QUALITY = "air_quality"
    VIBRATION = "vibration"
    NOISE = "noise"
    LIGHT = "light"
    PRESSURE = "pressure"

@dataclass
class SensorReading:
    """Single sensor reading."""
    sensor_id: str
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: float
    location: str = "unknown"

@dataclass
class EnvironmentalCondition:
    """Current environmental conditions."""
    temperature_celsius: float
    humidity_percent: float
    air_quality_index: float
    vibration_level: float
    noise_level_db: float
    light_intensity_lux: float
    atmospheric_pressure_hpa: float

class SmartEnvironmentalMonitor:
    """Smart environmental monitoring and data collection."""

    def __init__(self):
        self.sensors: Dict[str, Dict[str, Any]] = {}
        self.readings: List[SensorReading] = []
        self.max_readings = 10000
        self.reading_interval = 5.0  # seconds
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)

    def register_sensor(self, sensor_id: str, sensor_type: SensorType,
                       location: str = "printer") -> None:
        """Register an environmental sensor."""
        self.sensors[sensor_id] = {
            'type': sensor_type,
            'location': location,
            'last_reading': None,
            'status': 'active'
        }
        self.logger.info(f"Registered sensor {sensor_id} of type {sensor_type.value}")

    def record_reading(self, reading: SensorReading) -> None:
        """Record a sensor reading."""
        with self.lock:
            self.readings.append(reading)
            if len(self.readings) > self.max_readings:
                self.readings = self.readings[-self.max_readings:]

            # Update sensor status
            if reading.sensor_id in self.sensors:
                self.sensors[reading.sensor_id]['last_reading'] = reading.timestamp

    def get_current_conditions(self) -> EnvironmentalCondition:
        """Get current environmental conditions."""
        with self.lock:
            # Get latest readings for each sensor type
            latest_readings = {}

            for reading in reversed(self.readings):
                if reading.sensor_type not in latest_readings:
                    latest_readings[reading.sensor_type] = reading.value

                if len(latest_readings) == len(SensorType):
                    break

            return EnvironmentalCondition(
                temperature_celsius=latest_readings.get(SensorType.TEMPERATURE, 25.0),
                humidity_percent=latest_readings.get(SensorType.HUMIDITY, 50.0),
                air_quality_index=latest_readings.get(SensorType.AIR_QUALITY, 100.0),
                vibration_level=latest_readings.get(SensorType.VIBRATION, 0.0),
                noise_level_db=latest_readings.get(SensorType.NOISE, 40.0),
                light_intensity_lux=latest_readings.get(SensorType.LIGHT, 500.0),
                atmospheric_pressure_hpa=latest_readings.get(SensorType.PRESSURE, 1013.25)
            )

    def start_monitoring(self) -> None:
        """Start continuous environmental monitoring."""
        def monitoring_loop():
            while True:
                try:
                    # Simulate sensor readings
                    self._simulate_sensor_readings()
                    time.sleep(self.reading_interval)
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(1.0)

        monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitoring_thread.start()
        self.logger.info("Started environmental monitoring")

    def _simulate_sensor_readings(self) -> None:
        """Simulate sensor readings for demonstration."""
        current_time = time.time()

        # Simulate temperature (25°C ± 5°C)
        temp_reading = SensorReading(
            sensor_id="temp_sensor_1",
            sensor_type=SensorType.TEMPERATURE,
            value=25.0 + np.random.normal(0, 2.0),
            unit="°C",
            timestamp=current_time
        )
        self.record_reading(temp_reading)

        # Simulate humidity (50% ± 10%)
        humidity_reading = SensorReading(
            sensor_id="humidity_sensor_1",
            sensor_type=SensorType.HUMIDITY,
            value=max(0, min(100, 50.0 + np.random.normal(0, 5.0))),
            unit="%",
            timestamp=current_time
        )
        self.record_reading(humidity_reading)

        # Simulate other sensors
        for sensor_type in [SensorType.AIR_QUALITY, SensorType.VIBRATION, SensorType.NOISE]:
            value = self._get_simulated_value(sensor_type)
            reading = SensorReading(
                sensor_id=f"{sensor_type.value}_sensor_1",
                sensor_type=sensor_type,
                value=value,
                unit=self._get_unit_for_sensor(sensor_type),
                timestamp=current_time
            )
            self.record_reading(reading)

    def _get_simulated_value(self, sensor_type: SensorType) -> float:
        """Get simulated sensor value."""
        if sensor_type == SensorType.AIR_QUALITY:
            return max(0, 100 + np.random.normal(0, 10.0))
        elif sensor_type == SensorType.VIBRATION:
            return max(0, np.random.exponential(0.5))
        elif sensor_type == SensorType.NOISE:
            return max(30, 50 + np.random.normal(0, 10.0))
        elif sensor_type == SensorType.LIGHT:
            return max(0, 500 + np.random.normal(0, 100.0))
        elif sensor_type == SensorType.PRESSURE:
            return 1013.25 + np.random.normal(0, 5.0)
        else:
            return 0.0

    def _get_unit_for_sensor(self, sensor_type: SensorType) -> str:
        """Get unit for sensor type."""
        units = {
            SensorType.TEMPERATURE: "°C",
            SensorType.HUMIDITY: "%",
            SensorType.AIR_QUALITY: "AQI",
            SensorType.VIBRATION: "m/s²",
            SensorType.NOISE: "dB",
            SensorType.LIGHT: "lux",
            SensorType.PRESSURE: "hPa"
        }
        return units.get(sensor_type, "units")

class AdaptivePrintController:
    """Adaptive print controller based on environmental conditions."""

    def __init__(self, sensor_manager: SmartEnvironmentalMonitor):
        self.sensor_manager = sensor_manager
        self.logger = logging.getLogger(__name__)
        self.adaptation_rules: Dict[str, Callable] = {}

    def register_adaptation_rule(self, condition: str, rule: Callable) -> None:
        """Register adaptation rule for environmental conditions."""
        self.adaptation_rules[condition] = rule
        self.logger.info(f"Registered adaptation rule for: {condition}")

    def get_adaptive_print_settings(self, base_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Get adaptive print settings based on current conditions."""
        conditions = self.sensor_manager.get_current_conditions()
        adapted_settings = base_settings.copy()

        # Apply adaptation rules
        for condition_name, rule in self.adaptation_rules.items():
            adapted_settings = rule(conditions, adapted_settings)

        return adapted_settings

    def _high_temperature_adaptation(self, conditions: EnvironmentalCondition,
                                   settings: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt settings for high temperature."""
        if conditions.temperature_celsius > 30:
            settings['print_speed'] = settings.get('print_speed', 50) * 0.8  # Reduce speed
            settings['fan_speed'] = min(255, settings.get('fan_speed', 128) + 50)  # Increase cooling

        return settings

    def _high_humidity_adaptation(self, conditions: EnvironmentalCondition,
                                settings: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt settings for high humidity."""
        if conditions.humidity_percent > 70:
            settings['retraction_distance'] = settings.get('retraction_distance', 2.0) * 1.2  # Increase retraction
            settings['retraction_speed'] = settings.get('retraction_speed', 40) * 0.9  # Reduce speed

        return settings

    def setup_default_adaptation_rules(self) -> None:
        """Setup default adaptation rules."""
        self.register_adaptation_rule("high_temperature", self._high_temperature_adaptation)
        self.register_adaptation_rule("high_humidity", self._high_humidity_adaptation)
