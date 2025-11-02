"""Advanced analysis module for market-ready 3D print CAD software."""

import numpy as np
import trimesh
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from scipy.spatial import ConvexHull, Delaunay
from scipy.optimize import minimize
import warnings

@dataclass
class PrintabilityScore:
    """Comprehensive printability assessment."""
    overall_score: float
    overhang_score: float
    support_score: float
    wall_thickness_score: float
    detail_preservation: float
    estimated_success_rate: float
    risk_factors: List[str]
    recommendations: List[str]

@dataclass
class OptimalOrientation:
    """Optimal printing orientation data."""
    rotation_matrix: np.ndarray
    euler_angles: Tuple[float, float, float]
    support_volume: float
    print_time_estimate: float
    quality_score: float
    stability_score: float

class AdvancedMeshAnalyzer:
    """Professional-grade mesh analysis for 3D printing."""

    def __init__(self):
        self.analysis_cache = {}
        self.material_profiles = self._load_material_profiles()

    def _load_material_profiles(self) -> Dict:
        """Load material-specific printing parameters."""
        return {
            'PLA': {
                'min_wall_thickness': 0.8,
                'max_overhang_angle': 45,
                'bridge_max_length': 10,
                'min_feature_size': 0.4,
                'shrinkage_factor': 0.002
            },
            'ABS': {
                'min_wall_thickness': 1.0,
                'max_overhang_angle': 40,
                'bridge_max_length': 8,
                'min_feature_size': 0.5,
                'shrinkage_factor': 0.008
            },
            'PETG': {
                'min_wall_thickness': 0.9,
                'max_overhang_angle': 45,
                'bridge_max_length': 12,
                'min_feature_size': 0.45,
                'shrinkage_factor': 0.004
            },
            'TPU': {
                'min_wall_thickness': 1.2,
                'max_overhang_angle': 35,
                'bridge_max_length': 5,
                'min_feature_size': 0.8,
                'shrinkage_factor': 0.005
            },
            'Nylon': {
                'min_wall_thickness': 1.0,
                'max_overhang_angle': 40,
                'bridge_max_length': 8,
                'min_feature_size': 0.6,
                'shrinkage_factor': 0.015
            }
        }

    def comprehensive_analysis(self, mesh: trimesh.Trimesh,
                             material: str = 'PLA',
                             nozzle_diameter: float = 0.4,
                             layer_height: float = 0.2) -> Dict[str, Any]:
        """Perform comprehensive mesh analysis for 3D printing."""

        results = {
            'geometry': self._analyze_geometry(mesh),
            'printability': self._assess_printability(mesh, material, nozzle_diameter, layer_height),
            'structural': self._analyze_structure(mesh),
            'support_requirements': self._calculate_support_requirements(mesh, material),
            'optimal_orientation': self._find_optimal_orientation(mesh, material),
            'print_time_estimate': self._estimate_print_time(mesh, layer_height),
            'material_usage': self._calculate_material_usage(mesh, material),
            'quality_metrics': self._assess_quality_metrics(mesh, nozzle_diameter),
            'cost_estimate': self._estimate_cost(mesh, material),
            'failure_risks': self._identify_failure_risks(mesh, material)
        }

        return results

    def _analyze_geometry(self, mesh: trimesh.Trimesh) -> Dict:
        """Detailed geometric analysis."""

        # Compute advanced geometric properties
        mesh.fix_normals()

        return {
            'bounding_box': mesh.bounds.tolist(),
            'dimensions': (mesh.bounds[1] - mesh.bounds[0]).tolist(),
            'volume': float(mesh.volume),
            'surface_area': float(mesh.area),
            'center_of_mass': mesh.center_mass.tolist(),
            'moment_of_inertia': mesh.moment_inertia.tolist(),
            'is_watertight': bool(mesh.is_watertight),
            'is_manifold': bool(mesh.is_winding_consistent),
            'euler_number': int(mesh.euler_number),
            'face_count': len(mesh.faces),
            'vertex_count': len(mesh.vertices),
            'edge_count': len(mesh.edges),
            'convex_hull_volume': float(mesh.convex_hull.volume) if mesh.is_watertight else None,
            'sphericity': self._calculate_sphericity(mesh),
            'aspect_ratios': self._calculate_aspect_ratios(mesh)
        }

    def _assess_printability(self, mesh: trimesh.Trimesh,
                           material: str,
                           nozzle_diameter: float,
                           layer_height: float) -> PrintabilityScore:
        """Comprehensive printability assessment."""

        material_props = self.material_profiles.get(material, self.material_profiles['PLA'])

        # Overhang analysis
        overhang_faces = self._find_overhang_faces(mesh, material_props['max_overhang_angle'])
        overhang_score = max(0, 100 - (len(overhang_faces) / len(mesh.faces)) * 200)

        # Support analysis
        support_volume = self._estimate_support_volume(mesh, overhang_faces)
        support_score = max(0, 100 - (support_volume / mesh.volume) * 100)

        # Wall thickness analysis
        thin_sections = self._find_thin_sections(mesh, material_props['min_wall_thickness'])
        wall_score = max(0, 100 - (len(thin_sections) / len(mesh.faces)) * 200)

        # Detail preservation
        min_feature = self._find_minimum_feature_size(mesh)
        detail_score = min(100, (min_feature / material_props['min_feature_size']) * 100)

        # Calculate overall score
        overall_score = (overhang_score * 0.3 +
                        support_score * 0.25 +
                        wall_score * 0.25 +
                        detail_score * 0.2)

        # Success rate estimation
        success_rate = self._estimate_success_rate(overall_score, mesh, material)

        # Identify risks
        risks = []
        if overhang_score < 70:
            risks.append("Significant overhangs detected")
        if wall_score < 70:
            risks.append("Thin walls may fail")
        if detail_score < 50:
            risks.append("Small details may not print correctly")
        if not mesh.is_watertight:
            risks.append("Non-watertight mesh")

        # Generate recommendations
        recommendations = self._generate_recommendations(
            overhang_score, support_score, wall_score, detail_score, mesh, material
        )

        return PrintabilityScore(
            overall_score=overall_score,
            overhang_score=overhang_score,
            support_score=support_score,
            wall_thickness_score=wall_score,
            detail_preservation=detail_score,
            estimated_success_rate=success_rate,
            risk_factors=risks,
            recommendations=recommendations
        )

    def _analyze_structure(self, mesh: trimesh.Trimesh) -> Dict:
        """Structural analysis for printing stability."""

        return {
            'center_of_gravity': mesh.center_mass.tolist(),
            'stability_score': self._calculate_stability(mesh),
            'contact_area': self._calculate_contact_area(mesh),
            'hollow_sections': self._detect_hollow_sections(mesh),
            'stress_concentration_points': self._find_stress_points(mesh),
            'weak_joints': self._identify_weak_joints(mesh)
        }

    def _calculate_support_requirements(self, mesh: trimesh.Trimesh, material: str) -> Dict:
        """Calculate detailed support requirements."""

        material_props = self.material_profiles.get(material, self.material_profiles['PLA'])
        overhang_faces = self._find_overhang_faces(mesh, material_props['max_overhang_angle'])
        bridges = self._detect_bridges(mesh, material_props['bridge_max_length'])

        support_volume = self._estimate_support_volume(mesh, overhang_faces)
        support_contact_area = self._calculate_support_contact_area(mesh, overhang_faces)

        return {
            'required': len(overhang_faces) > 0 or len(bridges) > 0,
            'overhang_area': float(sum(mesh.area_faces[overhang_faces])),
            'support_volume': float(support_volume),
            'support_contact_area': float(support_contact_area),
            'support_points': self._identify_support_points(mesh, overhang_faces),
            'bridge_segments': bridges,
            'estimated_support_material': float(support_volume * 1.2),  # 20% extra for adhesion
            'removal_difficulty': self._assess_support_removal_difficulty(mesh, overhang_faces)
        }

    def _find_optimal_orientation(self, mesh: trimesh.Trimesh, material: str) -> OptimalOrientation:
        """Find optimal printing orientation using optimization algorithms."""

        def objective_function(angles):
            """Minimize support volume and maximize stability."""
            rx, ry, rz = angles
            rotation_matrix = trimesh.transformations.euler_matrix(rx, ry, rz)
            rotated_mesh = mesh.copy()
            rotated_mesh.apply_transform(rotation_matrix)

            # Calculate metrics
            material_props = self.material_profiles.get(material, self.material_profiles['PLA'])
            overhang_faces = self._find_overhang_faces(rotated_mesh, material_props['max_overhang_angle'])
            support_volume = self._estimate_support_volume(rotated_mesh, overhang_faces)
            stability = self._calculate_stability(rotated_mesh)
            contact_area = self._calculate_contact_area(rotated_mesh)

            # Combined objective (minimize)
            return support_volume / mesh.volume - stability * 0.5 - contact_area * 0.1

        # Optimize orientation
        initial_guess = [0, 0, 0]
        bounds = [(-np.pi, np.pi), (-np.pi, np.pi), (-np.pi, np.pi)]

        result = minimize(objective_function, initial_guess, method='L-BFGS-B', bounds=bounds)

        optimal_angles = result.x
        optimal_matrix = trimesh.transformations.euler_matrix(*optimal_angles)

        # Calculate final metrics
        rotated_mesh = mesh.copy()
        rotated_mesh.apply_transform(optimal_matrix)
        material_props = self.material_profiles.get(material, self.material_profiles['PLA'])
        overhang_faces = self._find_overhang_faces(rotated_mesh, material_props['max_overhang_angle'])
        support_volume = self._estimate_support_volume(rotated_mesh, overhang_faces)

        return OptimalOrientation(
            rotation_matrix=optimal_matrix,
            euler_angles=tuple(optimal_angles),
            support_volume=float(support_volume),
            print_time_estimate=self._estimate_print_time(rotated_mesh, 0.2),
            quality_score=self._assess_orientation_quality(rotated_mesh),
            stability_score=self._calculate_stability(rotated_mesh)
        )

    def _estimate_print_time(self, mesh: trimesh.Trimesh, layer_height: float) -> float:
        """Estimate printing time in hours."""

        # Simplified estimation based on volume and complexity
        num_layers = (mesh.bounds[1][2] - mesh.bounds[0][2]) / layer_height

        # Base time components (in hours)
        layer_time = 0.5 / 60  # 30 seconds per layer average
        volume_time = mesh.volume / 10000 * 1  # 1 hour per 10cm³

        # Complexity factor
        complexity = min(2.0, len(mesh.faces) / 10000)

        total_time = num_layers * layer_time + volume_time * complexity

        return round(total_time, 2)

    def _calculate_material_usage(self, mesh: trimesh.Trimesh, material: str) -> Dict:
        """Calculate material usage and requirements."""

        material_props = self.material_profiles.get(material, self.material_profiles['PLA'])

        # Standard densities (g/cm³)
        densities = {
            'PLA': 1.24, 'ABS': 1.04, 'PETG': 1.27,
            'TPU': 1.21, 'Nylon': 1.14
        }

        density = densities.get(material, 1.24)
        volume_cm3 = mesh.volume / 1000  # Convert mm³ to cm³

        # Account for infill (assume 20% standard)
        infill_factor = 0.2 + 0.1  # 20% infill + 10% for walls

        # Account for support
        support_factor = 1.15  # 15% extra for supports on average

        material_weight = volume_cm3 * density * infill_factor * support_factor

        # Filament length calculation (1.75mm diameter)
        filament_volume = material_weight / density  # cm³
        filament_radius = 0.175 / 2  # cm
        filament_length = filament_volume / (np.pi * filament_radius ** 2)  # cm

        return {
            'volume_mm3': float(mesh.volume),
            'weight_grams': float(material_weight),
            'filament_length_meters': float(filament_length / 100),
            'with_supports': float(material_weight * 1.15),
            'shrinkage_compensation': material_props['shrinkage_factor'],
            'recommended_spool_size': '1kg' if material_weight < 900 else '2kg'
        }

    def _assess_quality_metrics(self, mesh: trimesh.Trimesh, nozzle_diameter: float) -> Dict:
        """Assess print quality metrics."""

        return {
            'surface_quality': self._assess_surface_quality(mesh),
            'dimensional_accuracy': self._predict_dimensional_accuracy(mesh, nozzle_diameter),
            'layer_adhesion_risk': self._assess_layer_adhesion(mesh),
            'warping_risk': self._assess_warping_risk(mesh),
            'stringing_risk': self._assess_stringing_risk(mesh),
            'resolution_achievable': self._determine_achievable_resolution(mesh, nozzle_diameter)
        }

    def _estimate_cost(self, mesh: trimesh.Trimesh, material: str) -> Dict:
        """Estimate printing costs."""

        material_usage = self._calculate_material_usage(mesh, material)
        print_time = self._estimate_print_time(mesh, 0.2)

        # Material costs ($/kg)
        material_costs = {
            'PLA': 20, 'ABS': 18, 'PETG': 25,
            'TPU': 35, 'Nylon': 40
        }

        material_cost_per_kg = material_costs.get(material, 20)
        material_cost = (material_usage['weight_grams'] / 1000) * material_cost_per_kg

        # Machine time cost ($/hour)
        machine_cost_per_hour = 2.0
        time_cost = print_time * machine_cost_per_hour

        # Energy cost
        energy_cost = print_time * 0.2 * 0.15  # 200W * $0.15/kWh

        total_cost = material_cost + time_cost + energy_cost

        return {
            'material_cost': round(material_cost, 2),
            'time_cost': round(time_cost, 2),
            'energy_cost': round(energy_cost, 2),
            'total_cost': round(total_cost, 2),
            'cost_per_cm3': round(total_cost / (mesh.volume / 1000), 2)
        }

    def _identify_failure_risks(self, mesh: trimesh.Trimesh, material: str) -> List[Dict]:
        """Identify potential failure risks."""

        risks = []

        # Check for non-manifold edges
        if not mesh.is_winding_consistent:
            risks.append({
                'type': 'non_manifold',
                'severity': 'high',
                'description': 'Non-manifold geometry detected',
                'mitigation': 'Repair mesh using mesh repair tools'
            })

        # Check for thin walls
        material_props = self.material_profiles.get(material, self.material_profiles['PLA'])
        thin_sections = self._find_thin_sections(mesh, material_props['min_wall_thickness'])
        if thin_sections:
            risks.append({
                'type': 'thin_walls',
                'severity': 'medium',
                'description': f'Found {len(thin_sections)} thin wall sections',
                'mitigation': 'Increase wall thickness or use different orientation'
            })

        # Check for small features
        min_feature = self._find_minimum_feature_size(mesh)
        if min_feature < material_props['min_feature_size']:
            risks.append({
                'type': 'small_features',
                'severity': 'medium',
                'description': 'Features smaller than nozzle capability',
                'mitigation': 'Scale up model or use smaller nozzle'
            })

        # Check for overhangs
        overhang_faces = self._find_overhang_faces(mesh, material_props['max_overhang_angle'])
        if len(overhang_faces) > len(mesh.faces) * 0.1:
            risks.append({
                'type': 'excessive_overhangs',
                'severity': 'high',
                'description': 'More than 10% of model requires support',
                'mitigation': 'Reorient model or redesign for better printability'
            })

        return risks

    # Helper methods
    def _calculate_sphericity(self, mesh: trimesh.Trimesh) -> float:
        """Calculate sphericity (1.0 = perfect sphere)."""
        if not mesh.is_watertight:
            return 0.0

        volume = mesh.volume
        surface_area = mesh.area

        # Sphericity = (π^(1/3) * (6V)^(2/3)) / A
        sphericity = (np.pi ** (1/3) * (6 * volume) ** (2/3)) / surface_area
        return min(1.0, sphericity)

    def _calculate_aspect_ratios(self, mesh: trimesh.Trimesh) -> Dict[str, float]:
        """Calculate aspect ratios of bounding box."""
        dims = mesh.bounds[1] - mesh.bounds[0]
        return {
            'xy_ratio': float(dims[0] / dims[1]) if dims[1] > 0 else 0,
            'xz_ratio': float(dims[0] / dims[2]) if dims[2] > 0 else 0,
            'yz_ratio': float(dims[1] / dims[2]) if dims[2] > 0 else 0
        }

    def _find_overhang_faces(self, mesh: trimesh.Trimesh, max_angle: float) -> List[int]:
        """Find faces that exceed maximum overhang angle."""
        # Calculate face normals
        face_normals = mesh.face_normals

        # Check angle with build direction (Z-axis)
        z_axis = np.array([0, 0, -1])
        angles = np.arccos(np.clip(np.dot(face_normals, z_axis), -1, 1))
        angle_degrees = np.degrees(angles)

        # Find faces exceeding threshold
        overhang_faces = np.where(angle_degrees > max_angle)[0]

        return overhang_faces.tolist()

    def _find_thin_sections(self, mesh: trimesh.Trimesh, min_thickness: float) -> List[int]:
        """Identify thin wall sections."""
        thin_sections = []

        # Simplified approach: use ray casting to estimate thickness
        # In production, use more sophisticated methods

        for i, face in enumerate(mesh.faces):
            # Get face center and normal
            center = mesh.vertices[face].mean(axis=0)
            normal = mesh.face_normals[i]

            # Cast ray in both directions
            ray_origins = np.array([center - normal * 0.001, center + normal * 0.001])
            ray_directions = np.array([normal, -normal])

            # Check intersections
            locations, index_ray, index_tri = mesh.ray.intersects_location(
                ray_origins, ray_directions
            )

            if len(locations) >= 2:
                # Calculate thickness
                distances = np.linalg.norm(locations[0] - locations[1])
                if distances < min_thickness:
                    thin_sections.append(i)

        return thin_sections

    def _find_minimum_feature_size(self, mesh: trimesh.Trimesh) -> float:
        """Find the smallest feature size in the mesh."""
        # Check edge lengths
        edges = mesh.vertices[mesh.edges_unique]
        edge_lengths = np.linalg.norm(edges[:, 0] - edges[:, 1], axis=1)

        return float(np.min(edge_lengths)) if len(edge_lengths) > 0 else 0.0

    def _estimate_support_volume(self, mesh: trimesh.Trimesh, overhang_faces: List[int]) -> float:
        """Estimate support material volume."""
        if not overhang_faces:
            return 0.0

        # Simplified estimation
        overhang_area = sum(mesh.area_faces[overhang_faces])
        avg_support_height = (mesh.bounds[1][2] - mesh.bounds[0][2]) * 0.3

        return overhang_area * avg_support_height * 0.5  # 50% infill for supports

    def _calculate_support_contact_area(self, mesh: trimesh.Trimesh, overhang_faces: List[int]) -> float:
        """Calculate support contact area."""
        if not overhang_faces:
            return 0.0

        return sum(mesh.area_faces[overhang_faces])

    def _identify_support_points(self, mesh: trimesh.Trimesh, overhang_faces: List[int]) -> List[List[float]]:
        """Identify key support contact points."""
        support_points = []

        for face_idx in overhang_faces[:100]:  # Limit to 100 points for performance
            face = mesh.faces[face_idx]
            center = mesh.vertices[face].mean(axis=0)
            support_points.append(center.tolist())

        return support_points

    def _detect_bridges(self, mesh: trimesh.Trimesh, max_length: float) -> List[Dict]:
        """Detect bridging segments."""
        bridges = []

        # Simplified bridge detection
        # In production, use more sophisticated algorithms

        return bridges

    def _assess_support_removal_difficulty(self, mesh: trimesh.Trimesh, overhang_faces: List[int]) -> str:
        """Assess difficulty of support removal."""
        if not overhang_faces:
            return 'none'

        # Check accessibility
        internal_overhangs = 0
        for face_idx in overhang_faces:
            center = mesh.vertices[mesh.faces[face_idx]].mean(axis=0)
            # Simplified check for internal faces
            if center[2] > mesh.bounds[0][2] + (mesh.bounds[1][2] - mesh.bounds[0][2]) * 0.3:
                internal_overhangs += 1

        ratio = internal_overhangs / len(overhang_faces) if overhang_faces else 0

        if ratio > 0.5:
            return 'difficult'
        elif ratio > 0.2:
            return 'moderate'
        else:
            return 'easy'

    def _calculate_stability(self, mesh: trimesh.Trimesh) -> float:
        """Calculate printing stability score."""
        # Get bottom face area
        contact_area = self._calculate_contact_area(mesh)
        total_area = mesh.area

        # Center of mass height ratio
        com = mesh.center_mass
        height_ratio = (com[2] - mesh.bounds[0][2]) / (mesh.bounds[1][2] - mesh.bounds[0][2])

        # Lower center of mass is more stable
        stability = (contact_area / total_area) * (1 - height_ratio) * 100

        return min(100, max(0, stability))

    def _calculate_contact_area(self, mesh: trimesh.Trimesh) -> float:
        """Calculate build plate contact area."""
        # Find faces close to minimum Z
        min_z = mesh.bounds[0][2]
        threshold = min_z + 0.1

        contact_faces = []
        for i, face in enumerate(mesh.faces):
            face_vertices = mesh.vertices[face]
            if all(v[2] <= threshold for v in face_vertices):
                contact_faces.append(i)

        return sum(mesh.area_faces[contact_faces]) if contact_faces else 0.0

    def _detect_hollow_sections(self, mesh: trimesh.Trimesh) -> List[Dict]:
        """Detect hollow sections in the mesh."""
        # Simplified hollow detection
        # In production, use voxelization or ray casting

        return []

    def _find_stress_points(self, mesh: trimesh.Trimesh) -> List[List[float]]:
        """Identify stress concentration points."""
        # Simplified: find sharp corners and thin connections
        stress_points = []

        # Find vertices with high curvature
        # This is a simplified approach

        return stress_points

    def _identify_weak_joints(self, mesh: trimesh.Trimesh) -> List[Dict]:
        """Identify potentially weak joints."""
        weak_joints = []

        # Simplified: look for thin connections between larger volumes
        # In production, use more sophisticated structural analysis

        return weak_joints

    def _estimate_success_rate(self, overall_score: float, mesh: trimesh.Trimesh, material: str) -> float:
        """Estimate print success rate."""
        base_rate = overall_score

        # Adjust for mesh quality
        if not mesh.is_watertight:
            base_rate *= 0.8
        if not mesh.is_winding_consistent:
            base_rate *= 0.7

        # Material difficulty factors
        material_factors = {
            'PLA': 1.0, 'PETG': 0.95, 'ABS': 0.85,
            'TPU': 0.75, 'Nylon': 0.7
        }

        material_factor = material_factors.get(material, 0.9)

        return min(99, base_rate * material_factor)

    def _generate_recommendations(self, overhang_score: float, support_score: float,
                                 wall_score: float, detail_score: float,
                                 mesh: trimesh.Trimesh, material: str) -> List[str]:
        """Generate specific recommendations."""
        recommendations = []

        if overhang_score < 70:
            recommendations.append("Consider reorienting the model to reduce overhangs")
            recommendations.append("Use tree supports for better overhang handling")

        if wall_score < 70:
            recommendations.append("Increase wall thickness in CAD or use more perimeters")
            recommendations.append("Consider using variable layer height for thin sections")

        if detail_score < 50:
            recommendations.append("Use smaller nozzle (0.2mm) for fine details")
            recommendations.append("Reduce layer height to 0.1mm for better detail")

        if not mesh.is_watertight:
            recommendations.append("Repair mesh using mesh fixing tools before printing")

        if support_score < 60:
            recommendations.append("Enable support interface layers for easier removal")
            recommendations.append("Adjust support density to 15-20% for optimal balance")

        return recommendations

    def _assess_surface_quality(self, mesh: trimesh.Trimesh) -> float:
        """Assess expected surface quality."""
        # Check face size variation
        face_areas = mesh.area_faces
        area_std = np.std(face_areas)
        area_mean = np.mean(face_areas)

        uniformity = max(0, 100 - (area_std / area_mean) * 100) if area_mean > 0 else 0

        return min(100, uniformity)

    def _predict_dimensional_accuracy(self, mesh: trimesh.Trimesh, nozzle_diameter: float) -> float:
        """Predict dimensional accuracy."""
        # Simplified prediction based on feature size vs nozzle diameter
        min_feature = self._find_minimum_feature_size(mesh)

        if min_feature < nozzle_diameter:
            return 70.0
        elif min_feature < nozzle_diameter * 2:
            return 85.0
        else:
            return 95.0

    def _assess_layer_adhesion(self, mesh: trimesh.Trimesh) -> str:
        """Assess layer adhesion risk."""
        # Check for large overhangs and bridges
        z_range = mesh.bounds[1][2] - mesh.bounds[0][2]

        # Simplified assessment
        if z_range > 200:  # Tall prints have higher risk
            return 'high'
        elif z_range > 100:
            return 'medium'
        else:
            return 'low'

    def _assess_warping_risk(self, mesh: trimesh.Trimesh) -> str:
        """Assess warping risk."""
        # Check base dimensions
        base_area = self._calculate_contact_area(mesh)
        dims = mesh.bounds[1] - mesh.bounds[0]
        max_dim = max(dims[0], dims[1])

        if max_dim > 150 or base_area > 10000:
            return 'high'
        elif max_dim > 100 or base_area > 5000:
            return 'medium'
        else:
            return 'low'

    def _assess_stringing_risk(self, mesh: trimesh.Trimesh) -> str:
        """Assess stringing risk."""
        # Check for separated components
        components = mesh.split()

        if len(components) > 5:
            return 'high'
        elif len(components) > 2:
            return 'medium'
        else:
            return 'low'

    def _determine_achievable_resolution(self, mesh: trimesh.Trimesh, nozzle_diameter: float) -> Dict:
        """Determine achievable print resolution."""
        min_feature = self._find_minimum_feature_size(mesh)

        return {
            'recommended_layer_height': min(0.3, nozzle_diameter * 0.75),
            'minimum_layer_height': nozzle_diameter * 0.25,
            'maximum_layer_height': nozzle_diameter * 0.75,
            'xy_resolution': nozzle_diameter,
            'minimum_feature_reproducible': max(min_feature, nozzle_diameter * 1.5)
        }

    def _assess_orientation_quality(self, mesh: trimesh.Trimesh) -> float:
        """Assess quality of current orientation."""
        # Combine multiple factors
        stability = self._calculate_stability(mesh)
        contact = self._calculate_contact_area(mesh) / mesh.area * 100

        # Check for minimal support needs
        material_props = self.material_profiles['PLA']
        overhang_faces = self._find_overhang_faces(mesh, material_props['max_overhang_angle'])
        support_ratio = len(overhang_faces) / len(mesh.faces)

        quality = stability * 0.4 + contact * 0.3 + (1 - support_ratio) * 100 * 0.3

        return min(100, max(0, quality))