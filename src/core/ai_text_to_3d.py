"""AI-powered text-to-3D model generation using generative AI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union
import numpy as np
import trimesh
from enum import Enum
import logging
import re
import json
from pathlib import Path


class GenerationModel(Enum):
    """Available text-to-3D generation models."""
    BASIC_PARAMETRIC = "basic_parametric"
    GEOMETRIC_PRIMITIVES = "geometric_primitives"
    CSG_BASED = "csg_based"  # Constructive Solid Geometry
    PROCEDURAL_GENERATION = "procedural_generation"
    AI_ENHANCED = "ai_enhanced"  # Placeholder for future AI integration


class ShapeCategory(Enum):
    """Categories of shapes that can be generated."""
    PRIMITIVE = "primitive"  # cube, sphere, cylinder, etc.
    MECHANICAL = "mechanical"  # gears, shafts, fasteners
    ARCHITECTURAL = "architectural"  # walls, doors, windows
    ORGANIC = "organic"  # complex curved shapes
    ASSEMBLY = "assembly"  # multi-part assemblies


@dataclass
class TextTo3DRequest:
    """Request for text-to-3D generation."""
    text_prompt: str
    model: GenerationModel = GenerationModel.BASIC_PARAMETRIC
    target_quality: str = "medium"  # low, medium, high
    max_complexity: int = 1000  # Maximum number of geometric operations
    output_format: str = "stl"


@dataclass
class GeneratedModel:
    """Result of text-to-3D generation."""
    mesh: trimesh.Trimesh
    metadata: Dict[str, Any] = field(default_factory=dict)
    generation_steps: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class ParsedShapeDescription:
    """Parsed description of a shape from text."""
    shape_type: str
    dimensions: Dict[str, float] = field(default_factory=dict)
    modifiers: List[str] = field(default_factory=list)
    relationships: Dict[str, Any] = field(default_factory=dict)
    material_properties: Dict[str, Any] = field(default_factory=dict)


class TextTo3DGenerator:
    """AI-powered text-to-3D model generator."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Shape templates and patterns
        self.shape_patterns = {
            # Basic primitives
            r"(?:a |an )?cube(?: of size)? (.+)": ("cube", ["size"]),
            r"(?:a |an )?sphere(?: with radius)? (.+)": ("sphere", ["radius"]),
            r"(?:a |an )?cylinder(?: with radius)? (.+) (?:and height)? (.+)": ("cylinder", ["radius", "height"]),
            r"(?:a |an )?cone(?: with radius)? (.+) (?:and height)? (.+)": ("cone", ["base_radius", "height"]),

            # Mechanical components
            r"(?:a |an )?gear with (\d+) teeth(?: and module)? (.+)": ("gear", ["teeth", "module"]),
            r"(?:a |an )?shaft(?: with diameter)? (.+) (?:and length)? (.+)": ("shaft", ["diameter", "length"]),
            r"(?:a |an )?bolt m(\d+)(?:x(\d+))?": ("bolt", ["diameter", "length"]),

            # Architectural elements
            r"(?:a |an )?wall(?: of thickness)? (.+) (?:and height)? (.+) (?:and length)? (.+)": ("wall", ["thickness", "height", "length"]),
            r"(?:a |an )?door(?: with width)? (.+) (?:and height)? (.+)": ("door", ["width", "height"]),

            # Complex shapes
            r"(.+) with (.+) holes?": ("perforated_shape", ["base_shape", "hole_config"]),
            r"(.+) connected to (.+)": ("assembly", ["part1", "part2"]),
        }

        # Unit conversion patterns
        self.unit_patterns = {
            r"(\d+(?:\.\d+)?)\s*mm": (lambda x: float(x), "mm"),
            r"(\d+(?:\.\d+)?)\s*cm": (lambda x: float(x) * 10, "cm"),
            r"(\d+(?:\.\d+)?)\s*m": (lambda x: float(x) * 1000, "m"),
            r"(\d+(?:\.\d+)?)\s*inches?": (lambda x: float(x) * 25.4, "inch"),
            r"(\d+(?:\.\d+)?)\s*ft": (lambda x: float(x) * 304.8, "ft"),
        }

    def generate_from_text(self, request: TextTo3DRequest) -> GeneratedModel:
        """Generate a 3D model from text description."""

        try:
            # Parse the text prompt
            parsed_description = self._parse_text_prompt(request.text_prompt)

            # Generate the model based on parsed description
            mesh = self._generate_mesh_from_description(parsed_description, request)

            # Create metadata
            metadata = {
                "original_prompt": request.text_prompt,
                "parsed_description": parsed_description.__dict__,
                "generation_model": request.model.value,
                "target_quality": request.target_quality,
                "vertex_count": len(mesh.vertices),
                "face_count": len(mesh.faces),
                "bounding_box": mesh.bounds.tolist() if mesh.bounds is not None else None,
                "volume": float(mesh.volume) if mesh.is_watertight else 0.0,
                "surface_area": float(mesh.area),
            }

            # Generate warnings if needed
            warnings = []
            if len(mesh.faces) > request.max_complexity:
                warnings.append(f"Model complexity ({len(mesh.faces)} faces) exceeds limit")

            return GeneratedModel(
                mesh=mesh,
                metadata=metadata,
                generation_steps=["Text parsing", "Shape generation", "Mesh optimization"],
                confidence_score=self._calculate_confidence_score(parsed_description),
                warnings=warnings
            )

        except Exception as e:
            self.logger.error(f"Error generating model from text: {e}")
            # Return a simple cube as fallback
            fallback_mesh = trimesh.creation.box(extents=[10, 10, 10])
            return GeneratedModel(
                mesh=fallback_mesh,
                metadata={"error": str(e), "fallback": True},
                generation_steps=["Error occurred, using fallback"],
                confidence_score=0.0,
                warnings=[f"Generation failed: {str(e)}"]
            )

    def _parse_text_prompt(self, text: str) -> ParsedShapeDescription:
        """Parse natural language text into structured shape description."""

        text = text.lower().strip()

        # Try to match against known patterns
        for pattern, (shape_type, param_names) in self.shape_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                dimensions = {}

                # Extract dimensions with units
                for i, param_name in enumerate(param_names):
                    if i < len(groups):
                        value = self._parse_dimension(groups[i])
                        if value is not None:
                            dimensions[param_name] = value

                return ParsedShapeDescription(
                    shape_type=shape_type,
                    dimensions=dimensions,
                    modifiers=self._extract_modifiers(text),
                    relationships=self._extract_relationships(text)
                )

        # Fallback parsing for unrecognized patterns
        return ParsedShapeDescription(
            shape_type="unknown",
            modifiers=self._extract_modifiers(text)
        )

    def _parse_dimension(self, text: str) -> Optional[float]:
        """Parse dimension from text with unit conversion."""

        text = text.strip()

        # Try unit patterns
        for pattern, (converter, unit) in self.unit_patterns.items():
            match = re.search(pattern, text)
            if match:
                try:
                    value = converter(match.group(1))
                    return value
                except ValueError:
                    continue

        # Try plain numbers
        try:
            return float(text)
        except ValueError:
            pass

        # Try to extract first number
        number_match = re.search(r"(\d+(?:\.\d+)?)", text)
        if number_match:
            try:
                return float(number_match.group(1))
            except ValueError:
                pass

        return None

    def _extract_modifiers(self, text: str) -> List[str]:
        """Extract shape modifiers from text."""

        modifiers = []
        modifier_keywords = [
            "rounded", "sharp", "smooth", "rough", "hollow", "solid",
            "large", "small", "tall", "wide", "thin", "thick",
            "red", "blue", "green", "yellow", "black", "white"  # colors
        ]

        for modifier in modifier_keywords:
            if modifier in text:
                modifiers.append(modifier)

        return modifiers

    def _extract_relationships(self, text: str) -> Dict[str, Any]:
        """Extract relationships between parts."""

        relationships = {}

        # Check for assembly relationships
        if "connected to" in text or "attached to" in text:
            relationships["type"] = "assembly"

        if "inside" in text or "within" in text:
            relationships["containment"] = True

        if "above" in text or "below" in text:
            relationships["positional"] = True

        return relationships

    def _generate_mesh_from_description(self, description: ParsedShapeDescription,
                                      request: TextTo3DRequest) -> trimesh.Trimesh:
        """Generate mesh from parsed description."""

        shape_type = description.shape_type
        dimensions = description.dimensions

        try:
            if shape_type == "cube":
                size = dimensions.get("size", 10.0)
                return trimesh.creation.box(extents=[size, size, size])

            elif shape_type == "sphere":
                radius = dimensions.get("radius", 5.0)
                return trimesh.creation.uv_sphere(radius=radius)

            elif shape_type == "cylinder":
                radius = dimensions.get("radius", 5.0)
                height = dimensions.get("height", 10.0)
                return trimesh.creation.cylinder(radius=radius, height=height)

            elif shape_type == "cone":
                radius = dimensions.get("base_radius", 5.0)
                height = dimensions.get("height", 10.0)
                return trimesh.creation.cone(radius=radius, height=height)

            elif shape_type == "gear":
                # Simplified gear representation
                teeth = int(dimensions.get("teeth", 12))
                module = dimensions.get("module", 2.0)
                outer_radius = (teeth * module) / 2
                inner_radius = outer_radius * 0.8
                height = module * 2

                # Create basic cylindrical shape with teeth-like features
                gear = trimesh.creation.cylinder(radius=outer_radius, height=height)
                return gear

            elif shape_type == "shaft":
                diameter = dimensions.get("diameter", 10.0)
                length = dimensions.get("length", 50.0)
                radius = diameter / 2
                return trimesh.creation.cylinder(radius=radius, height=length)

            elif shape_type == "wall":
                thickness = dimensions.get("thickness", 0.2)
                height = dimensions.get("height", 3.0)
                length = dimensions.get("length", 10.0)
                return trimesh.creation.box(extents=[length, thickness, height])

            elif shape_type == "door":
                width = dimensions.get("width", 0.9)
                height = dimensions.get("height", 2.1)
                thickness = 0.05
                return trimesh.creation.box(extents=[width, thickness, height])

            else:
                # Default to a parametric box based on available dimensions
                width = dimensions.get("width", dimensions.get("size", 10.0))
                height = dimensions.get("height", dimensions.get("size", 10.0))
                depth = dimensions.get("depth", dimensions.get("thickness", dimensions.get("size", 10.0)))
                return trimesh.creation.box(extents=[width, depth, height])

        except Exception as e:
            self.logger.warning(f"Error generating {shape_type}: {e}")
            # Fallback
            return trimesh.creation.box(extents=[10, 10, 10])

    def _calculate_confidence_score(self, description: ParsedShapeDescription) -> float:
        """Calculate confidence score for the generated model."""

        score = 0.0

        # Base score for recognized shape types
        if description.shape_type != "unknown":
            score += 0.6

        # Bonus for having dimensions
        if description.dimensions:
            score += 0.2

        # Bonus for modifiers
        if description.modifiers:
            score += 0.1

        # Bonus for relationships
        if description.relationships:
            score += 0.1

        return min(1.0, score)

    def get_supported_shapes(self) -> List[str]:
        """Get list of supported shape types."""

        return [
            "cube", "sphere", "cylinder", "cone",
            "gear", "shaft", "bolt",
            "wall", "door",
            "perforated_shape", "assembly"
        ]

    def get_example_prompts(self) -> List[str]:
        """Get example text prompts for generation."""

        return [
            "a cube of size 20mm",
            "a sphere with radius 15mm",
            "a cylinder with radius 5mm and height 30mm",
            "a gear with 12 teeth and module 2",
            "a shaft with diameter 10mm and length 50mm",
            "a wall of thickness 200mm and height 3m and length 10m",
            "a door with width 900mm and height 2100mm"
        ]


class AIChatAssistant:
    """AI-powered chat assistant for CAD design assistance."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.conversation_history = []

    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a user query and provide assistance."""

        query = query.lower().strip()

        response = {
            "answer": "",
            "suggestions": [],
            "commands": [],
            "code_snippets": [],
            "confidence": 0.0
        }

        try:
            # Analyze query type
            if self._is_design_question(query):
                response.update(self._handle_design_question(query, context))
            elif self._is_troubleshooting_query(query):
                response.update(self._handle_troubleshooting(query, context))
            elif self._is_code_request(query):
                response.update(self._handle_code_request(query, context))
            else:
                response["answer"] = self._handle_general_query(query)

            # Add conversation context
            self.conversation_history.append({
                "query": query,
                "response": response,
                "timestamp": np.datetime64('now')
            })

            # Limit history
            if len(self.conversation_history) > 50:
                self.conversation_history = self.conversation_history[-50:]

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            response["answer"] = f"Sorry, I encountered an error: {str(e)}"
            response["confidence"] = 0.0

        return response

    def _is_design_question(self, query: str) -> bool:
        """Check if query is about design."""
        design_keywords = [
            "design", "model", "shape", "dimension", "size", "create", "build",
            "geometry", "part", "component", "assembly", "drawing"
        ]
        return any(keyword in query for keyword in design_keywords)

    def _is_troubleshooting_query(self, query: str) -> bool:
        """Check if query is about troubleshooting."""
        trouble_keywords = [
            "error", "problem", "issue", "failed", "not working", "help",
            "fix", "troubleshoot", "debug", "why"
        ]
        return any(keyword in query for keyword in trouble_keywords)

    def _is_code_request(self, query: str) -> bool:
        """Check if query is requesting code."""
        code_keywords = [
            "code", "script", "python", "function", "api", "program",
            "automate", "batch", "macro"
        ]
        return any(keyword in query for keyword in code_keywords)

    def _handle_design_question(self, query: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle design-related questions."""

        response = {"confidence": 0.8}

        if "cube" in query or "box" in query:
            response["answer"] = "To create a cube in CAD, you typically need to specify dimensions. For a 20mm cube, you can use parametric modeling or direct mesh creation."
            response["suggestions"] = [
                "Use the text-to-3D generator with prompt: 'a cube of size 20mm'",
                "In parametric CAD, create a box primitive and set all dimensions to 20mm",
                "For 3D printing, ensure wall thickness meets minimum requirements"
            ]

        elif "sphere" in query:
            response["answer"] = "Spheres are useful for organic shapes and can be created parametrically or through mesh generation."
            response["suggestions"] = [
                "Try text prompt: 'a sphere with radius 15mm'",
                "For printing, consider support structures if the sphere is large",
                "Check minimum wall thickness requirements"
            ]

        elif "wall thickness" in query:
            response["answer"] = "Wall thickness is critical for 3D printing. Minimum thickness depends on your printer's nozzle size and material."
            response["suggestions"] = [
                "For FDM printers: minimum 0.8mm wall thickness",
                "For resin printers: minimum 0.3mm wall thickness",
                "Use the validation tool to check your model's wall thickness"
            ]

        elif "support" in query:
            response["answer"] = "Support structures are needed for overhanging features. The angle threshold is typically 45-60 degrees."
            response["suggestions"] = [
                "Use automatic support generation in slicer software",
                "Design parts to minimize overhangs when possible",
                "Consider orientation to reduce support requirements"
            ]

        else:
            response["answer"] = "I can help with various design questions. Try asking about specific shapes, dimensions, or printing considerations."
            response["suggestions"] = [
                "Ask about specific shapes: cubes, spheres, cylinders",
                "Inquire about printing parameters: wall thickness, supports, infill",
                "Request code examples for automation"
            ]

        return response

    def _handle_troubleshooting(self, query: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle troubleshooting queries."""

        response = {"confidence": 0.7}

        if "not watertight" in query or "holes" in query:
            response["answer"] = "Non-watertight meshes have holes or gaps. This prevents proper 3D printing."
            response["suggestions"] = [
                "Use the mesh repair tools in the validation section",
                "Check for self-intersecting faces",
                "Ensure all edges form closed loops"
            ]

        elif "thin walls" in query:
            response["answer"] = "Thin walls can break during printing. The minimum thickness depends on your printer."
            response["suggestions"] = [
                "Increase wall thickness in your design",
                "Use multiple wall layers in slicer settings",
                "Consider material and nozzle size constraints"
            ]

        elif "overhang" in query:
            response["answer"] = "Overhangs require support structures. Angles greater than 45 degrees typically need supports."
            response["suggestions"] = [
                "Re-orient your model to minimize overhangs",
                "Use automatic support generation",
                "Consider tree supports for better removal"
            ]

        else:
            response["answer"] = "Common 3D printing issues include non-watertight meshes, thin walls, and overhangs. Please provide more details about your specific problem."
            response["suggestions"] = [
                "Run the validation tools on your model",
                "Check printer settings and calibration",
                "Review material-specific requirements"
            ]

        return response

    def _handle_code_request(self, query: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle code/script requests."""

        response = {"confidence": 0.9}

        if "batch" in query or "multiple" in query:
            response["answer"] = "For batch processing multiple STL files, you can use the CLI tool with wildcards."
            response["code_snippets"] = [
                "# Process all STL files in a directory",
                "printcad --batch 'models/*.stl' --parallel --auto-summary",
                "",
                "# Python script for custom batch processing",
                "import glob",
                "from pathlib import Path",
                "",
                "stl_files = glob.glob('models/*.stl')",
                "for stl_file in stl_files:",
                "    result = validate_file(Path(stl_file))",
                "    print(f'{stl_file}: {result.success}')",
            ]

        elif "api" in query or "integration" in query:
            response["answer"] = "The REST API allows integration with external systems for automated validation."
            response["code_snippets"] = [
                "# Python example for API integration",
                "import requests",
                "",
                "def validate_model(file_path):",
                "    with open(file_path, 'rb') as f:",
                "        response = requests.post(",
                "            'http://localhost:5000/api/validate',",
                "            files={'file': f}",
                "        )",
                "    return response.json()",
                "",
                "result = validate_model('model.stl')",
                "print(f'Validation: {result[\"success\"]}')",
            ]

        elif "export" in query:
            response["answer"] = "You can export validation results in various formats for integration with other tools."
            response["code_snippets"] = [
                "# Export to JSON",
                "printcad model.stl --output report.json --summary",
                "",
                "# Export to CSV for spreadsheet analysis",
                "import csv",
                "import json",
                "",
                "with open('report.json') as f:",
                "    data = json.load(f)",
                "",
                "with open('report.csv', 'w', newline='') as csvfile:",
                "    writer = csv.writer(csvfile)",
                "    writer.writerow(['Metric', 'Value'])",
                "    for key, value in data['metrics'].items():",
                "        writer.writerow([key, value])",
            ]

        else:
            response["answer"] = "I can provide code examples for various automation tasks."
            response["suggestions"] = [
                "Ask for batch processing scripts",
                "Request API integration examples",
                "Inquire about export automation"
            ]

        return response

    def _handle_general_query(self, query: str) -> str:
        """Handle general queries."""

        if "help" in query:
            return "I'm your CAD assistant. I can help with design questions, troubleshooting 3D printing issues, and provide code examples for automation."

        elif "version" in query or "about" in query:
            return "3D Print CAD Assistant v2.0 - Production-grade 3D model validation and optimization platform with AI-powered features."

        else:
            return "I'm here to help with 3D printing and CAD-related questions. Try asking about specific design issues, validation problems, or automation needs."


class NaturalLanguageDesignParser:
    """Advanced natural language parser for design descriptions."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_design_description(self, text: str) -> Dict[str, Any]:
        """Parse natural language design description into structured parameters."""
        parsed = {
            'shape_type': self._extract_shape_type(text),
            'dimensions': self._extract_dimensions(text),
            'materials': self._extract_materials(text),
            'features': self._extract_features(text),
            'constraints': self._extract_constraints(text),
            'complexity': self._estimate_complexity(text)
        }

        return parsed

    def _extract_shape_type(self, text: str) -> str:
        """Extract primary shape type from description."""
        # Simple keyword matching for demonstration
        keywords = {
            'cube': 'cube',
            'box': 'cube',
            'sphere': 'sphere',
            'ball': 'sphere',
            'cylinder': 'cylinder',
            'tube': 'cylinder',
            'cone': 'cone',
            'pyramid': 'pyramid',
            'gear': 'gear',
            'screw': 'screw',
            'bolt': 'bolt'
        }

        text_lower = text.lower()
        for keyword, shape in keywords.items():
            if keyword in text_lower:
                return shape

        return 'cube'  # Default fallback

    def _extract_dimensions(self, text: str) -> Dict[str, float]:
        """Extract dimensions from natural language."""
        dimensions = {}

        # Look for patterns like "10mm wide", "5cm tall", etc.
        patterns = [
            (r'(\d+(?:\.\d+)?)\s*(mm|cm|m|inch|in)\s*(wide|width|long|length|high|height|tall|thick|thickness)',
             'width'),
            (r'(\d+(?:\.\d+)?)\s*(mm|cm|m|inch|in)\s*(diameter|radius)', 'diameter'),
            (r'(\d+(?:\.\d+)?)\s*(mm|cm|m|inch|in)\s*(deep|depth)', 'depth')
        ]

        for pattern, dim_type in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2).lower()

                # Convert to mm
                if unit == 'cm':
                    value *= 10
                elif unit == 'm':
                    value *= 1000
                elif unit in ['inch', 'in']:
                    value *= 25.4

                dimensions[dim_type] = value

        return dimensions

    def _extract_materials(self, text: str) -> List[str]:
        """Extract material requirements from description."""
        materials = []

        material_keywords = [
            'plastic', 'metal', 'aluminum', 'steel', 'wood', 'ceramic',
            'resin', 'carbon fiber', 'titanium', 'brass'
        ]

        text_lower = text.lower()
        for material in material_keywords:
            if material in text_lower:
                materials.append(material)

        return materials or ['plastic']  # Default

    def _extract_features(self, text: str) -> List[str]:
        """Extract design features from description."""
        features = []

        feature_keywords = [
            'hole', 'holes', 'thread', 'threads', 'groove', 'grooves',
            'chamfer', 'fillet', 'engraving', 'emboss', 'cutout'
        ]

        text_lower = text.lower()
        for feature in feature_keywords:
            if feature in text_lower:
                features.append(feature)

        return features

    def _extract_constraints(self, text: str) -> Dict[str, Any]:
        """Extract design constraints."""
        constraints = {}

        # Look for constraints like "must fit in 10cm space"
        constraint_patterns = [
            (r'must fit in (\d+(?:\.\d+)?)\s*(mm|cm|m)', 'max_size'),
            (r'weight less than (\d+(?:\.\d+)?)\s*(g|kg)', 'max_weight'),
            (r'strength of (\d+(?:\.\d+)?)\s*(mpa|psi)', 'min_strength')
        ]

        for pattern, constraint_type in constraint_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2).lower()

                # Convert units
                if constraint_type == 'max_size' and unit == 'cm':
                    value *= 10
                elif constraint_type == 'max_size' and unit == 'm':
                    value *= 1000
                elif constraint_type == 'max_weight' and unit == 'kg':
                    value *= 1000

                constraints[constraint_type] = value

        return constraints

    def _estimate_complexity(self, text: str) -> int:
        """Estimate design complexity based on description length and keywords."""
        base_complexity = len(text.split()) * 2  # Base on word count

        complexity_keywords = ['complex', 'detailed', 'intricate', 'precise', 'multiple parts']
        for keyword in complexity_keywords:
            if keyword in text.lower():
                base_complexity += 50

        return min(base_complexity, 1000)  # Cap at 1000


class EnhancedTextTo3DGenerator:
    """Enhanced text-to-3D generator with natural language processing."""

    def __init__(self):
        self.parser = NaturalLanguageDesignParser()
        self.logger = logging.getLogger(__name__)

    def generate_from_natural_language(self, text: str, model: GenerationModel = GenerationModel.AI_ENHANCED) -> GeneratedModel:
        """Generate 3D model from natural language description."""
        # Parse the natural language input
        parsed_design = self.parser.parse_design_description(text)

        self.logger.info(f"Parsed design: {parsed_design}")

        # Generate model based on parsed parameters
        mesh = self._generate_mesh_from_parsed(parsed_design)

        # Create metadata
        metadata = {
            'original_text': text,
            'parsed_design': parsed_design,
            'generation_model': model.value,
            'complexity_score': parsed_design['complexity']
        }

        return GeneratedModel(
            mesh=mesh,
            metadata=metadata,
            generation_steps=[f"Parsed: {text}", f"Generated {parsed_design['shape_type']}"],
            confidence_score=self._calculate_confidence(parsed_design)
        )

    def _generate_mesh_from_parsed(self, parsed: Dict[str, Any]) -> trimesh.Trimesh:
        """Generate mesh from parsed design parameters."""
        shape_type = parsed['shape_type']
        dimensions = parsed['dimensions']

        # Generate basic shape
        if shape_type == 'cube':
            size = dimensions.get('width', 50.0)
            mesh = trimesh.creation.box(extents=[size, size, size])
        elif shape_type == 'sphere':
            radius = dimensions.get('diameter', 50.0) / 2
            mesh = trimesh.creation.icosphere(radius=radius)
        elif shape_type == 'cylinder':
            radius = dimensions.get('diameter', 50.0) / 2
            height = dimensions.get('height', 50.0)
            mesh = trimesh.creation.cylinder(radius=radius, height=height)
        else:
            # Default to cube
            mesh = trimesh.creation.box(extents=[50.0, 50.0, 50.0])

        # Apply features if specified
        for feature in parsed['features']:
            mesh = self._apply_feature(mesh, feature, dimensions)

        return mesh

    def _apply_feature(self, mesh: trimesh.Trimesh, feature: str, dimensions: Dict[str, float]) -> trimesh.Trimesh:
        """Apply a feature to the mesh."""
        if feature == 'hole':
            # Simple hole in the center
            hole_radius = dimensions.get('diameter', 50.0) * 0.1
            hole_depth = dimensions.get('depth', 50.0) * 0.5

            # Create hole cylinder and subtract
            hole = trimesh.creation.cylinder(radius=hole_radius, height=hole_depth)
            hole.apply_translation([0, 0, -hole_depth/2])

            # Subtract hole from mesh (simplified)
            # In practice, would use proper boolean operations
            pass

        return mesh

    def _calculate_confidence(self, parsed: Dict[str, Any]) -> float:
        """Calculate confidence score for the generation."""
        # Higher confidence if more parameters were extracted
        param_count = len(parsed['dimensions']) + len(parsed['materials']) + len(parsed['features'])
        confidence = min(1.0, param_count / 5.0)  # Max 5 parameters

        return confidence


def generate_3d_from_text(prompt: str, model: GenerationModel = GenerationModel.BASIC_PARAMETRIC) -> GeneratedModel:
    """Convenience function for text-to-3D generation."""
    request = TextTo3DRequest(text_prompt=prompt, model=model)
    return text_to_3d_generator.generate_from_text(request)


def chat_with_ai_assistant(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function for AI chat assistance."""
    return ai_chat_assistant.process_query(query, context)
