"""Advanced post-processing engine for 3D printing optimization."""

import numpy as np
import trimesh
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import math
import cv2
from pathlib import Path

class PostProcessingType(Enum):
    """Post-processing operation types."""
    SURFACE_SMOOTHING = "surface_smoothing"
    SUPPORT_REMOVAL = "support_removal"
    INFILL_OPTIMIZATION = "infill_optimization"
    LAYER_FUSION = "layer_fusion"
    DIMENSIONAL_CORRECTION = "dimensional_correction"
    SURFACE_FINISHING = "surface_finishing"
    STRESS_RELIEF = "stress_relief"
    TOLERANCE_ADJUSTMENT = "tolerance_adjustment"

@dataclass
class PostProcessingOperation:
    """Post-processing operation configuration."""
    type: PostProcessingType
    parameters: Dict[str, Any]
    priority: int = 0
    enabled: bool = True
    description: str = ""
    estimated_time: float = 0.0  # minutes
    material_compatibility: List[str] = None

    def __post_init__(self):
        if self.material_compatibility is None:
            self.material_compatibility = ["ALL"]

@dataclass
class SurfaceQualityMetrics:
    """Surface quality assessment metrics."""
    roughness_ra: float  # μm
    roughness_rz: float  # μm
    waviness: float  # μm
    layer_lines_visibility: float  # 0-1 scale
    surface_uniformity: float  # 0-1 scale
    dimensional_accuracy: float  # μm deviation
    feature_definition: float  # 0-1 scale

@dataclass
class PostProcessingResult:
    """Result of post-processing operations."""
    original_mesh: trimesh.Trimesh
    processed_mesh: trimesh.Trimesh
    operations_applied: List[PostProcessingOperation]
    quality_improvement: Dict[str, float]
    processing_time: float
    success_rate: float
    recommendations: List[str]
    warnings: List[str]

class AdvancedPostProcessor:
    """Professional post-processing engine."""

    def __init__(self):
        self.operations_registry = {}
        self.quality_analyzer = SurfaceQualityAnalyzer()
        self.dimensional_corrector = DimensionalCorrector()
        self.surface_optimizer = SurfaceOptimizer()

        self._register_operations()

    def _register_operations(self):
        """Register available post-processing operations."""

        # Surface smoothing operations
        self.operations_registry["gaussian_smoothing"] = PostProcessingOperation(
            type=PostProcessingType.SURFACE_SMOOTHING,
            parameters={
                "sigma": 0.5,
                "iterations": 3,
                "preserve_features": True
            },
            description="Gaussian smoothing for layer line reduction",
            estimated_time=5.0
        )

        self.operations_registry["laplacian_smoothing"] = PostProcessingOperation(
            type=PostProcessingType.SURFACE_SMOOTHING,
            parameters={
                "lambda_factor": 0.5,
                "iterations": 10,
                "boundary_preservation": True
            },
            description="Laplacian smoothing for uniform surface",
            estimated_time=8.0
        )

        # Support removal optimization
        self.operations_registry["support_interface_cleaning"] = PostProcessingOperation(
            type=PostProcessingType.SUPPORT_REMOVAL,
            parameters={
                "detection_threshold": 0.1,
                "cleaning_depth": 0.2,
                "surface_restoration": True
            },
            description="Clean support interface artifacts",
            estimated_time=12.0
        )

        # Infill optimization
        self.operations_registry["infill_density_optimization"] = PostProcessingOperation(
            type=PostProcessingType.INFILL_OPTIMIZATION,
            parameters={
                "target_strength": 0.8,
                "weight_optimization": True,
                "stress_analysis": True
            },
            description="Optimize infill for strength-to-weight ratio",
            estimated_time=15.0
        )

        # Dimensional correction
        self.operations_registry["shrinkage_compensation"] = PostProcessingOperation(
            type=PostProcessingType.DIMENSIONAL_CORRECTION,
            parameters={
                "material_shrinkage": 0.003,  # 0.3%
                "non_uniform_correction": True,
                "axis_specific": {"x": 1.0, "y": 1.0, "z": 1.002}
            },
            description="Compensate for material shrinkage",
            estimated_time=3.0
        )

        # Tolerance adjustment
        self.operations_registry["tolerance_optimization"] = PostProcessingOperation(
            type=PostProcessingType.TOLERANCE_ADJUSTMENT,
            parameters={
                "clearance_adjustment": 0.1,
                "fit_type": "sliding",  # sliding, press, clearance
                "surface_finish_compensation": True
            },
            description="Optimize tolerances for better fit",
            estimated_time=7.0
        )

    def analyze_print_quality(self, mesh: trimesh.Trimesh,
                            material: str = "PLA",
                            layer_height: float = 0.2) -> SurfaceQualityMetrics:
        """Analyze print quality and surface characteristics."""

        return self.quality_analyzer.analyze(mesh, material, layer_height)

    def recommend_operations(self, mesh: trimesh.Trimesh,
                           quality_metrics: SurfaceQualityMetrics,
                           material: str = "PLA",
                           print_settings: Dict = None) -> List[PostProcessingOperation]:
        """Recommend post-processing operations based on analysis."""

        recommendations = []

        # Surface quality-based recommendations
        if quality_metrics.roughness_ra > 10.0:  # High roughness
            recommendations.append(self.operations_registry["gaussian_smoothing"])

        if quality_metrics.layer_lines_visibility > 0.7:
            recommendations.append(self.operations_registry["laplacian_smoothing"])

        # Dimensional accuracy recommendations
        if quality_metrics.dimensional_accuracy > 50.0:  # Poor accuracy
            recommendations.append(self.operations_registry["shrinkage_compensation"])

        # Material-specific recommendations
        if material in ["ABS", "Nylon"]:
            # Higher shrinkage materials
            shrinkage_op = self.operations_registry["shrinkage_compensation"].copy()
            shrinkage_op.parameters["material_shrinkage"] = 0.008
            recommendations.append(shrinkage_op)

        # Feature definition recommendations
        if quality_metrics.feature_definition < 0.5:
            recommendations.append(self.operations_registry["tolerance_optimization"])

        return recommendations

    def apply_post_processing(self, mesh: trimesh.Trimesh,
                            operations: List[PostProcessingOperation],
                            material: str = "PLA") -> PostProcessingResult:
        """Apply post-processing operations to mesh."""

        original_mesh = mesh.copy()
        processed_mesh = mesh.copy()
        applied_operations = []
        total_time = 0.0
        success_count = 0
        warnings = []
        recommendations = []

        # Sort operations by priority
        operations = sorted(operations, key=lambda x: x.priority, reverse=True)

        for operation in operations:
            if not operation.enabled:
                continue

            # Check material compatibility
            if ("ALL" not in operation.material_compatibility and
                material not in operation.material_compatibility):
                warnings.append(f"Operation {operation.type.value} not compatible with {material}")
                continue

            try:
                # Apply operation
                processed_mesh = self._apply_operation(processed_mesh, operation)
                applied_operations.append(operation)
                total_time += operation.estimated_time
                success_count += 1

            except Exception as e:
                warnings.append(f"Failed to apply {operation.type.value}: {str(e)}")

        # Calculate quality improvement
        original_quality = self.analyze_print_quality(original_mesh, material)
        final_quality = self.analyze_print_quality(processed_mesh, material)

        quality_improvement = {
            "roughness_improvement": (original_quality.roughness_ra - final_quality.roughness_ra) / original_quality.roughness_ra,
            "dimensional_improvement": (original_quality.dimensional_accuracy - final_quality.dimensional_accuracy) / original_quality.dimensional_accuracy,
            "feature_improvement": final_quality.feature_definition - original_quality.feature_definition,
            "overall_improvement": self._calculate_overall_improvement(original_quality, final_quality)
        }

        # Generate recommendations for further improvement
        if final_quality.roughness_ra > 5.0:
            recommendations.append("Consider chemical smoothing for better surface finish")
        if final_quality.dimensional_accuracy > 25.0:
            recommendations.append("Calibrate printer for better dimensional accuracy")

        success_rate = success_count / len(operations) if operations else 1.0

        return PostProcessingResult(
            original_mesh=original_mesh,
            processed_mesh=processed_mesh,
            operations_applied=applied_operations,
            quality_improvement=quality_improvement,
            processing_time=total_time,
            success_rate=success_rate,
            recommendations=recommendations,
            warnings=warnings
        )

    def _apply_operation(self, mesh: trimesh.Trimesh,
                        operation: PostProcessingOperation) -> trimesh.Trimesh:
        """Apply specific post-processing operation."""

        if operation.type == PostProcessingType.SURFACE_SMOOTHING:
            return self._apply_surface_smoothing(mesh, operation.parameters)
        elif operation.type == PostProcessingType.SUPPORT_REMOVAL:
            return self._apply_support_removal(mesh, operation.parameters)
        elif operation.type == PostProcessingType.DIMENSIONAL_CORRECTION:
            return self._apply_dimensional_correction(mesh, operation.parameters)
        elif operation.type == PostProcessingType.TOLERANCE_ADJUSTMENT:
            return self._apply_tolerance_adjustment(mesh, operation.parameters)
        else:
            return mesh  # No operation applied

    def _apply_surface_smoothing(self, mesh: trimesh.Trimesh, params: Dict) -> trimesh.Trimesh:
        """Apply surface smoothing operations."""

        smoothed = mesh.copy()

        if "sigma" in params:  # Gaussian smoothing
            # Implement Gaussian smoothing
            smoothed = smoothed.smoothed(sigma=params["sigma"])

        if "lambda_factor" in params:  # Laplacian smoothing
            # Implement Laplacian smoothing
            for _ in range(params.get("iterations", 5)):
                smoothed = self.surface_optimizer.laplacian_smooth(
                    smoothed,
                    params["lambda_factor"]
                )

        return smoothed

    def _apply_support_removal(self, mesh: trimesh.Trimesh, params: Dict) -> trimesh.Trimesh:
        """Remove support interface artifacts."""

        cleaned = mesh.copy()

        # Detect support interface areas
        support_areas = self._detect_support_interfaces(cleaned, params["detection_threshold"])

        # Clean detected areas
        for area in support_areas:
            cleaned = self._clean_support_area(cleaned, area, params["cleaning_depth"])

        if params.get("surface_restoration", True):
            cleaned = self.surface_optimizer.restore_surface(cleaned, support_areas)

        return cleaned

    def _apply_dimensional_correction(self, mesh: trimesh.Trimesh, params: Dict) -> trimesh.Trimesh:
        """Apply dimensional corrections."""

        return self.dimensional_corrector.apply_correction(mesh, params)

    def _apply_tolerance_adjustment(self, mesh: trimesh.Trimesh, params: Dict) -> trimesh.Trimesh:
        """Adjust tolerances for better fit."""

        return self.dimensional_corrector.adjust_tolerances(mesh, params)

    def _detect_support_interfaces(self, mesh: trimesh.Trimesh, threshold: float) -> List[Dict]:
        """Detect support interface areas on mesh."""

        # Simplified detection - look for rough surface areas
        face_normals = mesh.face_normals
        face_areas = mesh.area_faces

        support_areas = []

        # Find faces with high roughness (simplified approach)
        for i, (normal, area) in enumerate(zip(face_normals, face_areas)):
            if normal[2] < -0.7:  # Downward facing
                support_areas.append({
                    "face_index": i,
                    "area": area,
                    "roughness_score": self._calculate_face_roughness(mesh, i)
                })

        return [area for area in support_areas if area["roughness_score"] > threshold]

    def _clean_support_area(self, mesh: trimesh.Trimesh, area: Dict, depth: float) -> trimesh.Trimesh:
        """Clean specific support interface area."""

        # Simplified cleaning - smooth the rough area
        face_idx = area["face_index"]

        # Get neighboring faces
        neighbors = self._get_face_neighbors(mesh, face_idx, radius=depth)

        # Apply local smoothing
        smoothed = self.surface_optimizer.local_smooth(mesh, neighbors)

        return smoothed

    def _calculate_face_roughness(self, mesh: trimesh.Trimesh, face_idx: int) -> float:
        """Calculate roughness score for a specific face."""

        # Get face and its neighbors
        neighbors = self._get_face_neighbors(mesh, face_idx, radius=1.0)

        if len(neighbors) < 3:
            return 0.0

        # Calculate normal variation
        face_normals = mesh.face_normals[neighbors]
        reference_normal = mesh.face_normals[face_idx]

        # Calculate standard deviation of dot products
        dot_products = np.dot(face_normals, reference_normal)
        roughness = 1.0 - np.mean(dot_products)

        return roughness

    def _get_face_neighbors(self, mesh: trimesh.Trimesh, face_idx: int, radius: float) -> List[int]:
        """Get neighboring faces within radius."""

        # Get face center
        face_center = mesh.triangles_center[face_idx]

        # Find faces within radius
        all_centers = mesh.triangles_center
        distances = np.linalg.norm(all_centers - face_center, axis=1)

        neighbors = np.where(distances <= radius)[0].tolist()
        return neighbors

    def _calculate_overall_improvement(self, original: SurfaceQualityMetrics,
                                     final: SurfaceQualityMetrics) -> float:
        """Calculate overall quality improvement score."""

        improvements = [
            (original.roughness_ra - final.roughness_ra) / original.roughness_ra,
            (original.dimensional_accuracy - final.dimensional_accuracy) / original.dimensional_accuracy,
            final.feature_definition - original.feature_definition,
            final.surface_uniformity - original.surface_uniformity
        ]

        # Weight the improvements
        weights = [0.3, 0.3, 0.2, 0.2]

        overall = sum(imp * weight for imp, weight in zip(improvements, weights))
        return max(0.0, min(1.0, overall))  # Clamp to 0-1 range

class SurfaceQualityAnalyzer:
    """Analyze surface quality of 3D printed parts."""

    def analyze(self, mesh: trimesh.Trimesh, material: str, layer_height: float) -> SurfaceQualityMetrics:
        """Comprehensive surface quality analysis."""

        # Calculate surface roughness
        roughness_ra = self._calculate_roughness_ra(mesh, layer_height)
        roughness_rz = self._calculate_roughness_rz(mesh, layer_height)

        # Calculate waviness
        waviness = self._calculate_waviness(mesh)

        # Layer line visibility
        layer_lines = self._assess_layer_lines(mesh, layer_height)

        # Surface uniformity
        uniformity = self._assess_surface_uniformity(mesh)

        # Dimensional accuracy
        accuracy = self._assess_dimensional_accuracy(mesh)

        # Feature definition
        features = self._assess_feature_definition(mesh)

        return SurfaceQualityMetrics(
            roughness_ra=roughness_ra,
            roughness_rz=roughness_rz,
            waviness=waviness,
            layer_lines_visibility=layer_lines,
            surface_uniformity=uniformity,
            dimensional_accuracy=accuracy,
            feature_definition=features
        )

    def _calculate_roughness_ra(self, mesh: trimesh.Trimesh, layer_height: float) -> float:
        """Calculate Ra (average roughness) based on layer height and surface variation."""

        # Theoretical Ra based on layer height
        theoretical_ra = layer_height * 0.25  # Typical relationship

        # Calculate surface variation
        face_normals = mesh.face_normals
        normal_variation = np.std(face_normals, axis=0)
        variation_factor = np.linalg.norm(normal_variation)

        # Combine theoretical and measured
        actual_ra = theoretical_ra * (1.0 + variation_factor * 10)

        return actual_ra * 1000  # Convert to micrometers

    def _calculate_roughness_rz(self, mesh: trimesh.Trimesh, layer_height: float) -> float:
        """Calculate Rz (maximum height of roughness profile)."""

        ra = self._calculate_roughness_ra(mesh, layer_height) / 1000  # Convert back to mm
        rz = ra * 6.0  # Typical relationship Rz ≈ 6*Ra

        return rz * 1000  # Convert to micrometers

    def _calculate_waviness(self, mesh: trimesh.Trimesh) -> float:
        """Calculate surface waviness."""

        # Simplified waviness calculation based on mesh geometry
        vertices = mesh.vertices

        # Calculate height variation along build direction (Z)
        z_coords = vertices[:, 2]
        z_range = np.max(z_coords) - np.min(z_coords)

        if z_range == 0:
            return 0.0

        # Calculate relative height variations
        layers = np.linspace(np.min(z_coords), np.max(z_coords), 20)
        layer_variations = []

        for i in range(len(layers) - 1):
            layer_mask = (z_coords >= layers[i]) & (z_coords < layers[i + 1])
            if np.any(layer_mask):
                layer_vertices = vertices[layer_mask]
                if len(layer_vertices) > 1:
                    xy_variation = np.std(layer_vertices[:, :2], axis=0)
                    layer_variations.append(np.linalg.norm(xy_variation))

        waviness = np.mean(layer_variations) if layer_variations else 0.0
        return waviness * 1000  # Convert to micrometers

    def _assess_layer_lines(self, mesh: trimesh.Trimesh, layer_height: float) -> float:
        """Assess visibility of layer lines (0=invisible, 1=very visible)."""

        # Calculate based on surface normal distribution
        face_normals = mesh.face_normals

        # Look for patterns in Z-normal components
        z_normals = face_normals[:, 2]
        z_variation = np.std(z_normals)

        # Higher variation suggests more visible layer lines
        visibility = min(1.0, z_variation * 5.0)

        return visibility

    def _assess_surface_uniformity(self, mesh: trimesh.Trimesh) -> float:
        """Assess surface uniformity (0=poor, 1=excellent)."""

        # Calculate uniformity based on face area variation
        face_areas = mesh.area_faces

        if len(face_areas) == 0:
            return 1.0

        area_variation = np.std(face_areas) / np.mean(face_areas)
        uniformity = max(0.0, 1.0 - area_variation)

        return uniformity

    def _assess_dimensional_accuracy(self, mesh: trimesh.Trimesh) -> float:
        """Assess dimensional accuracy deviation in micrometers."""

        # Simplified assessment based on mesh quality
        # In real application, this would compare to CAD model

        # Calculate mesh quality metrics
        face_angles = mesh.face_angles
        angle_variation = np.std(face_angles)

        # Convert to dimensional deviation estimate
        deviation = angle_variation * 100  # Empirical relationship

        return deviation * 1000  # Convert to micrometers

    def _assess_feature_definition(self, mesh: trimesh.Trimesh) -> float:
        """Assess feature definition quality (0=poor, 1=excellent)."""

        # Calculate based on edge sharpness and vertex distribution
        edges = mesh.edges_unique
        edge_lengths = mesh.edges_unique_length

        if len(edge_lengths) == 0:
            return 1.0

        # Calculate edge length consistency
        length_variation = np.std(edge_lengths) / np.mean(edge_lengths)
        definition = max(0.0, 1.0 - length_variation)

        return definition

class DimensionalCorrector:
    """Handle dimensional corrections and tolerance adjustments."""

    def apply_correction(self, mesh: trimesh.Trimesh, params: Dict) -> trimesh.Trimesh:
        """Apply dimensional corrections to mesh."""

        corrected = mesh.copy()

        # Apply shrinkage compensation
        if "material_shrinkage" in params:
            shrinkage = params["material_shrinkage"]

            if params.get("non_uniform_correction", False):
                # Apply axis-specific corrections
                axis_factors = params.get("axis_specific", {"x": 1.0, "y": 1.0, "z": 1.0})
                scale_matrix = np.diag([
                    1.0 + shrinkage * axis_factors["x"],
                    1.0 + shrinkage * axis_factors["y"],
                    1.0 + shrinkage * axis_factors["z"],
                    1.0
                ])
            else:
                # Uniform scaling
                scale_factor = 1.0 + shrinkage
                scale_matrix = np.eye(4) * scale_factor
                scale_matrix[3, 3] = 1.0

            corrected.apply_transform(scale_matrix)

        return corrected

    def adjust_tolerances(self, mesh: trimesh.Trimesh, params: Dict) -> trimesh.Trimesh:
        """Adjust tolerances for better fit."""

        adjusted = mesh.copy()

        clearance = params.get("clearance_adjustment", 0.1)
        fit_type = params.get("fit_type", "sliding")

        # Define tolerance adjustments based on fit type
        tolerance_factors = {
            "clearance": 1.2,  # More clearance
            "sliding": 1.0,    # Standard
            "press": 0.8       # Tighter fit
        }

        factor = tolerance_factors.get(fit_type, 1.0)

        # Apply uniform scaling for tolerance adjustment
        scale_factor = 1.0 + (clearance * factor / 1000)  # Convert to mm
        adjusted.apply_scale(scale_factor)

        return adjusted

class SurfaceOptimizer:
    """Advanced surface optimization algorithms."""

    def laplacian_smooth(self, mesh: trimesh.Trimesh, lambda_factor: float) -> trimesh.Trimesh:
        """Apply Laplacian smoothing to mesh."""

        smoothed = mesh.copy()

        # Get vertex neighbors
        vertex_neighbors = mesh.vertex_neighbors
        vertices = smoothed.vertices.copy()

        # Apply Laplacian smoothing
        for i, neighbors in enumerate(vertex_neighbors):
            if len(neighbors) > 0:
                neighbor_positions = vertices[neighbors]
                laplacian = np.mean(neighbor_positions, axis=0) - vertices[i]
                vertices[i] += lambda_factor * laplacian

        smoothed.vertices = vertices

        return smoothed

    def restore_surface(self, mesh: trimesh.Trimesh, damaged_areas: List[Dict]) -> trimesh.Trimesh:
        """Restore surface quality in damaged areas."""

        restored = mesh.copy()

        for area in damaged_areas:
            # Apply local reconstruction
            face_idx = area["face_index"]
            neighbors = self._get_local_region(mesh, face_idx, radius=2.0)

            # Apply local smoothing to restore surface
            restored = self.local_smooth(restored, neighbors)

        return restored

    def local_smooth(self, mesh: trimesh.Trimesh, face_indices: List[int]) -> trimesh.Trimesh:
        """Apply smoothing to specific mesh region."""

        smoothed = mesh.copy()

        # Get vertices in the region
        region_faces = mesh.faces[face_indices]
        region_vertices = np.unique(region_faces.flatten())

        # Apply local Laplacian smoothing
        vertices = smoothed.vertices.copy()
        vertex_neighbors = mesh.vertex_neighbors

        for vertex_idx in region_vertices:
            neighbors = vertex_neighbors[vertex_idx]
            if len(neighbors) > 0:
                neighbor_positions = vertices[neighbors]
                laplacian = np.mean(neighbor_positions, axis=0) - vertices[vertex_idx]
                vertices[vertex_idx] += 0.3 * laplacian  # Conservative smoothing

        smoothed.vertices = vertices

        return smoothed

    def _get_local_region(self, mesh: trimesh.Trimesh, center_face: int, radius: float) -> List[int]:
        """Get faces within radius of center face."""

        center_position = mesh.triangles_center[center_face]
        all_centers = mesh.triangles_center

        distances = np.linalg.norm(all_centers - center_position, axis=1)
        region_faces = np.where(distances <= radius)[0].tolist()

        return region_faces