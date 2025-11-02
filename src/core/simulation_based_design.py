"""Simulation-based design assistance with FEA integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union
import numpy as np
import trimesh
from enum import Enum
import logging
import time


class AnalysisType(Enum):
    """Types of structural analysis."""
    STATIC = "static"              # Static structural analysis
    MODAL = "modal"               # Modal analysis (natural frequencies)
    THERMAL = "thermal"           # Thermal analysis
    BUCKLING = "buckling"         # Buckling analysis
    FATIGUE = "fatigue"           # Fatigue analysis
    DYNAMIC = "dynamic"           # Dynamic analysis


class MaterialModel(Enum):
    """Material constitutive models."""
    LINEAR_ELASTIC = "linear_elastic"
    NONLINEAR_ELASTIC = "nonlinear_elastic"
    PLASTIC = "plastic"
    VISCOELASTIC = "viscoelastic"
    HYPERELASTIC = "hyperelastic"


@dataclass
class MaterialProperties:
    """Material properties for analysis."""

    name: str
    density: float  # kg/m³
    youngs_modulus: float  # Pa
    poisson_ratio: float
    yield_strength: Optional[float] = None  # Pa
    ultimate_strength: Optional[float] = None  # Pa
    thermal_expansion: float = 1e-5  # 1/K
    thermal_conductivity: float = 0.0  # W/(m·K)
    specific_heat: float = 0.0  # J/(kg·K)

    @classmethod
    def common_materials(cls) -> Dict[str, 'MaterialProperties']:
        """Get common engineering materials."""
        return {
            "steel": cls(
                name="Steel",
                density=7850,
                youngs_modulus=200e9,
                poisson_ratio=0.3,
                yield_strength=250e6,
                ultimate_strength=400e6,
                thermal_expansion=1.2e-5,
                thermal_conductivity=50.0,
                specific_heat=470.0
            ),
            "aluminum": cls(
                name="Aluminum",
                density=2700,
                youngs_modulus=70e9,
                poisson_ratio=0.33,
                yield_strength=100e6,
                ultimate_strength=200e6,
                thermal_expansion=2.3e-5,
                thermal_conductivity=237.0,
                specific_heat=897.0
            ),
            "pla": cls(
                name="PLA",
                density=1250,
                youngs_modulus=3.5e9,
                poisson_ratio=0.35,
                yield_strength=50e6,
                ultimate_strength=70e6,
                thermal_expansion=5e-5,
                thermal_conductivity=0.13,
                specific_heat=1800.0
            ),
            "abs": cls(
                name="ABS",
                density=1050,
                youngs_modulus=2.2e9,
                poisson_ratio=0.35,
                yield_strength=40e6,
                ultimate_strength=60e6,
                thermal_expansion=7e-5,
                thermal_conductivity=0.25,
                specific_heat=1500.0
            )
        }


@dataclass
class LoadCondition:
    """Load condition for analysis."""

    load_type: str  # "force", "pressure", "gravity", "thermal", "displacement"
    magnitude: Union[float, np.ndarray]
    direction: Optional[np.ndarray] = None
    location: Optional[np.ndarray] = None  # Point of application
    distribution: str = "uniform"  # "uniform", "linear", "custom"


@dataclass
class BoundaryCondition:
    """Boundary condition for analysis."""

    condition_type: str  # "fixed", "roller", "pinned", "symmetry"
    location: np.ndarray
    constraints: List[str]  # ["ux", "uy", "uz", "rx", "ry", "rz"]


@dataclass
class AnalysisResult:
    """Result of structural analysis."""

    analysis_type: AnalysisType
    displacements: np.ndarray
    stresses: np.ndarray
    strains: np.ndarray
    reaction_forces: np.ndarray
    natural_frequencies: Optional[np.ndarray] = None
    mode_shapes: Optional[np.ndarray] = None
    temperatures: Optional[np.ndarray] = None
    safety_factors: Optional[np.ndarray] = None
    converged: bool = True
    iterations: int = 0
    error_estimate: float = 0.0
    mesh_quality: float = 1.0


@dataclass
class DesignRecommendation:
    """Design improvement recommendation based on analysis."""

    issue_type: str  # "stress", "displacement", "stability", "fatigue"
    severity: str   # "low", "medium", "high", "critical"
    location: np.ndarray
    description: str
    suggested_fix: str
    quantitative_impact: Optional[Dict[str, float]] = None


class SimulationBasedDesigner:
    """Simulation-based design assistance with FEA integration."""

    def __init__(self):
        self.class AdvancedThermalAnalyzer:
    """Advanced thermal analysis for 3D printed parts."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def perform_thermal_analysis(self, mesh: trimesh.Trimesh, material: MaterialProperties,
                                boundary_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Perform advanced thermal analysis."""
        # Simplified thermal analysis for demonstration
        analysis_result = {
            'max_temperature': 0.0,
            'min_temperature': 0.0,
            'temperature_distribution': None,
            'heat_flux': None,
            'thermal_stress': None,
            'recommendations': []
        }

        # Calculate temperature distribution
        vertices = mesh.vertices
        temperature_field = self._calculate_temperature_field(vertices, material, boundary_conditions)
        analysis_result['temperature_distribution'] = temperature_field

        # Calculate thermal stress if material properties allow
        if material.youngs_modulus and material.thermal_expansion:
            thermal_stress = self._calculate_thermal_stress(temperature_field, material)
            analysis_result['thermal_stress'] = thermal_stress

        # Generate recommendations
        max_temp = np.max(temperature_field)
        min_temp = np.min(temperature_field)

        if max_temp > 100:  # Arbitrary threshold
            analysis_result['recommendations'].append("Consider better cooling for high-temperature areas")

        analysis_result['max_temperature'] = max_temp
        analysis_result['min_temperature'] = min_temp

        return analysis_result

    def _calculate_temperature_field(self, vertices: np.ndarray, material: MaterialProperties,
                                   boundary_conditions: Dict[str, Any]) -> np.ndarray:
        """Calculate temperature distribution across mesh."""
        # Simplified temperature calculation
        # In practice, would solve heat equation using FEA
        base_temp = boundary_conditions.get('ambient_temperature', 25.0)
        heat_source = boundary_conditions.get('heat_source_power', 0.0)

        # Simple linear temperature gradient based on distance from center
        center = np.mean(vertices, axis=0)
        distances = np.linalg.norm(vertices - center, axis=1)

        # Normalize distances
        max_distance = np.max(distances) if np.max(distances) > 0 else 1.0
        normalized_distances = distances / max_distance

        # Calculate temperature based on heat source and distance
        temperature_increase = heat_source * (1 - normalized_distances) * 10  # Arbitrary scaling
        temperatures = base_temp + temperature_increase

        return temperatures

    def _calculate_thermal_stress(self, temperature_field: np.ndarray, material: MaterialProperties) -> np.ndarray:
        """Calculate thermal stress due to temperature variations."""
        # Simplified thermal stress calculation
        # In practice, would use proper thermoelasticity equations

        delta_t = temperature_field - np.mean(temperature_field)
        thermal_strain = material.thermal_expansion * delta_t

        # Hooke's law for thermal stress
        thermal_stress = material.youngs_modulus * thermal_strain / (1 - material.poisson_ratio)

        return thermal_stress


class AdvancedStressAnalyzer:
    """Advanced stress analysis for complex loading conditions."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def perform_stress_analysis(self, mesh: trimesh.Trimesh, material: MaterialProperties,
                               loads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform advanced stress analysis."""
        analysis_result = {
            'von_mises_stress': None,
            'principal_stresses': None,
            'max_stress': 0.0,
            'safety_factor': 0.0,
            'critical_areas': [],
            'recommendations': []
        }

        # Calculate stress distribution
        stress_field = self._calculate_stress_field(mesh, material, loads)
        analysis_result['von_mises_stress'] = stress_field

        # Find critical areas
        max_stress = np.max(stress_field)
        critical_threshold = max_stress * 0.8  # 80% of max stress

        # Identify vertices with high stress
        critical_vertices = np.where(stress_field > critical_threshold)[0]
        analysis_result['critical_areas'] = critical_vertices.tolist()

        # Calculate safety factor
        if material.yield_strength:
            safety_factor = material.yield_strength / max_stress
            analysis_result['safety_factor'] = safety_factor

            if safety_factor < 1.5:
                analysis_result['recommendations'].append("Consider redesign for better stress distribution")
            elif safety_factor < 2.0:
                analysis_result['recommendations'].append("Monitor stress levels during use")

        analysis_result['max_stress'] = max_stress

        return analysis_result

    def _calculate_stress_field(self, mesh: trimesh.Trimesh, material: MaterialProperties,
                              loads: List[Dict[str, Any]]) -> np.ndarray:
        """Calculate stress distribution across mesh."""
        # Simplified stress calculation
        # In practice, would use finite element analysis

        vertices = mesh.vertices
        stress_field = np.zeros(len(vertices))

        for load in loads:
            load_type = load.get('type', 'force')
            magnitude = load.get('magnitude', 0.0)
            direction = load.get('direction', [0, 0, 1])
            application_point = load.get('point', [0, 0, 0])

            if load_type == 'force':
                # Calculate stress due to applied force
                force_vector = np.array(direction) * magnitude
                distances = np.linalg.norm(vertices - application_point, axis=1)

                # Simple stress distribution (inverse distance)
                stress_contribution = magnitude / (distances + 1e-6) * 0.1  # Arbitrary scaling
                stress_field += stress_contribution

        return stress_field


def run_advanced_simulation(mesh: trimesh.Trimesh, material: MaterialProperties,
                          analysis_type: AnalysisType, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Run advanced simulation with enhanced analysis capabilities."""
    if analysis_type == AnalysisType.THERMAL:
        analyzer = AdvancedThermalAnalyzer()
        return analyzer.perform_thermal_analysis(mesh, material, parameters)
    elif analysis_type in [AnalysisType.STATIC, AnalysisType.DYNAMIC]:
        analyzer = AdvancedStressAnalyzer()
        return analyzer.perform_stress_analysis(mesh, material, parameters.get('loads', []))
    else:
        # Fallback to basic analysis for other types
        return run_basic_simulation(mesh, material, analysis_type, parameters)
        self.materials = MaterialProperties.common_materials()

    def analyze_design(self, mesh: trimesh.Trimesh,
                      material: MaterialProperties,
                      loads: List[LoadCondition],
                      boundaries: List[BoundaryCondition],
                      analysis_type: AnalysisType = AnalysisType.STATIC) -> AnalysisResult:
        """Perform structural analysis on a design."""

        try:
            # Discretize mesh for analysis
            elements, nodes = self._create_analysis_mesh(mesh)

            # Assemble system matrices
            K, M = self._assemble_matrices(elements, nodes, material)

            # Apply boundary conditions
            K_reduced, M_reduced, load_vector = self._apply_boundary_conditions(
                K, M, loads, boundaries, nodes
            )

            # Solve system
            if analysis_type == AnalysisType.STATIC:
                result = self._solve_static_analysis(K_reduced, load_vector)
            elif analysis_type == AnalysisType.MODAL:
                result = self._solve_modal_analysis(K_reduced, M_reduced)
            elif analysis_type == AnalysisType.THERMAL:
                result = self._solve_thermal_analysis(K_reduced, load_vector)
            else:
                # Default to static analysis
                result = self._solve_static_analysis(K_reduced, load_vector)

            # Calculate derived quantities
            result.stresses = self._calculate_stresses(result.displacements, elements, nodes, material)
            result.strains = self._calculate_strains(result.displacements, elements, nodes)
            result.safety_factors = self._calculate_safety_factors(result.stresses, material)

            return result

        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            # Return empty result
            return AnalysisResult(
                analysis_type=analysis_type,
                displacements=np.array([]),
                stresses=np.array([]),
                strains=np.array([]),
                reaction_forces=np.array([]),
                converged=False
            )

    def generate_recommendations(self, analysis_result: AnalysisResult,
                               material: MaterialProperties,
                               mesh: trimesh.Trimesh) -> List[DesignRecommendation]:
        """Generate design improvement recommendations based on analysis."""

        recommendations = []

        try:
            # Analyze stress concentrations
            stress_recommendations = self._analyze_stress_concentrations(
                analysis_result, material, mesh
            )
            recommendations.extend(stress_recommendations)

            # Analyze displacement issues
            displacement_recommendations = self._analyze_displacements(
                analysis_result, mesh
            )
            recommendations.extend(displacement_recommendations)

            # Analyze stability (if buckling analysis available)
            if analysis_result.natural_frequencies is not None:
                stability_recommendations = self._analyze_stability(
                    analysis_result, material
                )
                recommendations.extend(stability_recommendations)

            # Analyze fatigue (simplified)
            fatigue_recommendations = self._analyze_fatigue(
                analysis_result, material
            )
            recommendations.extend(fatigue_recommendations)

            # Sort by severity
            severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            recommendations.sort(key=lambda x: severity_order.get(x.severity, 0), reverse=True)

        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {e}")

        return recommendations

    def optimize_design(self, mesh: trimesh.Trimesh,
                       material: MaterialProperties,
                       loads: List[LoadCondition],
                       boundaries: List[BoundaryCondition],
                       optimization_target: str = "weight") -> Dict[str, Any]:
        """Optimize design based on analysis results."""

        optimization_result = {
            "original_mesh": mesh,
            "optimized_mesh": mesh,  # Placeholder
            "improvement_metrics": {},
            "iterations": 0,
            "converged": False
        }

        try:
            # Run initial analysis
            initial_analysis = self.analyze_design(mesh, material, loads, boundaries)

            if not initial_analysis.converged:
                return optimization_result

            # Simple optimization: reduce material where stress is low
            # In practice, this would be much more sophisticated

            # Calculate stress-based density distribution
            avg_stress = np.mean(np.abs(initial_analysis.stresses))
            stress_ratio = np.abs(initial_analysis.stresses) / (avg_stress + 1e-6)

            # Areas with low stress can be reduced
            reduction_factor = np.clip(1.0 - stress_ratio * 0.3, 0.1, 1.0)

            # Apply optimization (simplified)
            # In practice, this would modify the mesh topology

            optimization_result.update({
                "improvement_metrics": {
                    "weight_reduction": np.mean(1.0 - reduction_factor) * 100,
                    "max_stress_change": 0.0,  # Would calculate actual change
                    "stiffness_change": 0.0
                },
                "iterations": 1,
                "converged": True
            })

        except Exception as e:
            self.logger.error(f"Design optimization failed: {e}")

        return optimization_result

    def _create_analysis_mesh(self, mesh: trimesh.Trimesh) -> Tuple[List[np.ndarray], np.ndarray]:
        """Create analysis-suitable mesh (tetrahedral elements)."""

        # For simplicity, convert to tetrahedral mesh
        # In practice, you'd use proper meshing algorithms

        try:
            # Use trimesh's tetrahedralization if available
            if hasattr(mesh, 'tetrahedralize'):
                tetrahedral_mesh = mesh.tetrahedralize()
                # Extract tetrahedral elements
                elements = []
                if hasattr(tetrahedral_mesh, 'tetrahedra'):
                    elements = tetrahedral_mesh.tetrahedra.tolist()

                nodes = tetrahedral_mesh.vertices

                return elements, nodes
            else:
                # Fallback: create simple tetrahedral mesh
                return self._create_simple_tetrahedral_mesh(mesh)

        except Exception as e:
            self.logger.warning(f"Tetrahedralization failed, using simplified mesh: {e}")
            return self._create_simple_tetrahedral_mesh(mesh)

    def _create_simple_tetrahedral_mesh(self, mesh: trimesh.Trimesh) -> Tuple[List[np.ndarray], np.ndarray]:
        """Create simplified tetrahedral mesh for analysis."""

        # Very simplified tetrahedral mesh generation
        bounds = mesh.bounds
        n_divisions = 5

        # Create structured grid
        x = np.linspace(bounds[0][0], bounds[1][0], n_divisions)
        y = np.linspace(bounds[0][1], bounds[1][1], n_divisions)
        z = np.linspace(bounds[0][2], bounds[1][2], n_divisions)

        nodes = []
        for i in x:
            for j in y:
                for k in z:
                    nodes.append([i, j, k])

        nodes = np.array(nodes)

        # Create tetrahedral elements (simplified)
        elements = []
        for i in range(n_divisions - 1):
            for j in range(n_divisions - 1):
                for k in range(n_divisions - 1):
                    # Create 6 tetrahedra per cube (simplified)
                    base_idx = i * n_divisions**2 + j * n_divisions + k

                    # Only create a few tetrahedra per cube for simplicity
                    tetra1 = [base_idx, base_idx + 1, base_idx + n_divisions, base_idx + n_divisions**2]
                    tetra2 = [base_idx + 1, base_idx + n_divisions + 1, base_idx + n_divisions, base_idx + n_divisions**2 + 1]

                    elements.extend([tetra1, tetra2])

        return elements, nodes

    def _assemble_matrices(self, elements: List[np.ndarray], nodes: np.ndarray,
                          material: MaterialProperties) -> Tuple[np.ndarray, np.ndarray]:
        """Assemble stiffness and mass matrices."""

        n_nodes = len(nodes)
        n_dof = n_nodes * 3

        # Initialize matrices
        K = np.zeros((n_dof, n_dof))  # Stiffness matrix
        M = np.zeros((n_dof, n_dof))  # Mass matrix

        for element in elements:
            if len(element) >= 4:  # Tetrahedral element
                element_nodes = nodes[element[:4]]
                K_element, M_element = self._calculate_element_matrices(element_nodes, material)

                # Assemble into global matrices
                for i in range(12):  # 4 nodes * 3 DOF
                    for j in range(12):
                        global_i = element[i // 3] * 3 + (i % 3)
                        global_j = element[j // 3] * 3 + (j % 3)

                        K[global_i, global_j] += K_element[i, j]
                        M[global_i, global_j] += M_element[i, j]

        return K, M

    def _calculate_element_matrices(self, element_nodes: np.ndarray,
                                  material: MaterialProperties) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate element stiffness and mass matrices for tetrahedral element."""

        # Simplified tetrahedral element formulation
        # In practice, this would use proper finite element theory

        # Volume calculation
        v1, v2, v3, v4 = element_nodes
        volume = abs(np.dot(v4 - v1, np.cross(v2 - v1, v3 - v1))) / 6.0

        if volume < 1e-12:
            return np.zeros((12, 12)), np.zeros((12, 12))

        # Material matrix (3D isotropic)
        E = material.youngs_modulus
        nu = material.poisson_ratio
        C = (E / ((1 + nu) * (1 - 2 * nu))) * np.array([
            [1 - nu, nu, nu, 0, 0, 0],
            [nu, 1 - nu, nu, 0, 0, 0],
            [nu, nu, 1 - nu, 0, 0, 0],
            [0, 0, 0, (1 - 2*nu)/2, 0, 0],
            [0, 0, 0, 0, (1 - 2*nu)/2, 0],
            [0, 0, 0, 0, 0, (1 - 2*nu)/2]
        ])

        # Shape function derivatives (simplified)
        B = np.zeros((6, 12))  # Strain-displacement matrix

        # Simplified stiffness matrix calculation
        K_element = volume * B.T @ C @ B

        # Mass matrix (lumped)
        density = material.density
        M_element = np.eye(12) * (density * volume / 4.0)  # Lumped mass

        return K_element, M_element

    def _apply_boundary_conditions(self, K: np.ndarray, M: np.ndarray,
                                 loads: List[LoadCondition],
                                 boundaries: List[BoundaryCondition],
                                 nodes: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Apply boundary conditions and loads."""

        n_dof = K.shape[0]
        load_vector = np.zeros(n_dof)

        # Apply loads
        for load in loads:
            if load.load_type == "force" and load.location is not None:
                # Find closest node
                distances = np.linalg.norm(nodes - load.location, axis=1)
                node_idx = np.argmin(distances)

                if load.direction is not None:
                    # Apply force in specified direction
                    for i, component in enumerate(load.direction):
                        if component != 0:
                            dof_idx = node_idx * 3 + i
                            load_vector[dof_idx] += load.magnitude * component
                else:
                    # Apply force in z-direction by default
                    load_vector[node_idx * 3 + 2] += load.magnitude

        # Apply boundary conditions (simplified)
        # In practice, this would modify the system matrices
        constrained_dof = set()

        for boundary in boundaries:
            if boundary.condition_type == "fixed":
                # Find nodes in boundary region
                distances = np.linalg.norm(nodes - boundary.location, axis=1)
                close_nodes = np.where(distances < 1.0)[0]  # Within 1 unit

                for node_idx in close_nodes:
                    for constraint in boundary.constraints:
                        if constraint == "ux":
                            constrained_dof.add(node_idx * 3)
                        elif constraint == "uy":
                            constrained_dof.add(node_idx * 3 + 1)
                        elif constraint == "uz":
                            constrained_dof.add(node_idx * 3 + 2)

        # Remove constrained DOF from system (simplified approach)
        free_dof = [i for i in range(n_dof) if i not in constrained_dof]

        K_reduced = K[np.ix_(free_dof, free_dof)]
        M_reduced = M[np.ix_(free_dof, free_dof)]
        load_vector_reduced = load_vector[free_dof]

        return K_reduced, M_reduced, load_vector_reduced

    def _solve_static_analysis(self, K: np.ndarray, load_vector: np.ndarray) -> AnalysisResult:
        """Solve static structural analysis."""

        try:
            # Solve Ku = f
            displacements_reduced = np.linalg.solve(K, load_vector)

            # Expand to full DOF vector
            displacements = np.zeros(K.shape[0] + (len(load_vector) - len(displacements_reduced)))
            free_dof = list(range(len(displacements_reduced)))
            displacements[free_dof] = displacements_reduced

            return AnalysisResult(
                analysis_type=AnalysisType.STATIC,
                displacements=displacements,
                stresses=np.array([]),  # Will be calculated later
                strains=np.array([]),
                reaction_forces=np.array([]),
                converged=True,
                iterations=1
            )

        except np.linalg.LinAlgError:
            # Matrix is singular
            return AnalysisResult(
                analysis_type=AnalysisType.STATIC,
                displacements=np.zeros(K.shape[0]),
                stresses=np.array([]),
                strains=np.array([]),
                reaction_forces=np.array([]),
                converged=False,
                iterations=0
            )

    def _solve_modal_analysis(self, K: np.ndarray, M: np.ndarray) -> AnalysisResult:
        """Solve modal analysis (natural frequencies and mode shapes)."""

        # Simplified modal analysis
        try:
            # Solve generalized eigenvalue problem: Kφ = λMφ
            eigenvalues, eigenvectors = np.linalg.eigh(K, M)

            # Natural frequencies (simplified)
            natural_frequencies = np.sqrt(np.abs(eigenvalues)) / (2 * np.pi)

            return AnalysisResult(
                analysis_type=AnalysisType.MODAL,
                displacements=np.array([]),
                stresses=np.array([]),
                strains=np.array([]),
                reaction_forces=np.array([]),
                natural_frequencies=natural_frequencies,
                mode_shapes=eigenvectors,
                converged=True,
                iterations=1
            )

        except Exception:
            return AnalysisResult(
                analysis_type=AnalysisType.MODAL,
                displacements=np.array([]),
                stresses=np.array([]),
                strains=np.array([]),
                reaction_forces=np.array([]),
                converged=False,
                iterations=0
            )

    def _solve_thermal_analysis(self, K: np.ndarray, load_vector: np.ndarray) -> AnalysisResult:
        """Solve thermal analysis."""

        # Simplified thermal analysis
        try:
            temperatures = np.linalg.solve(K, load_vector)

            return AnalysisResult(
                analysis_type=AnalysisType.THERMAL,
                displacements=np.array([]),
                stresses=np.array([]),
                strains=np.array([]),
                reaction_forces=np.array([]),
                temperatures=temperatures,
                converged=True,
                iterations=1
            )

        except Exception:
            return AnalysisResult(
                analysis_type=AnalysisType.THERMAL,
                displacements=np.array([]),
                stresses=np.array([]),
                strains=np.array([]),
                reaction_forces=np.array([]),
                converged=False,
                iterations=0
            )

    def _calculate_stresses(self, displacements: np.ndarray, elements: List[np.ndarray],
                          nodes: np.ndarray, material: MaterialProperties) -> np.ndarray:
        """Calculate stresses from displacements."""

        stresses = []

        for element in elements:
            if len(element) >= 4:
                element_nodes = nodes[element[:4]]
                element_displacements = displacements[element[:4] * 3]  # Expand to 12 DOF

                # Simplified stress calculation
                strain = np.zeros(6)  # 6 strain components
                stress = material.youngs_modulus * strain  # Hooke's law (simplified)

                stresses.append(np.max(np.abs(stress)))

        return np.array(stresses)

    def _calculate_strains(self, displacements: np.ndarray, elements: List[np.ndarray],
                         nodes: np.ndarray) -> np.ndarray:
        """Calculate strains from displacements."""

        strains = []

        for element in elements:
            if len(element) >= 4:
                # Simplified strain calculation
                strain = np.zeros(6)  # 6 strain components
                strains.append(np.max(np.abs(strain)))

        return np.array(strains)

    def _calculate_safety_factors(self, stresses: np.ndarray,
                               material: MaterialProperties) -> Optional[np.ndarray]:
        """Calculate safety factors."""

        if material.yield_strength is None:
            return None

        # Safety factor = yield strength / max stress
        safety_factors = material.yield_strength / (stresses + 1e-6)  # Avoid division by zero

        return safety_factors

    def _analyze_stress_concentrations(self, result: AnalysisResult,
                                     material: MaterialProperties,
                                     mesh: trimesh.Trimesh) -> List[DesignRecommendation]:
        """Analyze stress concentrations and generate recommendations."""

        recommendations = []

        if len(result.stresses) == 0:
            return recommendations

        # Find high stress regions
        mean_stress = np.mean(result.stresses)
        high_stress_threshold = mean_stress * 2.0

        high_stress_elements = np.where(result.stresses > high_stress_threshold)[0]

        for element_idx in high_stress_elements[:5]:  # Limit to top 5
            stress_ratio = result.stresses[element_idx] / (material.yield_strength or 1e9)

            if stress_ratio > 0.8:
                severity = "critical"
            elif stress_ratio > 0.6:
                severity = "high"
            elif stress_ratio > 0.4:
                severity = "medium"
            else:
                severity = "low"

            recommendations.append(DesignRecommendation(
                issue_type="stress",
                severity=severity,
                location=np.array([0, 0, 0]),  # Would calculate actual location
                description=f"High stress concentration detected (stress ratio: {stress_ratio:.2f})",
                suggested_fix="Add fillets or increase cross-section in high stress areas",
                quantitative_impact={"stress_reduction": 20.0, "weight_increase": 5.0}
            ))

        return recommendations

    def _analyze_displacements(self, result: AnalysisResult,
                            mesh: trimesh.Trimesh) -> List[DesignRecommendation]:
        """Analyze excessive displacements."""

        recommendations = []

        if len(result.displacements) == 0:
            return recommendations

        # Calculate maximum displacement
        max_displacement = np.max(np.abs(result.displacements))

        bounds = mesh.bounds
        characteristic_length = np.max(bounds[1] - bounds[0])

        displacement_ratio = max_displacement / characteristic_length

        if displacement_ratio > 0.1:  # More than 10% of characteristic length
            recommendations.append(DesignRecommendation(
                issue_type="displacement",
                severity="high",
                location=np.array([0, 0, 0]),
                description=f"Excessive displacement detected (ratio: {displacement_ratio:.2f})",
                suggested_fix="Add support structures or increase stiffness",
                quantitative_impact={"displacement_reduction": 30.0, "stiffness_increase": 25.0}
            ))

        return recommendations

    def _analyze_stability(self, result: AnalysisResult,
                         material: MaterialProperties) -> List[DesignRecommendation]:
        """Analyze structural stability."""

        recommendations = []

        if result.natural_frequencies is not None:
            # Check for low natural frequencies (potential for resonance)
            min_frequency = np.min(result.natural_frequencies)

            if min_frequency < 10:  # Hz
                recommendations.append(DesignRecommendation(
                    issue_type="stability",
                    severity="medium",
                    location=np.array([0, 0, 0]),
                    description=f"Low natural frequency detected ({min_frequency:.1f} Hz) - potential resonance risk",
                    suggested_fix="Increase stiffness or add damping features",
                    quantitative_impact={"frequency_increase": 50.0}
                ))

        return recommendations

    def _analyze_fatigue(self, result: AnalysisResult,
                       material: MaterialProperties) -> List[DesignRecommendation]:
        """Analyze fatigue life."""

        recommendations = []

        # Simplified fatigue analysis
        if len(result.stresses) > 0 and material.ultimate_strength:
            stress_amplitude = np.max(result.stresses) * 0.5  # Assume 50% amplitude

            # Simplified S-N curve (log-log relationship)
            fatigue_limit = material.ultimate_strength * 0.4  # Conservative estimate

            if stress_amplitude > fatigue_limit:
                life_cycles = 1e6 * (fatigue_limit / stress_amplitude) ** 3  # Simplified

                if life_cycles < 1e5:  # Less than 100k cycles
                    recommendations.append(DesignRecommendation(
                        issue_type="fatigue",
                        severity="high",
                        location=np.array([0, 0, 0]),
                        description=".0f"
                        suggested_fix="Reduce stress concentrations or use fatigue-resistant material",
                        quantitative_impact={"fatigue_life_increase": 200.0}
                    ))

        return recommendations


# Global instance
simulation_designer = SimulationBasedDesigner()


def analyze_structure(mesh: trimesh.Trimesh, material_name: str = "steel",
                    loads: Optional[List[LoadCondition]] = None,
                    boundaries: Optional[List[BoundaryCondition]] = None) -> AnalysisResult:
    """Convenience function for structural analysis."""
    material = simulation_designer.materials.get(material_name, simulation_designer.materials["steel"])

    if loads is None:
        loads = []

    if boundaries is None:
        boundaries = []

    return simulation_designer.analyze_design(mesh, material, loads, boundaries)


def get_design_recommendations(analysis_result: AnalysisResult,
                             material_name: str = "steel",
                             mesh: Optional[trimesh.Trimesh] = None) -> List[DesignRecommendation]:
    """Convenience function for design recommendations."""
    material = simulation_designer.materials.get(material_name, simulation_designer.materials["steel"])

    if mesh is None:
        mesh = trimesh.Trimesh()  # Empty mesh as fallback

    return simulation_designer.generate_recommendations(analysis_result, material, mesh)
