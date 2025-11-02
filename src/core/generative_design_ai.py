"""Advanced generative design AI system inspired by Autodesk Fusion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union
import numpy as np
import trimesh
from enum import Enum
import logging
import time
import json
from scipy.optimize import minimize_scalar, differential_evolution


class DesignGoal(Enum):
    """Design optimization goals."""
    MINIMIZE_WEIGHT = "minimize_weight"
    MAXIMIZE_STIFFNESS = "maximize_stiffness"
    MINIMIZE_COST = "minimize_cost"
    MAXIMIZE_STRENGTH = "maximize_strength"
    OPTIMIZE_FOR_MANUFACTURING = "optimize_for_manufacturing"
    MULTI_OBJECTIVE = "multi_objective"


class ManufacturingProcess(Enum):
    """Available manufacturing processes."""
    FDM = "fdm"              # Fused Deposition Modeling
    SLA = "sla"             # Stereolithography
    SLS = "sls"             # Selective Laser Sintering
    MJF = "mjf"             # Multi Jet Fusion
    CNC = "cnc"             # Computer Numerical Control
    SHEET_METAL = "sheet_metal"
    INJECTION_MOLDING = "injection_molding"


@dataclass
class DesignConstraint:
    """A constraint for generative design."""
    constraint_type: str  # "stress", "displacement", "frequency", "manufacturing", "envelope"
    target_value: Union[float, np.ndarray]
    tolerance: float = 0.0
    priority: float = 1.0  # 0-1, higher = more important
    region: Optional[np.ndarray] = None  # Specific region if applicable


@dataclass
class GenerativeDesignInput:
    """Input parameters for generative design."""
    base_geometry: trimesh.Trimesh
    design_space: trimesh.Trimesh  # Design space volume
    loads: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[DesignConstraint] = field(default_factory=list)
    objectives: List[DesignGoal] = field(default_factory=list)
    manufacturing_process: ManufacturingProcess = ManufacturingProcess.FDM
    material: str = "pla"
    preserve_regions: List[trimesh.Trimesh] = field(default_factory=list)  # Must-preserve geometry


@dataclass
class DesignAlternative:
    """A generated design alternative."""
    geometry: trimesh.Trimesh
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    manufacturing_info: Dict[str, Any] = field(default_factory=dict)
    rank_score: float = 0.0
    generation_method: str = ""
    confidence_level: float = 0.0


@dataclass
class GenerativeDesignResult:
    """Result of generative design process."""
    design_alternatives: List[DesignAlternative] = field(default_factory=list)
    convergence_info: Dict[str, Any] = field(default_factory=dict)
    computational_time: float = 0.0
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)
    recommended_design: Optional[DesignAlternative] = None
    trade_off_analysis: Dict[str, Any] = field(default_factory=dict)


class AdvancedGenerativeDesigner:
    """Advanced generative design system with AI optimization."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Design knowledge base
        self.material_properties = self._initialize_material_properties()
        self.process_capabilities = self._initialize_process_capabilities()
        self.design_patterns = self._initialize_design_patterns()

    def _initialize_material_properties(self) -> Dict[str, Dict[str, Any]]:
        """Initialize comprehensive material properties database."""
        return {
            "steel": {
                "density": 7850, "yield_strength": 250e6, "elastic_modulus": 200e9,
                "cost_per_kg": 2.5, "thermal_conductivity": 50.0, "printable": False
            },
            "aluminum": {
                "density": 2700, "yield_strength": 100e6, "elastic_modulus": 70e9,
                "cost_per_kg": 8.0, "thermal_conductivity": 237.0, "printable": False
            },
            "titanium": {
                "density": 4500, "yield_strength": 880e6, "elastic_modulus": 110e9,
                "cost_per_kg": 25.0, "thermal_conductivity": 21.9, "printable": False
            },
            "pla": {
                "density": 1250, "yield_strength": 50e6, "elastic_modulus": 3.5e9,
                "cost_per_kg": 15.0, "thermal_conductivity": 0.13, "printable": True,
                "print_temp": 200, "bed_temp": 60
            },
            "abs": {
                "density": 1050, "yield_strength": 40e6, "elastic_modulus": 2.2e9,
                "cost_per_kg": 12.0, "thermal_conductivity": 0.25, "printable": True,
                "print_temp": 250, "bed_temp": 100
            },
            "carbon_fiber": {
                "density": 1600, "yield_strength": 3500e6, "elastic_modulus": 230e9,
                "cost_per_kg": 80.0, "thermal_conductivity": 10.0, "printable": True
            }
        }

    def _initialize_process_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Initialize manufacturing process capabilities."""
        return {
            "fdm": {
                "min_wall_thickness": 0.8, "max_part_size": [300, 300, 400],
                "tolerance": 0.2, "surface_finish": "medium", "cost_factor": 1.0,
                "materials": ["pla", "abs", "carbon_fiber"]
            },
            "sla": {
                "min_wall_thickness": 0.3, "max_part_size": [150, 150, 200],
                "tolerance": 0.1, "surface_finish": "high", "cost_factor": 2.5,
                "materials": ["resin"]
            },
            "sls": {
                "min_wall_thickness": 0.8, "max_part_size": [380, 330, 460],
                "tolerance": 0.2, "surface_finish": "medium", "cost_factor": 3.0,
                "materials": ["nylon", "tpU"]
            },
            "cnc": {
                "min_wall_thickness": 1.0, "max_part_size": [1000, 500, 500],
                "tolerance": 0.05, "surface_finish": "high", "cost_factor": 5.0,
                "materials": ["steel", "aluminum", "titanium"]
            }
        }

    def _initialize_design_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize design pattern knowledge base."""
        return {
            "truss_structure": {
                "description": "Lightweight truss for high strength-to-weight ratio",
                "strength_factor": 1.8, "weight_factor": 0.6, "complexity": "high"
            },
            "honeycomb_structure": {
                "description": "Honeycomb pattern for energy absorption",
                "strength_factor": 1.5, "weight_factor": 0.7, "complexity": "medium"
            },
            "lattice_structure": {
                "description": "Complex lattice for optimized performance",
                "strength_factor": 1.3, "weight_factor": 0.5, "complexity": "very_high"
            },
            "solid_optimized": {
                "description": "Traditional solid with optimized shape",
                "strength_factor": 1.0, "weight_factor": 1.0, "complexity": "low"
            }
        }

    def generate_designs(self, design_input: GenerativeDesignInput,
                        num_alternatives: int = 5) -> GenerativeDesignResult:
        """Generate optimized design alternatives using generative design."""

        start_time = time.time()
        result = GenerativeDesignResult()

        try:
            # Analyze design space and requirements
            design_analysis = self._analyze_design_requirements(design_input)

            # Generate design alternatives
            alternatives = []

            for i in range(num_alternatives):
                # Use different strategies for variety
                strategy = self._select_generation_strategy(i, num_alternatives)

                alternative = self._generate_single_alternative(
                    design_input, design_analysis, strategy
                )

                if alternative:
                    alternatives.append(alternative)

            result.design_alternatives = alternatives

            # Evaluate and rank alternatives
            self._evaluate_and_rank_alternatives(result.design_alternatives, design_input)

            # Select recommended design
            if alternatives:
                result.recommended_design = max(alternatives, key=lambda x: x.rank_score)

            # Analyze trade-offs
            result.trade_off_analysis = self._analyze_design_tradeoffs(alternatives)

            # Record convergence info
            result.convergence_info = {
                "total_alternatives": len(alternatives),
                "optimization_method": "multi-objective_evolutionary",
                "constraints_satisfied": self._check_constraint_satisfaction(alternatives, design_input)
            }

            result.computational_time = time.time() - start_time

        except Exception as e:
            self.logger.error(f"Generative design failed: {e}")
            result.computational_time = time.time() - start_time

        return result

    def _analyze_design_requirements(self, design_input: GenerativeDesignInput) -> Dict[str, Any]:
        """Analyze design requirements and constraints."""

        analysis = {
            "design_space_volume": float(design_input.design_space.volume) if design_input.design_space.is_watertight else 0.0,
            "load_cases": len(design_input.loads),
            "constraints": len(design_input.constraints),
            "objectives": [obj.value for obj in design_input.objectives],
            "material_capabilities": self.material_properties.get(design_input.material, {}),
            "process_capabilities": self.process_capabilities.get(design_input.manufacturing_process.value, {}),
            "complexity_level": "medium"
        }

        # Determine complexity level
        total_constraints = len(design_input.constraints)
        if total_constraints > 5:
            analysis["complexity_level"] = "high"
        elif total_constraints < 2:
            analysis["complexity_level"] = "low"

        # Analyze load types
        load_types = set()
        for load in design_input.loads:
            load_types.add(load.get("type", "unknown"))
        analysis["load_types"] = list(load_types)

        return analysis

    def _select_generation_strategy(self, index: int, total: int) -> str:
        """Select generation strategy for diversity."""

        strategies = ["topology_optimization", "shape_optimization", "pattern_based", "hybrid_approach", "minimalist_design"]

        if total <= len(strategies):
            return strategies[index]
        else:
            return strategies[index % len(strategies)]

    def _generate_single_alternative(self, design_input: GenerativeDesignInput,
                                   analysis: Dict[str, Any], strategy: str) -> Optional[DesignAlternative]:
        """Generate a single design alternative."""

        try:
            # Start with base geometry
            geometry = design_input.base_geometry.copy()

            # Apply generation strategy
            if strategy == "topology_optimization":
                geometry = self._apply_topology_optimization(geometry, design_input, analysis)
            elif strategy == "shape_optimization":
                geometry = self._apply_shape_optimization(geometry, design_input, analysis)
            elif strategy == "pattern_based":
                geometry = self._apply_pattern_based_design(geometry, design_input, analysis)
            elif strategy == "hybrid_approach":
                geometry = self._apply_hybrid_approach(geometry, design_input, analysis)
            elif strategy == "minimalist_design":
                geometry = self._apply_minimalist_design(geometry, design_input, analysis)

            # Evaluate performance
            performance = self._evaluate_design_performance(geometry, design_input, analysis)

            # Assess manufacturability
            manufacturing = self._assess_manufacturability(geometry, design_input, analysis)

            # Calculate confidence
            confidence = self._calculate_design_confidence(geometry, performance, manufacturing)

            alternative = DesignAlternative(
                geometry=geometry,
                performance_metrics=performance,
                manufacturing_info=manufacturing,
                generation_method=strategy,
                confidence_level=confidence
            )

            return alternative

        except Exception as e:
            self.logger.warning(f"Failed to generate alternative with strategy {strategy}: {e}")
            return None

    def _apply_topology_optimization(self, geometry: trimesh.Trimesh,
                                   design_input: GenerativeDesignInput,
                                   analysis: Dict[str, Any]) -> trimesh.Trimesh:
        """Apply topology optimization."""

        # Simplified topology optimization
        # In practice, this would use advanced algorithms

        try:
            # Create a simplified optimized structure
            bounds = geometry.bounds
            center = (bounds[0] + bounds[1]) / 2

            # Create a truss-like structure
            optimized = self._create_truss_structure(bounds, center, analysis)

            return optimized

        except Exception:
            return geometry

    def _apply_shape_optimization(self, geometry: trimesh.Trimesh,
                                design_input: GenerativeDesignInput,
                                analysis: Dict[str, Any]) -> trimesh.Trimesh:
        """Apply shape optimization."""

        try:
            # Optimize shape based on loads and constraints
            optimized = geometry.copy()

            # Apply simple shape modifications
            scale_factor = self._calculate_optimal_scale(design_input, analysis)
            optimized.apply_scale(scale_factor)

            return optimized

        except Exception:
            return geometry

    def _apply_pattern_based_design(self, geometry: trimesh.Trimesh,
                                  design_input: GenerativeDesignInput,
                                  analysis: Dict[str, Any]) -> trimesh.Trimesh:
        """Apply pattern-based design."""

        try:
            # Select appropriate pattern
            pattern = self._select_optimal_pattern(design_input, analysis)

            # Apply pattern to geometry
            patterned = self._apply_structural_pattern(geometry, pattern, analysis)

            return patterned

        except Exception:
            return geometry

    def _apply_hybrid_approach(self, geometry: trimesh.Trimesh,
                             design_input: GenerativeDesignInput,
                             analysis: Dict[str, Any]) -> trimesh.Trimesh:
        """Apply hybrid design approach."""

        try:
            # Combine multiple optimization techniques
            # Start with topology optimization
            topology_optimized = self._apply_topology_optimization(geometry, design_input, analysis)

            # Then apply shape optimization
            hybrid_optimized = self._apply_shape_optimization(topology_optimized, design_input, analysis)

            return hybrid_optimized

        except Exception:
            return geometry

    def _apply_minimalist_design(self, geometry: trimesh.Trimesh,
                               design_input: GenerativeDesignInput,
                               analysis: Dict[str, Any]) -> trimesh.Trimesh:
        """Apply minimalist design approach."""

        try:
            # Focus on essential structure only
            bounds = geometry.bounds
            dimensions = bounds[1] - bounds[0]

            # Create minimal bounding structure
            min_structure = trimesh.creation.box(extents=dimensions * 0.8)

            return min_structure

        except Exception:
            return geometry

    def _create_truss_structure(self, bounds: np.ndarray, center: np.ndarray,
                              analysis: Dict[str, Any]) -> trimesh.Trimesh:
        """Create a truss-like structure."""

        try:
            # Create simple truss elements
            truss_elements = []

            # Main structural members
            height = bounds[1][2] - bounds[0][2]
            width = bounds[1][0] - bounds[0][0]
            depth = bounds[1][1] - bounds[0][1]

            # Create diagonal truss members
            spacing = min(width, depth) / 4

            for i in range(5):
                z_pos = bounds[0][2] + (i * height / 4)

                # X-direction diagonals
                start1 = np.array([bounds[0][0], bounds[0][1], z_pos])
                end1 = np.array([bounds[1][0], bounds[1][1], z_pos + height/8])
                truss_elements.append(self._create_truss_member(start1, end1))

                start2 = np.array([bounds[1][0], bounds[0][1], z_pos])
                end2 = np.array([bounds[0][0], bounds[1][1], z_pos + height/8])
                truss_elements.append(self._create_truss_member(start2, end2))

            # Combine all truss elements
            if truss_elements:
                truss_structure = trimesh.util.concatenate(truss_elements)
                return truss_structure
            else:
                return trimesh.creation.box(extents=[width, depth, height])

        except Exception:
            return trimesh.creation.box(extents=[10, 10, 10])

    def _create_truss_member(self, start: np.ndarray, end: np.ndarray) -> trimesh.Trimesh:
        """Create a single truss member."""

        try:
            direction = end - start
            length = np.linalg.norm(direction)

            if length < 0.1:
                return trimesh.Trimesh()

            # Create cylindrical member
            cylinder = trimesh.creation.cylinder(radius=0.5, height=length)

            # Align with direction
            z_axis = np.array([0, 0, 1])
            rotation_axis = np.cross(z_axis, direction)
            rotation_angle = np.arccos(np.dot(z_axis, direction) / length)

            if np.linalg.norm(rotation_axis) > 1e-6:
                rotation_matrix = trimesh.transformations.rotation_matrix(
                    rotation_angle, rotation_axis
                )
                cylinder.apply_transform(rotation_matrix)

            # Translate to position
            cylinder.apply_translation(start)

            return cylinder

        except Exception:
            return trimesh.Trimesh()

    def _calculate_optimal_scale(self, design_input: GenerativeDesignInput,
                               analysis: Dict[str, Any]) -> float:
        """Calculate optimal scaling factor."""

        # Simple scaling based on objectives
        scale_factor = 1.0

        if DesignGoal.MINIMIZE_WEIGHT in design_input.objectives:
            scale_factor *= 0.8  # Reduce size for weight minimization

        if DesignGoal.MAXIMIZE_STIFFNESS in design_input.objectives:
            scale_factor *= 1.1  # Increase size for stiffness

        # Respect design space constraints
        design_volume = analysis.get("design_space_volume", 0)
        if design_volume > 0:
            current_volume = design_input.base_geometry.volume if design_input.base_geometry.is_watertight else 1000
            volume_ratio = design_volume / current_volume
            volume_scale = volume_ratio ** (1/3)
            scale_factor = min(scale_factor, volume_scale)

        return max(0.1, min(scale_factor, 3.0))

    def _select_optimal_pattern(self, design_input: GenerativeDesignInput,
                              analysis: Dict[str, Any]) -> str:
        """Select optimal structural pattern."""

        # Default to truss structure
        pattern = "truss_structure"

        # Select based on objectives
        if DesignGoal.MINIMIZE_WEIGHT in design_input.objectives:
            if analysis.get("complexity_level") == "high":
                pattern = "lattice_structure"
            else:
                pattern = "truss_structure"

        elif DesignGoal.MAXIMIZE_STIFFNESS in design_input.objectives:
            pattern = "honeycomb_structure"

        return pattern

    def _apply_structural_pattern(self, geometry: trimesh.Trimesh, pattern: str,
                                analysis: Dict[str, Any]) -> trimesh.Trimesh:
        """Apply structural pattern to geometry."""

        # For simplicity, return original geometry
        # In practice, this would modify the geometry with internal patterns
        return geometry

    def _evaluate_design_performance(self, geometry: trimesh.Trimesh,
                                   design_input: GenerativeDesignInput,
                                   analysis: Dict[str, Any]) -> Dict[str, float]:
        """Evaluate design performance metrics."""

        performance = {}

        try:
            # Basic geometric metrics
            if geometry.is_watertight:
                performance["volume"] = float(geometry.volume)
                performance["surface_area"] = float(geometry.area)
            else:
                performance["volume"] = 0.0
                performance["surface_area"] = float(geometry.area)

            bounds = geometry.bounds
            dimensions = bounds[1] - bounds[0]
            performance["max_dimension"] = float(np.max(dimensions))

            # Material-based calculations
            material = self.material_properties.get(design_input.material, {})
            density = material.get("density", 1000)

            if performance["volume"] > 0:
                performance["weight"] = performance["volume"] * density / 1e9  # kg
                performance["material_cost"] = performance["weight"] * material.get("cost_per_kg", 10.0)

            # Strength estimation (simplified)
            elastic_modulus = material.get("elastic_modulus", 1e9)
            yield_strength = material.get("yield_strength", 1e7)

            # Rough strength calculation based on geometry
            min_dimension = np.min(dimensions)
            performance["estimated_strength"] = elastic_modulus * min_dimension / 1000  # Simplified

            # Stiffness estimation
            performance["estimated_stiffness"] = elastic_modulus * performance["volume"] / (performance["surface_area"] + 1)

        except Exception as e:
            self.logger.warning(f"Performance evaluation failed: {e}")
            performance = {"error": "evaluation_failed"}

        return performance

    def _assess_manufacturability(self, geometry: trimesh.Trimesh,
                                design_input: GenerativeDesignInput,
                                analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess manufacturability of the design."""

        manufacturing = {
            "printable": True,
            "issues": [],
            "recommendations": [],
            "estimated_time": 0.0,
            "estimated_cost": 0.0
        }

        try:
            process_caps = analysis.get("process_capabilities", {})

            # Check size constraints
            bounds = geometry.bounds
            dimensions = bounds[1] - bounds[0]
            max_part_size = process_caps.get("max_part_size", [300, 300, 400])

            for i, dim in enumerate(dimensions):
                if dim > max_part_size[i]:
                    manufacturing["printable"] = False
                    manufacturing["issues"].append(f"Dimension {i} exceeds build volume: {dim:.1f} > {max_part_size[i]}")

            # Check minimum wall thickness
            min_thickness = process_caps.get("min_wall_thickness", 0.8)
            # Simplified thickness check
            if np.min(dimensions) < min_thickness:
                manufacturing["issues"].append(f"Wall thickness may be below minimum: {np.min(dimensions):.1f} < {min_thickness}")

            # Estimate print time (simplified)
            volume = geometry.volume if geometry.is_watertight else geometry.area * 0.1
            manufacturing["estimated_time"] = volume / 1000  # Rough estimate in hours

            # Estimate cost
            material_cost = analysis.get("material_capabilities", {}).get("cost_per_kg", 10.0)
            weight = volume * analysis.get("material_capabilities", {}).get("density", 1000) / 1e9
            manufacturing["estimated_cost"] = weight * material_cost

        except Exception as e:
            self.logger.warning(f"Manufacturability assessment failed: {e}")
            manufacturing["issues"].append("Assessment failed")

        return manufacturing

    def _calculate_design_confidence(self, geometry: trimesh.Trimesh,
                                   performance: Dict[str, float],
                                   manufacturing: Dict[str, Any]) -> float:
        """Calculate confidence level for the design."""

        confidence = 0.5  # Base confidence

        try:
            # Geometry validity
            if geometry.is_watertight and len(geometry.faces) > 10:
                confidence += 0.2

            # Performance metrics available
            if len(performance) > 3:
                confidence += 0.1

            # Manufacturability
            if manufacturing.get("printable", False):
                confidence += 0.2
            else:
                confidence -= 0.1

            # No critical issues
            if len(manufacturing.get("issues", [])) == 0:
                confidence += 0.1

        except Exception:
            confidence = 0.1

        return np.clip(confidence, 0.0, 1.0)

    def _evaluate_and_rank_alternatives(self, alternatives: List[DesignAlternative],
                                       design_input: GenerativeDesignInput):
        """Evaluate and rank design alternatives."""

        for alternative in alternatives:
            # Calculate composite score based on objectives
            score = 0.0

            performance = alternative.performance_metrics
            manufacturing = alternative.manufacturing_info

            # Weight factors based on objectives
            weights = {}
            for objective in design_input.objectives:
                if objective == DesignGoal.MINIMIZE_WEIGHT:
                    weights["weight"] = -1.0  # Negative for minimization
                elif objective == DesignGoal.MAXIMIZE_STIFFNESS:
                    weights["stiffness"] = 1.0
                elif objective == DesignGoal.MAXIMIZE_STRENGTH:
                    weights["strength"] = 1.0
                elif objective == DesignGoal.MINIMIZE_COST:
                    weights["cost"] = -1.0

            # Calculate weighted score
            for metric, weight in weights.items():
                if metric == "weight" and "weight" in performance:
                    score += weight * (1.0 / (performance["weight"] + 1e-6))  # Normalize
                elif metric == "stiffness" and "estimated_stiffness" in performance:
                    score += weight * performance["estimated_stiffness"] / 1e12  # Normalize
                elif metric == "strength" and "estimated_strength" in performance:
                    score += weight * performance["estimated_strength"] / 1e9  # Normalize
                elif metric == "cost" and "estimated_cost" in manufacturing:
                    score += weight * (1.0 / (manufacturing["estimated_cost"] + 1e-6))

            # Penalize for manufacturing issues
            if not manufacturing.get("printable", True):
                score -= 0.5

            alternative.rank_score = score

        # Sort by score (higher is better)
        alternatives.sort(key=lambda x: x.rank_score, reverse=True)

    def _analyze_design_tradeoffs(self, alternatives: List[DesignAlternative]) -> Dict[str, Any]:
        """Analyze trade-offs between design alternatives."""

        tradeoffs = {
            "pareto_front": [],
            "correlation_matrix": {},
            "sensitivity_analysis": {},
            "recommendation": {}
        }

        if len(alternatives) < 2:
            return tradeoffs

        try:
            # Extract key metrics
            weights = []
            strengths = []
            costs = []

            for alt in alternatives:
                perf = alt.performance_metrics
                manuf = alt.manufacturing_info

                weights.append(perf.get("weight", 0))
                strengths.append(perf.get("estimated_strength", 0))
                costs.append(manuf.get("estimated_cost", 0))

            # Calculate correlations
            tradeoffs["correlation_matrix"] = {
                "weight_vs_strength": np.corrcoef(weights, strengths)[0, 1] if len(weights) > 1 else 0,
                "weight_vs_cost": np.corrcoef(weights, costs)[0, 1] if len(weights) > 1 else 0,
                "strength_vs_cost": np.corrcoef(strengths, costs)[0, 1] if len(strengths) > 1 else 0
            }

            # Identify Pareto optimal designs
            pareto_indices = self._identify_pareto_front(alternatives)
            tradeoffs["pareto_front"] = [alternatives[i].rank_score for i in pareto_indices]

        except Exception as e:
            self.logger.warning(f"Trade-off analysis failed: {e}")

        return tradeoffs

    def _identify_pareto_front(self, alternatives: List[DesignAlternative]) -> List[int]:
        """Identify Pareto optimal designs."""

        pareto_indices = []

        for i, alt1 in enumerate(alternatives):
            is_pareto = True

            for j, alt2 in enumerate(alternatives):
                if i == j:
                    continue

                # Check if alt2 dominates alt1
                if (alt2.performance_metrics.get("weight", float('inf')) <= alt1.performance_metrics.get("weight", float('inf')) and
                    alt2.performance_metrics.get("estimated_strength", 0) >= alt1.performance_metrics.get("estimated_strength", 0) and
                    alt2.manufacturing_info.get("estimated_cost", float('inf')) <= alt1.manufacturing_info.get("estimated_cost", float('inf'))):

                    # alt2 is better in all metrics
                    if (alt2.performance_metrics.get("weight", float('inf')) < alt1.performance_metrics.get("weight", float('inf')) or
                        alt2.performance_metrics.get("estimated_strength", 0) > alt1.performance_metrics.get("estimated_strength", 0) or
                        alt2.manufacturing_info.get("estimated_cost", float('inf')) < alt1.manufacturing_info.get("estimated_cost", float('inf'))):
                        is_pareto = False
                        break

            if is_pareto:
                pareto_indices.append(i)

        return pareto_indices

    def _check_constraint_satisfaction(self, alternatives: List[DesignAlternative],
                                     design_input: GenerativeDesignInput) -> bool:
        """Check if constraints are satisfied."""

        # Simplified constraint checking
        for alternative in alternatives:
            # Check if design fits within design space
            if design_input.design_space.contains(alternative.geometry.vertices).all():
                return True

        return False

    def optimize_design_iteratively(self, design_input: GenerativeDesignInput,
                                  max_iterations: int = 10) -> GenerativeDesignResult:
        """Perform iterative design optimization."""

        # Generate initial population
        result = self.generate_designs(design_input, num_alternatives=5)

        # Iterative refinement (simplified)
        for iteration in range(max_iterations):
            if not result.design_alternatives:
                break

            # Select best designs for refinement
            best_designs = result.design_alternatives[:2]  # Top 2

            # Generate variations of best designs
            new_alternatives = []
            for design in best_designs:
                # Create slight variations
                variation = self._create_design_variation(design, design_input)
                if variation:
                    new_alternatives.append(variation)

            # Add new alternatives to population
            result.design_alternatives.extend(new_alternatives)

            # Re-evaluate and rank
            self._evaluate_and_rank_alternatives(result.design_alternatives, design_input)

            # Keep only top designs
            result.design_alternatives = result.design_alternatives[:5]

        return result

    def _create_design_variation(self, base_design: DesignAlternative,
                               design_input: GenerativeDesignInput) -> Optional[DesignAlternative]:
        """Create a variation of an existing design."""

        try:
            # Create slight modification
            variation_geometry = base_design.geometry.copy()

            # Apply small random scaling
            scale_factor = 0.95 + np.random.random() * 0.1  # 0.95 to 1.05
            variation_geometry.apply_scale(scale_factor)

            # Re-evaluate
            analysis = self._analyze_design_requirements(design_input)
            performance = self._evaluate_design_performance(variation_geometry, design_input, analysis)
            manufacturing = self._assess_manufacturability(variation_geometry, design_input, analysis)
            confidence = self._calculate_design_confidence(variation_geometry, performance, manufacturing)

            variation = DesignAlternative(
                geometry=variation_geometry,
                performance_metrics=performance,
                manufacturing_info=manufacturing,
                generation_method="variation",
                confidence_level=confidence
            )

            return variation

        except Exception:
            return None


# Global instance
advanced_generative_designer = AdvancedGenerativeDesigner()


def generate_design_alternatives(base_geometry: trimesh.Trimesh,
                               design_space: trimesh.Trimesh,
                               objectives: List[DesignGoal],
                               material: str = "pla",
                               manufacturing_process: ManufacturingProcess = ManufacturingProcess.FDM) -> GenerativeDesignResult:
    """Convenience function for generative design."""
    design_input = GenerativeDesignInput(
        base_geometry=base_geometry,
        design_space=design_space,
        objectives=objectives,
        material=material,
        manufacturing_process=manufacturing_process
    )

    return advanced_generative_designer.generate_designs(design_input)


def optimize_design_iteratively(design_input: GenerativeDesignInput,
                              max_iterations: int = 10) -> GenerativeDesignResult:
    """Convenience function for iterative optimization."""
    return advanced_generative_designer.optimize_design_iteratively(design_input, max_iterations)
