"""G-code generation for 3D printing."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, TextIO
from enum import Enum
from pathlib import Path
import numpy as np
import logging
import time


class GcodeFlavor(Enum):
    """G-code flavors for different firmwares."""
    MARLIN = "marlin"
    REPRAP = "reprap"
    REPETIER = "repetier"
    SMOOTHIEWARE = "smoothieware"
    KLIPPER = "klipper"
    MACH3 = "mach3"
    SAILFISH = "sailfish"
    PRUSA = "prusa"
    BAMBU = "bambu"


class CoolingStrategy(Enum):
    """Cooling strategies."""
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"
    MINIMAL = "minimal"
    BRIDGES_ONLY = "bridges_only"
    AUTO = "auto"


@dataclass
class GcodeSettings:
    """Comprehensive G-code generation settings."""
    # Flavor and compatibility
    gcode_flavor: GcodeFlavor = GcodeFlavor.MARLIN
    gcode_comments: bool = True
    verbose_gcode: bool = False

    # Machine settings
    machine_name: str = "3D Printer"
    bed_size_x: float = 220
    bed_size_y: float = 220
    bed_size_z: float = 250
    origin_at_center: bool = False
    use_relative_e: bool = True
    use_firmware_retraction: bool = False

    # Filament settings
    filament_diameter: float = 1.75
    filament_density: float = 1.24  # g/cm³ for PLA
    filament_cost: float = 20.0  # $/kg

    # Temperature settings
    nozzle_temperature: float = 210
    bed_temperature: float = 60
    chamber_temperature: Optional[float] = None
    standby_temperature: float = 175
    wait_for_temperature: bool = True

    # Speed settings (mm/s)
    print_speed: float = 60
    travel_speed: float = 180
    first_layer_speed: float = 20
    infill_speed: float = 80
    perimeter_speed: float = 50
    external_perimeter_speed: float = 30
    bridge_speed: float = 30
    gap_fill_speed: float = 20
    support_speed: float = 50

    # Acceleration settings (mm/s²)
    acceleration_enabled: bool = True
    print_acceleration: float = 1000
    travel_acceleration: float = 2000
    retract_acceleration: float = 1500
    first_layer_acceleration: float = 500

    # Jerk settings (mm/s)
    jerk_enabled: bool = True
    jerk_xy: float = 10
    jerk_z: float = 0.4
    jerk_e: float = 5

    # Retraction settings
    retraction_distance: float = 0.8
    retraction_speed: float = 35
    retraction_extra_prime: float = 0
    retraction_min_travel: float = 2
    retraction_lift_z: float = 0.2
    retraction_lift_above: float = 0
    retraction_lift_below: float = 250
    firmware_retraction_enabled: bool = False

    # Cooling settings
    cooling_enabled: bool = True
    min_fan_speed: int = 30
    max_fan_speed: int = 100
    bridge_fan_speed: int = 100
    disable_fan_first_layers: int = 3
    full_fan_speed_layer: int = 5
    cooling_strategy: CoolingStrategy = CoolingStrategy.NORMAL

    # Advanced features
    pressure_advance: float = 0.0
    arc_fitting: bool = False
    arc_fitting_tolerance: float = 0.025
    spiral_vase_mode: bool = False
    variable_layer_height: bool = False
    wipe_nozzle: bool = True
    wipe_distance: float = 2
    prime_nozzle: bool = True
    prime_volume: float = 10

    # Start/End G-code
    start_gcode: str = ""
    end_gcode: str = ""
    layer_change_gcode: str = ""
    before_retraction_gcode: str = ""
    after_retraction_gcode: str = ""
    tool_change_gcode: str = ""

    # Output settings
    output_file_extension: str = ".gcode"
    include_thumbnails: bool = True
    thumbnail_size: Tuple[int, int] = (300, 300)
    include_metadata: bool = True


@dataclass
class GcodeCommand:
    """Single G-code command."""
    command: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    comment: Optional[str] = None
    is_movement: bool = False
    extrusion_amount: float = 0
    speed: Optional[float] = None
    time_estimate: float = 0


@dataclass
class GcodeLayer:
    """G-code for a single layer."""
    layer_number: int
    z_height: float
    commands: List[GcodeCommand] = field(default_factory=list)
    print_time: float = 0
    extrusion_length: float = 0
    travel_distance: float = 0


@dataclass
class GcodeResult:
    """Result of G-code generation."""
    success: bool
    layers: List[GcodeLayer]
    total_commands: int
    total_print_time: float
    total_filament_length: float
    total_filament_weight: float
    total_filament_cost: float
    total_travel_distance: float
    bounding_box: Tuple[float, float, float]
    warnings: List[str]
    statistics: Dict[str, Any]
    gcode_content: Optional[str] = None


class GcodeGenerator:
    """Advanced G-code generator for 3D printing."""

    def __init__(self, settings: GcodeSettings = None):
        """Initialize G-code generator."""
        self.settings = settings or GcodeSettings()
        self.logger = logging.getLogger(__name__)

        # State tracking
        self.current_position = np.array([0.0, 0.0, 0.0])
        self.current_e = 0.0
        self.current_f = 0.0
        self.is_retracted = False
        self.current_fan_speed = 0
        self.current_temperature = 0
        self.current_bed_temp = 0
        self.layers: List[GcodeLayer] = []

    def generate_gcode(self, sliced_layers: List[Any],
                      output_path: Optional[Path] = None) -> GcodeResult:
        """
        Generate G-code from sliced layers.

        Args:
            sliced_layers: List of LayerData from slicing engine
            output_path: Optional path to save G-code file

        Returns:
            GcodeResult with generated G-code
        """
        start_time = time.time()
        self.layers = []
        warnings = []

        try:
            # Generate start G-code
            start_commands = self._generate_start_gcode()

            # Process each layer
            for layer_idx, layer_data in enumerate(sliced_layers):
                gcode_layer = self._process_layer(layer_data, layer_idx)
                self.layers.append(gcode_layer)

                # Update cooling strategy
                self._update_cooling(gcode_layer)

            # Generate end G-code
            end_commands = self._generate_end_gcode()

            # Calculate statistics
            statistics = self._calculate_statistics()

            # Calculate totals
            total_commands = sum(len(layer.commands) for layer in self.layers)
            total_commands += len(start_commands) + len(end_commands)

            total_time = sum(layer.print_time for layer in self.layers)
            total_filament = sum(layer.extrusion_length for layer in self.layers)
            total_weight = self._calculate_filament_weight(total_filament)
            total_cost = total_weight * self.settings.filament_cost / 1000
            total_travel = sum(layer.travel_distance for layer in self.layers)

            # Generate G-code content
            gcode_content = None
            if output_path or len(self.layers) > 0:
                gcode_content = self._generate_gcode_content(
                    start_commands, self.layers, end_commands
                )

                if output_path:
                    with open(output_path, 'w') as f:
                        f.write(gcode_content)

            generation_time = time.time() - start_time

            return GcodeResult(
                success=True,
                layers=self.layers,
                total_commands=total_commands,
                total_print_time=total_time,
                total_filament_length=total_filament,
                total_filament_weight=total_weight,
                total_filament_cost=total_cost,
                total_travel_distance=total_travel,
                bounding_box=self._calculate_bounding_box(),
                warnings=warnings,
                statistics=statistics,
                gcode_content=gcode_content
            )

        except Exception as e:
            self.logger.error(f"G-code generation failed: {e}")
            return GcodeResult(
                success=False,
                layers=[],
                total_commands=0,
                total_print_time=0,
                total_filament_length=0,
                total_filament_weight=0,
                total_filament_cost=0,
                total_travel_distance=0,
                bounding_box=(0, 0, 0),
                warnings=[f"G-code generation failed: {str(e)}"],
                statistics={}
            )

    def _generate_start_gcode(self) -> List[GcodeCommand]:
        """Generate start G-code commands."""
        commands = []

        # Header comments
        if self.settings.gcode_comments:
            commands.append(GcodeCommand(
                command=";",
                comment=f"Generated by 3D Print CAD Assistant"
            ))
            commands.append(GcodeCommand(
                command=";",
                comment=f"Machine: {self.settings.machine_name}"
            ))
            commands.append(GcodeCommand(
                command=";",
                comment=f"Filament: {self.settings.filament_diameter}mm"
            ))

        # Custom start G-code
        if self.settings.start_gcode:
            for line in self.settings.start_gcode.split('\n'):
                if line.strip():
                    commands.append(GcodeCommand(command=line))
        else:
            # Default start sequence
            commands.extend(self._generate_default_start_sequence())

        return commands

    def _generate_default_start_sequence(self) -> List[GcodeCommand]:
        """Generate default start sequence."""
        commands = []

        # Initialize printer
        commands.append(GcodeCommand(
            command="G21",
            comment="Set units to millimeters"
        ))
        commands.append(GcodeCommand(
            command="G90",
            comment="Absolute positioning"
        ))
        commands.append(GcodeCommand(
            command="M82",
            comment="Absolute extrusion"
        ))

        # Home axes
        commands.append(GcodeCommand(
            command="G28",
            comment="Home all axes"
        ))

        # Level bed if supported
        if self.settings.gcode_flavor in [GcodeFlavor.MARLIN, GcodeFlavor.PRUSA]:
            commands.append(GcodeCommand(
                command="G29",
                comment="Auto bed leveling"
            ))

        # Set temperatures
        commands.append(GcodeCommand(
            command="M140",
            parameters={"S": self.settings.bed_temperature},
            comment="Set bed temperature"
        ))
        commands.append(GcodeCommand(
            command="M104",
            parameters={"S": self.settings.nozzle_temperature},
            comment="Set nozzle temperature"
        ))

        if self.settings.wait_for_temperature:
            commands.append(GcodeCommand(
                command="M190",
                parameters={"S": self.settings.bed_temperature},
                comment="Wait for bed temperature"
            ))
            commands.append(GcodeCommand(
                command="M109",
                parameters={"S": self.settings.nozzle_temperature},
                comment="Wait for nozzle temperature"
            ))

        # Prime nozzle
        if self.settings.prime_nozzle:
            commands.extend(self._generate_prime_sequence())

        # Reset extrusion
        commands.append(GcodeCommand(
            command="G92",
            parameters={"E": 0},
            comment="Reset extruder"
        ))

        return commands

    def _generate_prime_sequence(self) -> List[GcodeCommand]:
        """Generate nozzle priming sequence."""
        commands = []

        # Move to prime position
        commands.append(GcodeCommand(
            command="G1",
            parameters={"X": 10, "Y": 10, "Z": 0.3, "F": 5000},
            comment="Move to prime position"
        ))

        # Prime line
        commands.append(GcodeCommand(
            command="G1",
            parameters={"X": 10, "Y": 100, "E": self.settings.prime_volume, "F": 1500},
            comment="Prime line"
        ))
        commands.append(GcodeCommand(
            command="G1",
            parameters={"X": 11, "Y": 100},
            comment="Move over"
        ))
        commands.append(GcodeCommand(
            command="G1",
            parameters={"X": 11, "Y": 10, "E": self.settings.prime_volume * 2, "F": 1500},
            comment="Prime line return"
        ))

        # Retract
        commands.append(GcodeCommand(
            command="G1",
            parameters={"E": -self.settings.retraction_distance, "F": self.settings.retraction_speed * 60},
            comment="Retract"
        ))

        # Lift Z
        commands.append(GcodeCommand(
            command="G1",
            parameters={"Z": 2, "F": 3000},
            comment="Lift Z"
        ))

        return commands

    def _process_layer(self, layer_data: Any, layer_idx: int) -> GcodeLayer:
        """Process a single layer into G-code."""
        gcode_layer = GcodeLayer(
            layer_number=layer_idx,
            z_height=layer_data.z_height
        )

        # Layer change
        if self.settings.layer_change_gcode:
            for line in self.settings.layer_change_gcode.split('\n'):
                if line.strip():
                    gcode_layer.commands.append(GcodeCommand(command=line))

        # Move to layer height
        gcode_layer.commands.append(GcodeCommand(
            command="G1",
            parameters={"Z": layer_data.z_height, "F": self.settings.travel_speed * 60},
            comment=f"Move to layer {layer_idx}"
        ))

        # Process perimeters
        for perimeter in layer_data.perimeters:
            commands = self._generate_path_commands(
                perimeter,
                self.settings.perimeter_speed,
                "Perimeter"
            )
            gcode_layer.commands.extend(commands)

        # Process infill
        for infill in layer_data.infill:
            commands = self._generate_path_commands(
                infill,
                self.settings.infill_speed,
                "Infill"
            )
            gcode_layer.commands.extend(commands)

        # Process solid infill
        for solid in layer_data.solid_infill:
            commands = self._generate_path_commands(
                solid,
                self.settings.print_speed,
                "Solid infill"
            )
            gcode_layer.commands.extend(commands)

        # Process supports
        for support in layer_data.supports:
            commands = self._generate_path_commands(
                support,
                self.settings.support_speed,
                "Support"
            )
            gcode_layer.commands.extend(commands)

        # Process bridges with special settings
        for bridge in layer_data.bridges:
            commands = self._generate_bridge_commands(bridge)
            gcode_layer.commands.extend(commands)

        # Calculate layer statistics
        gcode_layer.print_time = self._calculate_layer_time(gcode_layer)
        gcode_layer.extrusion_length = self._calculate_layer_extrusion(gcode_layer)
        gcode_layer.travel_distance = self._calculate_layer_travel(gcode_layer)

        return gcode_layer

    def _generate_path_commands(self, path: List[Tuple[float, float]],
                               speed: float, path_type: str) -> List[GcodeCommand]:
        """Generate G-code commands for a path."""
        commands = []

        if not path:
            return commands

        # Travel to start of path
        start_point = path[0]
        if self._needs_travel(start_point):
            # Retract if needed
            if not self.is_retracted:
                commands.extend(self._generate_retraction())

            # Travel move
            commands.append(GcodeCommand(
                command="G0",
                parameters={
                    "X": start_point[0],
                    "Y": start_point[1],
                    "F": self.settings.travel_speed * 60
                },
                comment=f"Travel to {path_type}",
                is_movement=True
            ))

            # Update position
            self.current_position[0] = start_point[0]
            self.current_position[1] = start_point[1]

            # Unretract
            if self.is_retracted:
                commands.extend(self._generate_unretraction())

        # Extrusion moves along path
        for i in range(1, len(path)):
            point = path[i]
            prev_point = path[i-1]

            # Calculate extrusion
            distance = np.sqrt((point[0] - prev_point[0])**2 +
                             (point[1] - prev_point[1])**2)
            extrusion = self._calculate_extrusion(distance)

            # Generate move command
            cmd = GcodeCommand(
                command="G1",
                parameters={
                    "X": point[0],
                    "Y": point[1],
                    "E": self.current_e + extrusion,
                    "F": speed * 60
                },
                is_movement=True,
                extrusion_amount=extrusion,
                speed=speed
            )

            # Add arc fitting if enabled
            if self.settings.arc_fitting and i < len(path) - 1:
                arc_cmd = self._try_arc_fitting(prev_point, point, path[i+1])
                if arc_cmd:
                    cmd = arc_cmd

            commands.append(cmd)

            # Update state
            self.current_position[0] = point[0]
            self.current_position[1] = point[1]
            self.current_e += extrusion

        return commands

    def _generate_bridge_commands(self, bridge: List[Tuple[float, float]]) -> List[GcodeCommand]:
        """Generate G-code for bridging with special settings."""
        commands = []

        # Set bridge fan speed
        if self.settings.cooling_enabled:
            commands.append(GcodeCommand(
                command="M106",
                parameters={"S": int(self.settings.bridge_fan_speed * 2.55)},
                comment="Bridge cooling"
            ))

        # Generate bridge path
        bridge_commands = self._generate_path_commands(
            bridge,
            self.settings.bridge_speed,
            "Bridge"
        )
        commands.extend(bridge_commands)

        # Restore normal fan speed
        if self.settings.cooling_enabled:
            commands.append(GcodeCommand(
                command="M106",
                parameters={"S": int(self.current_fan_speed * 2.55)},
                comment="Restore cooling"
            ))

        return commands

    def _needs_travel(self, target: Tuple[float, float]) -> bool:
        """Check if travel move is needed."""
        distance = np.sqrt((target[0] - self.current_position[0])**2 +
                          (target[1] - self.current_position[1])**2)
        return distance > 0.1  # 0.1mm threshold

    def _generate_retraction(self) -> List[GcodeCommand]:
        """Generate retraction commands."""
        commands = []

        if self.settings.before_retraction_gcode:
            commands.append(GcodeCommand(command=self.settings.before_retraction_gcode))

        if self.settings.firmware_retraction_enabled:
            commands.append(GcodeCommand(
                command="G10",
                comment="Firmware retraction"
            ))
        else:
            # Z hop
            if self.settings.retraction_lift_z > 0:
                commands.append(GcodeCommand(
                    command="G1",
                    parameters={
                        "Z": self.current_position[2] + self.settings.retraction_lift_z,
                        "F": self.settings.travel_speed * 60
                    },
                    comment="Z hop"
                ))

            # Retract filament
            commands.append(GcodeCommand(
                command="G1",
                parameters={
                    "E": self.current_e - self.settings.retraction_distance,
                    "F": self.settings.retraction_speed * 60
                },
                comment="Retract"
            ))
            self.current_e -= self.settings.retraction_distance

        if self.settings.after_retraction_gcode:
            commands.append(GcodeCommand(command=self.settings.after_retraction_gcode))

        self.is_retracted = True
        return commands

    def _generate_unretraction(self) -> List[GcodeCommand]:
        """Generate unretraction commands."""
        commands = []

        if self.settings.firmware_retraction_enabled:
            commands.append(GcodeCommand(
                command="G11",
                comment="Firmware unretraction"
            ))
        else:
            # Unretract filament
            extra_prime = self.settings.retraction_extra_prime
            commands.append(GcodeCommand(
                command="G1",
                parameters={
                    "E": self.current_e + self.settings.retraction_distance + extra_prime,
                    "F": self.settings.retraction_speed * 60
                },
                comment="Unretract"
            ))
            self.current_e += self.settings.retraction_distance + extra_prime

            # Lower Z
            if self.settings.retraction_lift_z > 0:
                commands.append(GcodeCommand(
                    command="G1",
                    parameters={
                        "Z": self.current_position[2],
                        "F": self.settings.travel_speed * 60
                    },
                    comment="Z unlift"
                ))

        self.is_retracted = False
        return commands

    def _calculate_extrusion(self, distance: float) -> float:
        """Calculate extrusion amount for distance."""
        # Calculate volume of filament
        nozzle_diameter = 0.4  # Default nozzle
        layer_height = 0.2  # Default layer height

        # Extrusion width (typically 120% of nozzle diameter)
        extrusion_width = nozzle_diameter * 1.2

        # Volume of extruded material
        volume = distance * extrusion_width * layer_height

        # Calculate filament length
        filament_radius = self.settings.filament_diameter / 2
        filament_area = np.pi * filament_radius * filament_radius
        filament_length = volume / filament_area

        return filament_length

    def _try_arc_fitting(self, p1: Tuple[float, float],
                        p2: Tuple[float, float],
                        p3: Tuple[float, float]) -> Optional[GcodeCommand]:
        """Try to fit arc to three points."""
        if not self.settings.arc_fitting:
            return None

        # Calculate if points form an arc within tolerance
        # Simplified - production would use proper arc detection

        # Check if points are collinear
        v1 = np.array([p2[0] - p1[0], p2[1] - p1[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])

        cross = np.cross(v1, v2)
        if abs(cross) < 0.01:  # Nearly collinear
            return None

        # Could be an arc - generate G2/G3 command
        # This is simplified - production would calculate actual arc parameters

        return None  # For now, don't generate arcs

    def _update_cooling(self, layer: GcodeLayer):
        """Update cooling settings for layer."""
        layer_num = layer.layer_number

        if not self.settings.cooling_enabled:
            return

        # Determine fan speed
        if layer_num < self.settings.disable_fan_first_layers:
            fan_speed = 0
        elif layer_num < self.settings.full_fan_speed_layer:
            # Ramp up fan speed
            progress = (layer_num - self.settings.disable_fan_first_layers) / \
                      (self.settings.full_fan_speed_layer - self.settings.disable_fan_first_layers)
            fan_speed = self.settings.min_fan_speed + \
                       (self.settings.max_fan_speed - self.settings.min_fan_speed) * progress
        else:
            fan_speed = self.settings.max_fan_speed

        # Apply cooling strategy
        if self.settings.cooling_strategy == CoolingStrategy.AGGRESSIVE:
            fan_speed = min(100, fan_speed * 1.2)
        elif self.settings.cooling_strategy == CoolingStrategy.MINIMAL:
            fan_speed = fan_speed * 0.5

        # Set fan speed if changed
        if abs(fan_speed - self.current_fan_speed) > 1:
            layer.commands.insert(0, GcodeCommand(
                command="M106",
                parameters={"S": int(fan_speed * 2.55)},
                comment=f"Set fan to {fan_speed}%"
            ))
            self.current_fan_speed = fan_speed

    def _generate_end_gcode(self) -> List[GcodeCommand]:
        """Generate end G-code commands."""
        commands = []

        # Custom end G-code
        if self.settings.end_gcode:
            for line in self.settings.end_gcode.split('\n'):
                if line.strip():
                    commands.append(GcodeCommand(command=line))
        else:
            # Default end sequence
            commands.extend(self._generate_default_end_sequence())

        return commands

    def _generate_default_end_sequence(self) -> List[GcodeCommand]:
        """Generate default end sequence."""
        commands = []

        # Retract filament
        commands.append(GcodeCommand(
            command="G1",
            parameters={"E": self.current_e - 5, "F": self.settings.retraction_speed * 60},
            comment="Final retraction"
        ))

        # Turn off heaters
        commands.append(GcodeCommand(
            command="M104",
            parameters={"S": 0},
            comment="Turn off nozzle"
        ))
        commands.append(GcodeCommand(
            command="M140",
            parameters={"S": 0},
            comment="Turn off bed"
        ))

        # Turn off fan
        commands.append(GcodeCommand(
            command="M106",
            parameters={"S": 0},
            comment="Turn off fan"
        ))

        # Move to safe position
        commands.append(GcodeCommand(
            command="G91",
            comment="Relative positioning"
        ))
        commands.append(GcodeCommand(
            command="G1",
            parameters={"Z": 10, "F": 3000},
            comment="Lift Z"
        ))
        commands.append(GcodeCommand(
            command="G90",
            comment="Absolute positioning"
        ))
        commands.append(GcodeCommand(
            command="G1",
            parameters={"X": 0, "Y": self.settings.bed_size_y, "F": 3000},
            comment="Present print"
        ))

        # Disable steppers
        commands.append(GcodeCommand(
            command="M84",
            comment="Disable steppers"
        ))

        return commands

    def _calculate_layer_time(self, layer: GcodeLayer) -> float:
        """Calculate print time for layer."""
        time = 0

        for command in layer.commands:
            if command.is_movement:
                # Calculate time based on speed
                if command.speed:
                    # Simplified - would need actual distance calculation
                    time += 1.0 / command.speed  # Rough estimate

        return time

    def _calculate_layer_extrusion(self, layer: GcodeLayer) -> float:
        """Calculate total extrusion for layer."""
        return sum(cmd.extrusion_amount for cmd in layer.commands)

    def _calculate_layer_travel(self, layer: GcodeLayer) -> float:
        """Calculate travel distance for layer."""
        distance = 0
        prev_pos = self.current_position.copy()

        for command in layer.commands:
            if command.is_movement:
                # Extract position from parameters
                if 'X' in command.parameters and 'Y' in command.parameters:
                    new_pos = np.array([
                        command.parameters['X'],
                        command.parameters['Y'],
                        prev_pos[2]
                    ])
                    distance += np.linalg.norm(new_pos - prev_pos)
                    prev_pos = new_pos

        return distance

    def _calculate_filament_weight(self, length_mm: float) -> float:
        """Calculate filament weight from length."""
        radius_mm = self.settings.filament_diameter / 2
        volume_mm3 = length_mm * np.pi * radius_mm * radius_mm
        volume_cm3 = volume_mm3 / 1000
        weight_g = volume_cm3 * self.settings.filament_density
        return weight_g

    def _calculate_bounding_box(self) -> Tuple[float, float, float]:
        """Calculate bounding box of print."""
        if not self.layers:
            return (0, 0, 0)

        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')

        for layer in self.layers:
            max_z = max(max_z, layer.z_height)
            min_z = min(min_z, layer.z_height)

            for command in layer.commands:
                if command.is_movement and command.parameters:
                    if 'X' in command.parameters:
                        min_x = min(min_x, command.parameters['X'])
                        max_x = max(max_x, command.parameters['X'])
                    if 'Y' in command.parameters:
                        min_y = min(min_y, command.parameters['Y'])
                        max_y = max(max_y, command.parameters['Y'])

        return (max_x - min_x, max_y - min_y, max_z - min_z)

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate G-code statistics."""
        stats = {
            'layer_count': len(self.layers),
            'average_layer_time': sum(l.print_time for l in self.layers) / len(self.layers) if self.layers else 0,
            'movement_commands': sum(1 for l in self.layers for c in l.commands if c.is_movement),
            'retraction_count': sum(1 for l in self.layers for c in l.commands if 'retract' in (c.comment or '').lower()),
            'max_x': 0,
            'max_y': 0,
            'max_z': 0,
            'gcode_flavor': self.settings.gcode_flavor.value
        }

        # Find max coordinates
        for layer in self.layers:
            for command in layer.commands:
                if command.parameters:
                    stats['max_x'] = max(stats['max_x'], command.parameters.get('X', 0))
                    stats['max_y'] = max(stats['max_y'], command.parameters.get('Y', 0))
                    stats['max_z'] = max(stats['max_z'], command.parameters.get('Z', 0))

        return stats

    def _generate_gcode_content(self, start_commands: List[GcodeCommand],
                               layers: List[GcodeLayer],
                               end_commands: List[GcodeCommand]) -> str:
        """Generate complete G-code file content."""
        lines = []

        # Add metadata if enabled
        if self.settings.include_metadata:
            lines.extend(self._generate_metadata())

        # Add start commands
        for cmd in start_commands:
            lines.append(self._format_command(cmd))

        # Add layer commands
        for layer in layers:
            if self.settings.gcode_comments:
                lines.append(f"; Layer {layer.layer_number} at Z={layer.z_height:.2f}")

            for cmd in layer.commands:
                lines.append(self._format_command(cmd))

        # Add end commands
        for cmd in end_commands:
            lines.append(self._format_command(cmd))

        return '\n'.join(lines)

    def _generate_metadata(self) -> List[str]:
        """Generate G-code metadata comments."""
        metadata = [
            "; Generated by 3D Print CAD Assistant",
            f"; Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"; Printer: {self.settings.machine_name}",
            f"; Filament: {self.settings.filament_diameter}mm",
            f"; Nozzle Temperature: {self.settings.nozzle_temperature}°C",
            f"; Bed Temperature: {self.settings.bed_temperature}°C",
            f"; Layer Count: {len(self.layers)}",
            ";"
        ]
        return metadata

    def _format_command(self, cmd: GcodeCommand) -> str:
        """Format a G-code command as string."""
        if cmd.command == ";":
            # Pure comment
            return f"; {cmd.comment}" if cmd.comment else ";"

        # Build command string
        parts = [cmd.command]

        # Add parameters
        for key, value in cmd.parameters.items():
            if isinstance(value, float):
                parts.append(f"{key}{value:.3f}")
            else:
                parts.append(f"{key}{value}")

        # Add comment if enabled
        if self.settings.gcode_comments and cmd.comment:
            return f"{' '.join(parts)} ; {cmd.comment}"
        else:
            return ' '.join(parts)