"""Tcl/Tk/AWK-inspired text processing and GUI for 3D CAD operations."""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Tuple, Match
from pathlib import Path


class TextProcessingStyle(Enum):
    """Text processing styles."""
    AWK = "awk"              # AWK-style field processing
    TCL = "tcl"              # Tcl-style string processing
    SED = "sed"              # Sed-style stream editing
    PERL = "perl"            # Perl-style regex processing
    CUSTOM = "custom"        # Custom text processing


@dataclass
class TextPattern:
    """Text pattern for matching."""
    pattern: str
    regex: Optional[re.Pattern] = None
    fields: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.regex and self.pattern:
            try:
                self.regex = re.compile(self.pattern)
            except re.error:
                pass

    def matches(self, text: str) -> Optional[Match]:
        """Check if pattern matches text."""
        if self.regex:
            return self.regex.search(text)
        return None


class AWKStyleProcessor:
    """AWK-inspired text processor."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.patterns: List[TextPattern] = []
        self.field_separators: Dict[str, str] = {}
        self.variables: Dict[str, Any] = {}

    def add_pattern(self, pattern: TextPattern) -> None:
        """Add processing pattern."""
        self.patterns.append(pattern)

    def set_field_separator(self, separator: str, name: str = "default") -> None:
        """Set field separator."""
        self.field_separators[name] = separator

    def process_text(self, text: str, separator_name: str = "default") -> Dict[str, Any]:
        """Process text using AWK-style patterns."""
        separator = self.field_separators.get(separator_name, " ")

        # Split into records and fields
        records = text.split('\n')
        processed_records = []

        for record in records:
            if not record.strip():
                continue

            # Split into fields
            fields = record.split(separator)

            # Apply patterns
            for pattern in self.patterns:
                match = pattern.matches(record)

                if match:
                    # Apply pattern actions
                    processed_record = self._apply_pattern_actions(pattern, fields, match)
                    processed_records.append(processed_record)
                    break
            else:
                # No pattern matched
                processed_records.append({
                    "original": record,
                    "fields": fields,
                    "matched": False
                })

        return {
            "processed_records": len(processed_records),
            "records": processed_records,
            "separator_used": separator,
            "patterns_applied": len(self.patterns)
        }

    def _apply_pattern_actions(self, pattern: TextPattern,
                              fields: List[str], match: Match) -> Dict[str, Any]:
        """Apply pattern actions."""
        result = {
            "original": " ".join(fields),
            "fields": fields,
            "matched": True,
            "pattern": pattern.pattern,
            "processed": False
        }

        # Apply field actions
        for action in pattern.actions:
            if action.startswith("print"):
                result["output"] = " ".join(fields)
            elif action.startswith("sum"):
                # Sum numeric fields
                try:
                    numeric_fields = [float(f) for f in fields if f.replace('.', '').isdigit()]
                    result["sum"] = sum(numeric_fields)
                except ValueError:
                    result["sum"] = 0
            elif action.startswith("count"):
                result["count"] = len(fields)

        result["processed"] = True
        return result

    def extract_numeric_data(self, text: str) -> List[float]:
        """Extract numeric data from text."""
        # Find all numbers in text
        numbers = re.findall(r'[-+]?\d*\.?\d+', text)

        try:
            return [float(num) for num in numbers]
        except ValueError:
            return []

    def process_cad_log(self, log_content: str) -> Dict[str, Any]:
        """Process CAD log file."""
        log_analysis = {
            "total_lines": len(log_content.split('\n')),
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "processing_times": [],
            "errors": [],
            "warnings": []
        }

        try:
            lines = log_content.split('\n')

            for line in lines:
                line_lower = line.lower()

                if "error" in line_lower:
                    log_analysis["error_count"] += 1
                    log_analysis["errors"].append(line.strip())

                elif "warning" in line_lower:
                    log_analysis["warning_count"] += 1
                    log_analysis["warnings"].append(line.strip())

                elif "info" in line_lower or "processing" in line_lower:
                    log_analysis["info_count"] += 1

                # Extract processing times
                time_match = re.search(r'(\d+\.?\d*)s', line)
                if time_match:
                    try:
                        processing_time = float(time_match.group(1))
                        log_analysis["processing_times"].append(processing_time)
                    except ValueError:
                        pass

        except Exception as e:
            log_analysis["error"] = str(e)

        return log_analysis

    def parse_gcode(self, gcode_content: str) -> Dict[str, Any]:
        """Parse G-code file."""
        gcode_analysis = {
            "total_lines": len(gcode_content.split('\n')),
            "commands": defaultdict(int),
            "coordinates": [],
            "movements": [],
            "layers": 0,
            "print_time_estimate": 0.0
        }

        try:
            lines = gcode_content.split('\n')

            for line in lines:
                line = line.strip()
                if not line or line.startswith(';'):
                    continue

                # Parse G-code commands
                if line.startswith('G'):
                    gcode_analysis["commands"]["G"] += 1
                elif line.startswith('M'):
                    gcode_analysis["commands"]["M"] += 1
                elif line.startswith('T'):
                    gcode_analysis["commands"]["T"] += 1

                # Extract coordinates
                coord_match = re.findall(r'[XYZEF]\s*([-+]?\d*\.?\d+)', line)
                if coord_match:
                    try:
                        coords = [float(coord) for coord in coord_match]
                        gcode_analysis["coordinates"].extend(coords)
                    except ValueError:
                        pass

                # Count layers (Z coordinate changes)
                if 'Z' in line:
                    gcode_analysis["layers"] += 1

        except Exception as e:
            gcode_analysis["error"] = str(e)

        return gcode_analysis


class TclStyleInterpreter:
    """Tcl-inspired command interpreter."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.commands: Dict[str, Callable] = {}
        self.variables: Dict[str, Any] = {}
        self.procedures: Dict[str, str] = {}

    def register_command(self, command_name: str, command_func: Callable) -> None:
        """Register Tcl-style command."""
        self.commands[command_name] = command_func

    def define_variable(self, var_name: str, value: Any) -> None:
        """Define Tcl-style variable."""
        self.variables[var_name] = value

    def define_procedure(self, proc_name: str, body: str) -> None:
        """Define Tcl-style procedure."""
        self.procedures[proc_name] = body

    def execute_command(self, command: str) -> Any:
        """Execute Tcl-style command."""
        command = command.strip()

        if not command:
            return None

        try:
            # Parse command
            parts = command.split()
            if not parts:
                return None

            cmd_name = parts[0]

            if cmd_name in self.commands:
                # Execute built-in command
                return self.commands[cmd_name](*parts[1:])
            elif cmd_name in self.procedures:
                # Execute procedure
                return self._execute_procedure(cmd_name, parts[1:])
            else:
                # Variable substitution
                if cmd_name.startswith('$'):
                    var_name = cmd_name[1:]
                    return self.variables.get(var_name, cmd_name)

        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return None

    def _execute_procedure(self, proc_name: str, args: List[str]) -> Any:
        """Execute procedure."""
        procedure_body = self.procedures[proc_name]

        # Simple argument substitution
        for i, arg in enumerate(args):
            procedure_body = procedure_body.replace(f"arg{i}", arg)

        # Execute procedure body
        return self.execute_command(procedure_body)

    def evaluate_expression(self, expression: str) -> Any:
        """Evaluate Tcl-style expression."""
        # Simple expression evaluation
        try:
            # Replace variables
            for var_name, var_value in self.variables.items():
                expression = expression.replace(f"${var_name}", str(var_value))

            # Replace commands in brackets
            expression = self._substitute_bracketed_commands(expression)

            return eval(expression, {"__builtins__": {}})

        except Exception as e:
            self.logger.error(f"Expression evaluation failed: {e}")
            return expression

    def _substitute_bracketed_commands(self, expression: str) -> str:
        """Substitute bracketed commands."""
        # Find [command] patterns
        bracket_pattern = re.compile(r'\[([^\]]+)\]')

        def replace_command(match):
            command = match.group(1)
            result = self.execute_command(command)
            return str(result) if result is not None else ""

        return bracket_pattern.sub(replace_command, expression)


class TkStyleGUI:
    """Tcl/Tk-inspired GUI system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.widgets: Dict[str, Dict[str, Any]] = {}
        self.windows: Dict[str, Dict[str, Any]] = {}
        self.event_handlers: Dict[str, Callable] = {}

    def create_window(self, window_name: str, title: str = "",
                     width: int = 400, height: int = 300) -> Dict[str, Any]:
        """Create GUI window."""
        window = {
            "name": window_name,
            "title": title,
            "width": width,
            "height": height,
            "widgets": [],
            "visible": False,
            "created_at": time.time()
        }

        self.windows[window_name] = window

        self.logger.info(f"Created window: {window_name}")
        return window

    def add_widget(self, window_name: str, widget_type: str,
                  widget_name: str, properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add widget to window."""
        if window_name not in self.windows:
            return {"error": f"Window {window_name} not found"}

        widget = {
            "type": widget_type,
            "name": widget_name,
            "properties": properties or {},
            "position": properties.get("position", (0, 0)) if properties else (0, 0),
            "size": properties.get("size", (100, 30)) if properties else (100, 30),
            "visible": True,
            "created_at": time.time()
        }

        self.widgets[widget_name] = widget
        self.windows[window_name]["widgets"].append(widget_name)

        self.logger.info(f"Added widget {widget_name} to window {window_name}")
        return widget

    def bind_event(self, widget_name: str, event: str, handler: Callable) -> None:
        """Bind event to widget."""
        event_key = f"{widget_name}:{event}"
        self.event_handlers[event_key] = handler

    def show_window(self, window_name: str) -> Dict[str, Any]:
        """Show GUI window."""
        if window_name not in self.windows:
            return {"error": f"Window {window_name} not found"}

        window = self.windows[window_name]
        window["visible"] = True

        return {
            "window_name": window_name,
            "title": window["title"],
            "widgets": len(window["widgets"]),
            "displayed": True
        }

    def create_cad_interface(self, interface_name: str) -> Dict[str, Any]:
        """Create CAD interface."""
        # Create main window
        main_window = self.create_window(
            f"{interface_name}_main",
            "3D CAD Assistant",
            1000, 700
        )

        # Add CAD-specific widgets
        widgets_added = []

        # Menu bar
        menu_widget = self.add_widget(
            f"{interface_name}_main",
            "menu",
            f"{interface_name}_menu",
            {"items": ["File", "Edit", "View", "Tools", "Help"]}
        )
        widgets_added.append(menu_widget)

        # Toolbar
        toolbar_widget = self.add_widget(
            f"{interface_name}_main",
            "toolbar",
            f"{interface_name}_toolbar",
            {"buttons": ["Open", "Save", "Export", "Settings"]}
        )
        widgets_added.append(toolbar_widget)

        # 3D viewer
        viewer_widget = self.add_widget(
            f"{interface_name}_main",
            "canvas",
            f"{interface_name}_viewer",
            {"width": 600, "height": 400, "type": "3d_viewer"}
        )
        widgets_added.append(viewer_widget)

        # Properties panel
        properties_widget = self.add_widget(
            f"{interface_name}_main",
            "panel",
            f"{interface_name}_properties",
            {"title": "Properties", "fields": ["Vertices", "Faces", "Volume", "Material"]}
        )
        widgets_added.append(properties_widget)

        # Status bar
        status_widget = self.add_widget(
            f"{interface_name}_main",
            "status",
            f"{interface_name}_status",
            {"message": "Ready"}
        )
        widgets_added.append(status_widget)

        return {
            "interface_name": interface_name,
            "main_window": f"{interface_name}_main",
            "widgets_added": len(widgets_added),
            "widgets": [w["name"] for w in widgets_added],
            "cad_specific": True
        }

    def get_gui_layout(self, window_name: str) -> Dict[str, Any]:
        """Get GUI layout."""
        if window_name not in self.windows:
            return {"error": f"Window {window_name} not found"}

        window = self.windows[window_name]

        return {
            "window_name": window_name,
            "title": window["title"],
            "dimensions": (window["width"], window["height"]),
            "widget_count": len(window["widgets"]),
            "widgets": [
                {
                    "name": widget_name,
                    "type": self.widgets[widget_name]["type"],
                    "position": self.widgets[widget_name]["position"],
                    "size": self.widgets[widget_name]["size"]
                }
                for widget_name in window["widgets"]
            ],
            "layout_type": "tcl_tk_style"
        }


class CADTextProcessor:
    """CAD text processing system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.awk_processor = AWKStyleProcessor()
        self.tcl_interpreter = TclStyleInterpreter()
        self.gui_builder = TkStyleGUI()
        self.text_patterns: Dict[str, TextPattern] = {}

    def initialize_text_system(self) -> bool:
        """Initialize text processing system."""
        try:
            # Setup AWK patterns for CAD files
            self._setup_cad_patterns()

            # Setup Tcl commands
            self._setup_tcl_commands()

            # Setup GUI components
            self._setup_gui_components()

            self.logger.info("CAD text processing system initialized")
            return True

        except Exception as e:
            self.logger.error(f"Text system initialization failed: {e}")
            return False

    def _setup_cad_patterns(self) -> None:
        """Setup CAD file patterns."""
        # STL file pattern
        stl_pattern = TextPattern(
            pattern=r'facet normal\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)',
            fields=["normal_x", "normal_y", "normal_z"],
            actions=["print", "sum"]
        )
        self.awk_processor.add_pattern(stl_pattern)
        self.text_patterns["stl_normal"] = stl_pattern

        # G-code pattern
        gcode_pattern = TextPattern(
            pattern=r'(G[0-9]+)\s+.*X\s*([-\d\.]+).*Y\s*([-\d\.]+).*Z\s*([-\d\.]+)',
            fields=["command", "x", "y", "z"],
            actions=["print", "count"]
        )
        self.awk_processor.add_pattern(gcode_pattern)
        self.text_patterns["gcode_movement"] = gcode_pattern

        # OBJ file pattern
        obj_pattern = TextPattern(
            pattern=r'^v\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)',
            fields=["x", "y", "z"],
            actions=["print", "sum"]
        )
        self.awk_processor.add_pattern(obj_pattern)
        self.text_patterns["obj_vertex"] = obj_pattern

    def _setup_tcl_commands(self) -> None:
        """Setup Tcl-style commands."""
        def cmd_set(var_name: str, value: str) -> None:
            """Set variable command."""
            self.tcl_interpreter.define_variable(var_name, value)

        def cmd_puts(message: str) -> None:
            """Print command."""
            self.logger.info(f"Tcl output: {message}")

        def cmd_expr(expression: str) -> Any:
            """Expression evaluation command."""
            return self.tcl_interpreter.evaluate_expression(expression)

        def cmd_proc(proc_name: str, args: str, body: str) -> None:
            """Procedure definition command."""
            self.tcl_interpreter.define_procedure(proc_name, body)

        self.tcl_interpreter.register_command("set", cmd_set)
        self.tcl_interpreter.register_command("puts", cmd_puts)
        self.tcl_interpreter.register_command("expr", cmd_expr)
        self.tcl_interpreter.register_command("proc", cmd_proc)

    def _setup_gui_components(self) -> None:
        """Setup GUI components."""
        # Create default CAD interface
        self.gui_builder.create_cad_interface("default_cad")

    def process_cad_file(self, file_content: str, file_type: str) -> Dict[str, Any]:
        """Process CAD file using text processing."""
        processing_result = {
            "file_type": file_type,
            "processing_timestamp": time.time(),
            "lines_processed": len(file_content.split('\n')),
            "patterns_matched": 0,
            "extracted_data": {},
            "processing_success": True
        }

        try:
            if file_type.lower() == "stl":
                result = self._process_stl_file(file_content)
                processing_result.update(result)

            elif file_type.lower() == "gcode":
                result = self._process_gcode_file(file_content)
                processing_result.update(result)

            elif file_type.lower() == "obj":
                result = self._process_obj_file(file_content)
                processing_result.update(result)

            else:
                # Generic text processing
                result = self.awk_processor.process_text(file_content)
                processing_result.update(result)

        except Exception as e:
            processing_result["processing_success"] = False
            processing_result["error"] = str(e)

        return processing_result

    def _process_stl_file(self, content: str) -> Dict[str, Any]:
        """Process STL file."""
        normals = []
        vertices = []

        # Extract normals and vertices
        normal_pattern = r'facet normal\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)'
        vertex_pattern = r'vertex\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)'

        for line in content.split('\n'):
            # Extract normals
            normal_match = re.search(normal_pattern, line)
            if normal_match:
                normal = [float(normal_match.group(i)) for i in range(1, 4)]
                normals.append(normal)

            # Extract vertices
            vertex_match = re.search(vertex_pattern, line)
            if vertex_match:
                vertex = [float(vertex_match.group(i)) for i in range(1, 4)]
                vertices.append(vertex)

        return {
            "normals_extracted": len(normals),
            "vertices_extracted": len(vertices),
            "triangles": len(vertices) // 3 if vertices else 0,
            "stl_specific": True
        }

    def _process_gcode_file(self, content: str) -> Dict[str, Any]:
        """Process G-code file."""
        gcode_analysis = self.awk_processor.parse_gcode(content)

        # Extract additional information
        total_distance = 0
        coordinates = []

        for line in content.split('\n'):
            # Extract movement commands
            if re.search(r'G[01]\s', line):
                coord_match = re.findall(r'[XYZEF]\s*([-+]?\d*\.?\d+)', line)
                if coord_match:
                    try:
                        coords = [float(coord) for coord in coord_match]
                        coordinates.extend(coords)
                    except ValueError:
                        pass

        return {
            "gcode_analysis": gcode_analysis,
            "coordinates_extracted": len(coordinates),
            "estimated_print_time": gcode_analysis.get("print_time_estimate", 0),
            "movement_commands": gcode_analysis.get("commands", {}).get("G", 0)
        }

    def _process_obj_file(self, content: str) -> Dict[str, Any]:
        """Process OBJ file."""
        vertices = []
        faces = []
        materials = []

        for line in content.split('\n'):
            # Extract vertices
            if line.startswith('v '):
                coords = re.findall(r'[-+]?\d*\.?\d+', line[2:])
                if len(coords) >= 3:
                    try:
                        vertex = [float(coords[i]) for i in range(3)]
                        vertices.append(vertex)
                    except ValueError:
                        pass

            # Extract faces
            elif line.startswith('f '):
                face_indices = re.findall(r'\d+', line[2:])
                if face_indices:
                    faces.append([int(idx) - 1 for idx in face_indices])  # Convert to 0-based

            # Extract materials
            elif line.startswith('mtllib ') or line.startswith('usemtl '):
                materials.append(line.strip())

        return {
            "vertices_extracted": len(vertices),
            "faces_extracted": len(faces),
            "materials_found": len(materials),
            "obj_specific": True
        }

    def create_cad_script(self, script_name: str, script_content: str) -> Dict[str, Any]:
        """Create CAD script."""
        script_result = {
            "script_name": script_name,
            "script_length": len(script_content),
            "commands_parsed": 0,
            "variables_defined": 0,
            "procedures_defined": 0
        }

        try:
            # Parse script content
            lines = script_content.split('\n')

            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Execute Tcl-style command
                result = self.tcl_interpreter.execute_command(line)
                script_result["commands_parsed"] += 1

                # Check for variable definitions
                if line.startswith('set '):
                    script_result["variables_defined"] += 1

                # Check for procedure definitions
                if line.startswith('proc '):
                    script_result["procedures_defined"] += 1

        except Exception as e:
            script_result["error"] = str(e)

        return script_result

    def generate_gui_layout(self, layout_name: str, layout_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate GUI layout."""
        layout_result = {
            "layout_name": layout_name,
            "specification": layout_spec,
            "windows_created": 0,
            "widgets_added": 0,
            "layout_success": True
        }

        try:
            # Create windows
            windows = layout_spec.get("windows", [])

            for window_spec in windows:
                window_name = window_spec.get("name", f"window_{int(time.time())}")
                window = self.gui_builder.create_window(
                    window_name,
                    window_spec.get("title", ""),
                    window_spec.get("width", 400),
                    window_spec.get("height", 300)
                )
                layout_result["windows_created"] += 1

                # Add widgets
                widgets = window_spec.get("widgets", [])

                for widget_spec in widgets:
                    widget = self.gui_builder.add_widget(
                        window_name,
                        widget_spec.get("type", "button"),
                        widget_spec.get("name", "widget"),
                        widget_spec.get("properties", {})
                    )
                    layout_result["widgets_added"] += 1

                    # Bind events if specified
                    if "events" in widget_spec:
                        for event, handler in widget_spec["events"].items():
                            self.gui_builder.bind_event(widget["name"], event, handler)

        except Exception as e:
            layout_result["layout_success"] = False
            layout_result["error"] = str(e)

        return layout_result

    def get_text_processing_stats(self) -> Dict[str, Any]:
        """Get text processing statistics."""
        return {
            "awk_processor": {
                "patterns": len(self.awk_processor.patterns),
                "field_separators": len(self.awk_processor.field_separators),
                "variables": len(self.awk_processor.variables)
            },
            "tcl_interpreter": {
                "commands": len(self.tcl_interpreter.commands),
                "variables": len(self.tcl_interpreter.variables),
                "procedures": len(self.tcl_interpreter.procedures)
            },
            "gui_builder": {
                "windows": len(self.gui_builder.windows),
                "widgets": len(self.gui_builder.widgets),
                "event_handlers": len(self.gui_builder.event_handlers)
            },
            "text_patterns": len(self.text_patterns),
            "processing_capabilities": [
                "stl_file_processing",
                "gcode_analysis",
                "obj_file_processing",
                "log_analysis",
                "script_execution",
                "gui_generation"
            ]
        }


class CADTextInterface:
    """Complete CAD text interface system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.text_processor = CADTextProcessor()
        self.script_library: Dict[str, str] = {}
        self.gui_interfaces: Dict[str, Dict[str, Any]] = {}

    def initialize_text_interface(self) -> bool:
        """Initialize text interface."""
        try:
            if not self.text_processor.initialize_text_system():
                return False

            # Setup script library
            self._setup_script_library()

            self.logger.info("CAD text interface initialized")
            return True

        except Exception as e:
            self.logger.error(f"Text interface initialization failed: {e}")
            return False

    def _setup_script_library(self) -> None:
        """Setup script library."""
        # CAD automation scripts
        self.script_library["mesh_analysis"] = """
        set input_file $input_file
        set output_file $output_file

        # Process mesh file
        set mesh_data [read_file $input_file]
        set vertices [extract_vertices $mesh_data]
        set faces [extract_faces $mesh_data]

        puts "Vertices: [llength $vertices]"
        puts "Faces: [llength $faces]"
        """

        self.script_library["batch_processing"] = """
        set input_dir $input_dir
        set output_dir $output_dir

        # Process all STL files in directory
        foreach file [glob $input_dir/*.stl] {
            set output_file [file join $output_dir [file tail $file]]
            process_stl $file $output_file
        }
        """

        self.script_library["quality_check"] = """
        set mesh_file $mesh_file

        # Quality analysis
        set mesh_data [load_mesh $mesh_file]
        set quality_score [analyze_quality $mesh_data]

        if {$quality_score < 0.5} {
            puts "Poor quality mesh detected"
        } else {
            puts "Mesh quality acceptable"
        }
        """

    def process_cad_text_data(self, text_data: str, data_type: str) -> Dict[str, Any]:
        """Process CAD text data."""
        return self.text_processor.process_cad_file(text_data, data_type)

    def execute_cad_script(self, script_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute CAD script."""
        if script_name not in self.script_library:
            return {"error": f"Script {script_name} not found"}

        script_content = self.script_library[script_name]

        # Substitute parameters
        for param_name, param_value in (parameters or {}).items():
            script_content = script_content.replace(f"${param_name}", str(param_value))

        return self.text_processor.create_cad_script(script_name, script_content)

    def create_custom_gui(self, gui_name: str, layout_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create custom GUI."""
        return self.text_processor.generate_gui_layout(gui_name, layout_spec)

    def analyze_cad_logs(self, log_files: List[str]) -> Dict[str, Any]:
        """Analyze CAD log files."""
        analysis_results = {
            "files_analyzed": len(log_files),
            "total_errors": 0,
            "total_warnings": 0,
            "total_processing_time": 0.0,
            "file_analyses": []
        }

        try:
            for log_file in log_files:
                try:
                    with open(log_file, 'r') as f:
                        log_content = f.read()

                    log_analysis = self.text_processor.awk_processor.process_cad_log(log_content)
                    analysis_results["file_analyses"].append({
                        "file": log_file,
                        "analysis": log_analysis
                    })

                    analysis_results["total_errors"] += log_analysis.get("error_count", 0)
                    analysis_results["total_warnings"] += log_analysis.get("warning_count", 0)
                    analysis_results["total_processing_time"] += sum(log_analysis.get("processing_times", []))

                except Exception as e:
                    self.logger.error(f"Log analysis failed for {log_file}: {e}")

        except Exception as e:
            analysis_results["error"] = str(e)

        return analysis_results

    def get_text_interface_summary(self) -> Dict[str, Any]:
        """Get text interface summary."""
        return {
            "text_processor": self.text_processor.get_text_processing_stats(),
            "script_library": len(self.script_library),
            "gui_interfaces": len(self.gui_interfaces),
            "available_scripts": list(self.script_library.keys()),
            "text_processing_features": [
                "stl_text_processing",
                "gcode_analysis",
                "obj_text_processing",
                "log_analysis",
                "tcl_scripting",
                "gui_generation"
            ]
        }


# Factory functions for text processing
def create_awk_processor() -> AWKStyleProcessor:
    """Create AWK-style processor."""
    return AWKStyleProcessor()


def create_tcl_interpreter() -> TclStyleInterpreter:
    """Create Tcl-style interpreter."""
    return TclStyleInterpreter()


def create_gui_builder() -> TkStyleGUI:
    """Create Tk-style GUI builder."""
    return TkStyleGUI()


def create_text_processor() -> CADTextProcessor:
    """Create CAD text processor."""
    return CADTextProcessor()


def create_text_interface() -> CADTextInterface:
    """Create CAD text interface."""
    return CADTextInterface()
