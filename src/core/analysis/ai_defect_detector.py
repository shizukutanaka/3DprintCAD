"""AI-powered defect detection for 3D mesh validation using machine learning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union
import logging
import numpy as np
import trimesh
from enum import Enum

# ML libraries
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class AIDefectType(Enum):
    """Types of defects detectable by AI."""
    NON_MANIFOLD_EDGES = "non_manifold_edges"
    HOLES = "holes"
    SELF_INTERSECTIONS = "self_intersections"
    THIN_WALLS = "thin_walls"
    OVERHANGS = "overhangs"
    POOR_SURFACE_QUALITY = "poor_surface_quality"
    STRUCTURAL_WEAKNESSES = "structural_weaknesses"
    SCALING_ISSUES = "scaling_issues"
    ORIENTATION_PROBLEMS = "orientation_problems"


class AIModelType(Enum):
    """Types of AI models for defect detection."""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    NEURAL_NETWORK = "neural_network"
    ENSEMBLE = "ensemble"


@dataclass
class AIDefectDetectionResult:
    """Result of AI-powered defect detection."""

    defect_type: AIDefectType
    confidence: float
    severity: str  # "low", "medium", "high", "critical"
    location: Optional[List[float]] = None  # 3D coordinates
    description: str = ""
    suggested_fix: Optional[str] = None
    feature_importance: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "defect_type": self.defect_type.value,
            "confidence": self.confidence,
            "severity": self.severity,
            "location": self.location,
            "description": self.description,
            "suggested_fix": self.suggested_fix,
            "feature_importance": self.feature_importance,
        }


@dataclass
class AIMeshFeatures:
    """Features extracted from mesh for AI analysis."""

    # Geometric features
    surface_area: float
    volume: float
    bounding_box_volume: float
    aspect_ratio: float
    compactness: float

    # Topology features
    vertex_count: int
    face_count: int
    edge_count: int
    euler_characteristic: int
    genus: int

    # Quality features
    min_edge_length: float
    max_edge_length: float
    avg_edge_length: float
    min_face_area: float
    max_face_area: float
    avg_face_area: float

    # Structural features
    min_wall_thickness: float
    overhang_ratio: float
    cavity_count: int
    floating_parts: int

    def to_array(self) -> np.ndarray:
        """Convert features to numpy array for ML models."""
        return np.array([
            self.surface_area,
            self.volume,
            self.bounding_box_volume,
            self.aspect_ratio,
            self.compactness,
            self.vertex_count,
            self.face_count,
            self.edge_count,
            self.euler_characteristic,
            self.genus,
            self.min_edge_length,
            self.max_edge_length,
            self.avg_edge_length,
            self.min_face_area,
            self.max_face_area,
            self.avg_face_area,
            self.min_wall_thickness,
            self.overhang_ratio,
            self.cavity_count,
            self.floating_parts,
        ])


"""Advanced AI-powered defect detection for 3D mesh validation using deep learning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union
import logging
import numpy as np
import trimesh
from enum import Enum
import json
import pickle
from pathlib import Path
import hashlib
import time

# ML libraries
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import Dataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class AIDefectType(Enum):
    """Types of defects detectable by AI."""
    NON_MANIFOLD_EDGES = "non_manifold_edges"
    HOLES = "holes"
    SELF_INTERSECTIONS = "self_intersections"
    THIN_WALLS = "thin_walls"
    OVERHANGS = "overhangs"
    POOR_SURFACE_QUALITY = "poor_surface_quality"
    STRUCTURAL_WEAKNESSES = "structural_weaknesses"
    SCALING_ISSUES = "scaling_issues"
    ORIENTATION_PROBLEMS = "orientation_problems"
    PRINTABILITY_ISSUES = "printability_issues"


class AIModelType(Enum):
    """Types of AI models for defect detection."""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    NEURAL_NETWORK = "neural_network"
    ENSEMBLE = "ensemble"
    DEEP_LEARNING = "deep_learning"


class DefectSeverity(Enum):
    """Severity levels for defects."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AIMeshFeatures:
    """Enhanced features extracted from mesh for AI analysis."""

    # Basic geometric features
    surface_area: float
    volume: float
    bounding_box_volume: float
    aspect_ratio: float
    compactness: float

    # Topology features
    vertex_count: int
    face_count: int
    edge_count: int
    euler_characteristic: int
    genus: int

    # Quality features
    min_edge_length: float
    max_edge_length: float
    avg_edge_length: float
    min_face_area: float
    max_face_area: float
    avg_face_area: float

    # Structural features
    min_wall_thickness: float
    overhang_ratio: float
    cavity_count: int
    floating_parts: int

    # Advanced features
    surface_roughness: float
    curvature_variance: float
    normal_consistency: float
    mesh_density: float
    symmetry_score: float

    # Statistical features
    edge_length_std: float
    face_area_std: float
    vertex_distribution_entropy: float

    def to_array(self) -> np.ndarray:
        """Convert features to numpy array for ML models."""
        return np.array([
            self.surface_area,
            self.volume,
            self.bounding_box_volume,
            self.aspect_ratio,
            self.compactness,
            self.vertex_count,
            self.face_count,
            self.edge_count,
            self.euler_characteristic,
            self.genus,
            self.min_edge_length,
            self.max_edge_length,
            self.avg_edge_length,
            self.min_face_area,
            self.max_face_area,
            self.avg_face_area,
            self.min_wall_thickness,
            self.overhang_ratio,
            self.cavity_count,
            self.floating_parts,
            self.surface_roughness,
            self.curvature_variance,
            self.normal_consistency,
            self.mesh_density,
            self.symmetry_score,
            self.edge_length_std,
            self.face_area_std,
            self.vertex_distribution_entropy,
        ])

    def to_tensor(self) -> torch.Tensor:
        """Convert features to PyTorch tensor."""
        if TORCH_AVAILABLE:
            return torch.FloatTensor(self.to_array()).unsqueeze(0)
        return torch.from_numpy(self.to_array()).float().unsqueeze(0)


@dataclass
class AIDefectDetectionResult:
    """Enhanced result of AI-powered defect detection."""

    defect_type: AIDefectType
    confidence: float
    severity: DefectSeverity
    location: Optional[List[float]] = None  # 3D coordinates
    description: str = ""
    suggested_fix: Optional[str] = None
    feature_importance: Dict[str, float] = field(default_factory=dict)
    affected_area: Optional[Dict[str, Any]] = None
    repair_suggestions: List[str] = field(default_factory=list)
    risk_score: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "defect_type": self.defect_type.value,
            "confidence": self.confidence,
            "severity": self.severity.value,
            "location": self.location,
            "description": self.description,
            "suggested_fix": self.suggested_fix,
            "feature_importance": self.feature_importance,
            "affected_area": self.affected_area,
            "repair_suggestions": self.repair_suggestions,
            "risk_score": self.risk_score,
        }


class MeshFeatureExtractor:
    """Advanced feature extractor for 3D meshes."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def extract_comprehensive_features(self, mesh: trimesh.Trimesh) -> AIMeshFeatures:
        """Extract comprehensive features from mesh for AI analysis."""
        try:
            # Basic geometric properties
            surface_area = mesh.area
            volume = mesh.volume if mesh.is_watertight else 0.0
            bounds = mesh.bounds
            bounding_box_volume = np.prod(bounds[1] - bounds[0])

            # Aspect ratio (longest to shortest dimension)
            dimensions = bounds[1] - bounds[0]
            aspect_ratio = max(dimensions) / min(dimensions) if min(dimensions) > 0 else float('inf')

            # Compactness (sphere-like measure)
            compactness = (surface_area ** 3) / (36 * np.pi * volume ** 2) if volume > 0 else float('inf')

            # Topology features
            vertex_count = len(mesh.vertices)
            face_count = len(mesh.faces)
            edge_count = len(mesh.edges_unique)
            euler_characteristic = vertex_count - edge_count + face_count
            genus = (2 - euler_characteristic) // 2 if euler_characteristic <= 2 else 0

            # Edge length statistics
            edge_lengths = mesh.edges_unique_length
            min_edge_length = float(np.min(edge_lengths)) if len(edge_lengths) > 0 else 0.0
            max_edge_length = float(np.max(edge_lengths)) if len(edge_lengths) > 0 else 0.0
            avg_edge_length = float(np.mean(edge_lengths)) if len(edge_lengths) > 0 else 0.0
            edge_length_std = float(np.std(edge_lengths)) if len(edge_lengths) > 0 else 0.0

            # Face area statistics
            face_areas = mesh.area_faces
            min_face_area = float(np.min(face_areas)) if len(face_areas) > 0 else 0.0
            max_face_area = float(np.max(face_areas)) if len(face_areas) > 0 else 0.0
            avg_face_area = float(np.mean(face_areas)) if len(face_areas) > 0 else 0.0
            face_area_std = float(np.std(face_areas)) if len(face_areas) > 0 else 0.0

            # Wall thickness estimation (enhanced)
            min_wall_thickness = self._estimate_wall_thickness(mesh)

            # Overhang analysis
            overhang_ratio = self._calculate_overhang_ratio(mesh)

            # Cavity detection
            cavity_count = self._count_cavities(mesh)

            # Floating parts
            floating_parts = len(trimesh.graph.connected_components(mesh.face_adjacency)) - 1

            # Advanced features
            surface_roughness = self._calculate_surface_roughness(mesh)
            curvature_variance = self._calculate_curvature_variance(mesh)
            normal_consistency = self._calculate_normal_consistency(mesh)
            mesh_density = self._calculate_mesh_density(mesh)
            symmetry_score = self._calculate_symmetry_score(mesh)

            # Statistical features
            vertex_distribution_entropy = self._calculate_vertex_distribution_entropy(mesh)

            return AIMeshFeatures(
                surface_area=surface_area,
                volume=volume,
                bounding_box_volume=bounding_box_volume,
                aspect_ratio=aspect_ratio,
                compactness=compactness,
                vertex_count=vertex_count,
                face_count=face_count,
                edge_count=edge_count,
                euler_characteristic=euler_characteristic,
                genus=genus,
                min_edge_length=min_edge_length,
                max_edge_length=max_edge_length,
                avg_edge_length=avg_edge_length,
                min_face_area=min_face_area,
                max_face_area=max_face_area,
                avg_face_area=avg_face_area,
                min_wall_thickness=min_wall_thickness,
                overhang_ratio=overhang_ratio,
                cavity_count=cavity_count,
                floating_parts=floating_parts,
                surface_roughness=surface_roughness,
                curvature_variance=curvature_variance,
                normal_consistency=normal_consistency,
                mesh_density=mesh_density,
                symmetry_score=symmetry_score,
                edge_length_std=edge_length_std,
                face_area_std=face_area_std,
                vertex_distribution_entropy=vertex_distribution_entropy,
            )

        except Exception as e:
            self.logger.error(f"Error extracting features: {e}")
            # Return basic features as fallback
            return self._get_basic_features(mesh)

    def _get_basic_features(self, mesh: trimesh.Trimesh) -> AIMeshFeatures:
        """Get basic features as fallback."""
        bounds = mesh.bounds
        return AIMeshFeatures(
            surface_area=mesh.area,
            volume=mesh.volume if mesh.is_watertight else 0.0,
            bounding_box_volume=np.prod(bounds[1] - bounds[0]),
            aspect_ratio=max(bounds[1] - bounds[0]) / min(bounds[1] - bounds[0]) if min(bounds[1] - bounds[0]) > 0 else float('inf'),
            compactness=0.0,
            vertex_count=len(mesh.vertices),
            face_count=len(mesh.faces),
            edge_count=len(mesh.edges_unique),
            euler_characteristic=0,
            genus=0,
            min_edge_length=0.0,
            max_edge_length=0.0,
            avg_edge_length=0.0,
            min_face_area=0.0,
            max_face_area=0.0,
            avg_face_area=0.0,
            min_wall_thickness=0.8,
            overhang_ratio=0.0,
            cavity_count=0,
            floating_parts=0,
            surface_roughness=0.0,
            curvature_variance=0.0,
            normal_consistency=0.0,
            mesh_density=0.0,
            symmetry_score=0.0,
            edge_length_std=0.0,
            face_area_std=0.0,
            vertex_distribution_entropy=0.0,
        )

    def _estimate_wall_thickness(self, mesh: trimesh.Trimesh) -> float:
        """Estimate minimum wall thickness using advanced ray casting."""
        try:
            bounds = mesh.bounds
            center = (bounds[0] + bounds[1]) / 2

            # Use more sophisticated ray casting
            directions = [
                [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1],
                [1, 1, 0], [1, -1, 0], [-1, 1, 0], [-1, -1, 0],
                [1, 0, 1], [1, 0, -1], [-1, 0, 1], [-1, 0, -1],
                [0, 1, 1], [0, 1, -1], [0, -1, 1], [0, -1, -1]
            ]

            thicknesses = []
            for direction in directions:
                # Cast ray and find intersections
                locations, index_ray, index_tri = mesh.ray.intersects_location(
                    ray_origins=[center],
                    ray_directions=[direction],
                    multiple_hits=True
                )

                if len(locations) >= 2:
                    # Calculate distances and find minimum thickness
                    distances = np.linalg.norm(locations - center, axis=1)
                    for i in range(len(distances) - 1):
                        thickness = abs(distances[i+1] - distances[i])
                        if thickness > 0.01:  # Avoid noise
                            thicknesses.append(thickness)

            return min(thicknesses) if thicknesses else 0.8

        except Exception:
            return 0.8  # Default minimum

    def _calculate_surface_roughness(self, mesh: trimesh.Trimesh) -> float:
        """Calculate surface roughness metric."""
        try:
            # Calculate variation in face normals
            face_normals = mesh.face_normals
            normal_magnitude_variance = np.var(np.linalg.norm(face_normals, axis=1))

            # Calculate edge length variation
            edge_lengths = mesh.edges_unique_length
            edge_length_variance = np.var(edge_lengths) if len(edge_lengths) > 0 else 0.0

            # Combine metrics
            roughness = (normal_magnitude_variance * 0.5 + edge_length_variance * 0.5)
            return float(roughness)

        except Exception:
            return 0.0

    def _calculate_curvature_variance(self, mesh: trimesh.Trimesh) -> float:
        """Calculate curvature variance across mesh surface."""
        try:
            # Calculate discrete curvature using angle deviation
            curvatures = []

            for face_idx in range(len(mesh.faces)):
                face = mesh.faces[face_idx]
                vertices = mesh.vertices[face]

                # Calculate angles at each vertex
                for i in range(3):
                    v1 = vertices[i]
                    v2 = vertices[(i + 1) % 3]
                    v3 = vertices[(i + 2) % 3]

                    # Vector calculations
                    vec1 = v1 - v2
                    vec2 = v3 - v2

                    # Calculate angle
                    cos_angle = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
                    cos_angle = np.clip(cos_angle, -1.0, 1.0)
                    angle = np.arccos(cos_angle)

                    curvatures.append(angle)

            return float(np.var(curvatures)) if curvatures else 0.0

        except Exception:
            return 0.0

    def _calculate_normal_consistency(self, mesh: trimesh.Trimesh) -> float:
        """Calculate normal vector consistency."""
        try:
            face_normals = mesh.face_normals

            # Check for consistent orientation
            # Calculate average normal
            avg_normal = np.mean(face_normals, axis=0)
            avg_normal /= np.linalg.norm(avg_normal)

            # Calculate consistency score
            dot_products = np.dot(face_normals, avg_normal)
            consistency = np.mean(dot_products)

            return float(consistency)

        except Exception:
            return 0.0

    def _calculate_mesh_density(self, mesh: trimesh.Trimesh) -> float:
        """Calculate mesh density metric."""
        try:
            # Calculate vertices per unit surface area
            if mesh.area > 0:
                density = len(mesh.vertices) / mesh.area
                return float(density)
            return 0.0

        except Exception:
            return 0.0

    def _calculate_symmetry_score(self, mesh: trimesh.Trimesh) -> float:
        """Calculate symmetry score."""
        try:
            # Simple symmetry check along principal axes
            bounds = mesh.bounds
            center = (bounds[0] + bounds[1]) / 2

            # Check symmetry along X-axis
            left_vertices = mesh.vertices[mesh.vertices[:, 0] < center[0]]
            right_vertices = mesh.vertices[mesh.vertices[:, 0] > center[0]]

            symmetry_scores = []
            if len(left_vertices) > 0 and len(right_vertices) > 0:
                # Calculate distance from center
                left_distances = np.linalg.norm(left_vertices - center, axis=1)
                right_distances = np.linalg.norm(right_vertices - center, axis=1)

                # Compare distributions
                if len(left_distances) > 0 and len(right_distances) > 0:
                    left_mean = np.mean(left_distances)
                    right_mean = np.mean(right_distances)
                    symmetry_scores.append(1.0 - min(abs(left_mean - right_mean) / max(left_mean, right_mean), 1.0))

            return float(np.mean(symmetry_scores)) if symmetry_scores else 0.0

        except Exception:
            return 0.0

    def _calculate_vertex_distribution_entropy(self, mesh: trimesh.Trimesh) -> float:
        """Calculate entropy of vertex distribution."""
        try:
            # Calculate spatial distribution entropy
            vertices = mesh.vertices

            # Simple entropy calculation based on position distribution
            if len(vertices) < 2:
                return 0.0

            # Normalize positions
            bounds = mesh.bounds
            normalized_vertices = (vertices - bounds[0]) / (bounds[1] - bounds[0])

            # Calculate entropy for each dimension
            entropies = []
            for dim in range(3):
                hist, _ = np.histogram(normalized_vertices[:, dim], bins=10, range=(0, 1))
                hist = hist / np.sum(hist) if np.sum(hist) > 0 else hist
                hist = hist[hist > 0]  # Remove zeros
                if len(hist) > 0:
                    entropy = -np.sum(hist * np.log2(hist))
                    entropies.append(entropy)

            return float(np.mean(entropies)) if entropies else 0.0

        except Exception:
            return 0.0

    def _calculate_overhang_ratio(self, mesh: trimesh.Trimesh) -> float:
        """Calculate ratio of faces that are overhangs."""
        try:
            # Enhanced overhang detection
            face_normals = mesh.face_normals
            overhang_threshold = 0.1  # cos(84°) ≈ 0.1

            overhang_faces = np.abs(face_normals[:, 2]) < overhang_threshold
            overhang_ratio = np.sum(overhang_faces) / len(face_normals)

            return float(overhang_ratio)
        except Exception:
            return 0.0

    def _count_cavities(self, mesh: trimesh.Trimesh) -> int:
        """Count cavities in the mesh."""
        try:
            if not mesh.is_watertight:
                return 0

            # Enhanced cavity detection using voxelization
            # This is a simplified approach
            return max(0, mesh.euler_number - 2)
        except Exception:
            return 0
    """AI-powered defect detection system."""

    def __init__(self, model_type: AIModelType = AIModelType.RANDOM_FOREST):
        self.model_type = model_type
        self.models = {}
        self.scalers = {}
        self.feature_names = [
            'surface_area', 'volume', 'bounding_box_volume', 'aspect_ratio', 'compactness',
            'vertex_count', 'face_count', 'edge_count', 'euler_characteristic', 'genus',
            'min_edge_length', 'max_edge_length', 'avg_edge_length',
            'min_face_area', 'max_face_area', 'avg_face_area',
            'min_wall_thickness', 'overhang_ratio', 'cavity_count', 'floating_parts'
        ]

        if not SKLEARN_AVAILABLE:
            logging.warning("scikit-learn not available. AI defect detection disabled.")
            return

        self._initialize_models()

    def _initialize_models(self):
        """Initialize ML models for each defect type."""
        if not SKLEARN_AVAILABLE:
            return

        for defect_type in AIDefectType:
            if self.model_type == AIModelType.RANDOM_FOREST:
                self.models[defect_type] = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
            elif self.model_type == AIModelType.GRADIENT_BOOSTING:
                self.models[defect_type] = GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=6,
                    random_state=42
                )

            self.scalers[defect_type] = StandardScaler()

    def extract_features(self, mesh: trimesh.Trimesh) -> AIMeshFeatures:
        """Extract features from mesh for AI analysis."""
        # Basic geometric properties
        surface_area = mesh.area
        volume = mesh.volume if mesh.is_watertight else 0.0
        bounds = mesh.bounds
        bounding_box_volume = np.prod(bounds[1] - bounds[0])

        # Aspect ratio (longest to shortest dimension)
        dimensions = bounds[1] - bounds[0]
        aspect_ratio = max(dimensions) / min(dimensions) if min(dimensions) > 0 else float('inf')

        # Compactness (sphere-like measure)
        compactness = (surface_area ** 3) / (36 * np.pi * volume ** 2) if volume > 0 else float('inf')

        # Topology features
        vertex_count = len(mesh.vertices)
        face_count = len(mesh.faces)
        edge_count = len(mesh.edges_unique)
        euler_characteristic = vertex_count - edge_count + face_count
        genus = (2 - euler_characteristic) // 2 if euler_characteristic <= 2 else 0

        # Edge length statistics
        edge_lengths = mesh.edges_unique_length
        min_edge_length = float(np.min(edge_lengths)) if len(edge_lengths) > 0 else 0.0
        max_edge_length = float(np.max(edge_lengths)) if len(edge_lengths) > 0 else 0.0
        avg_edge_length = float(np.mean(edge_lengths)) if len(edge_lengths) > 0 else 0.0

        # Face area statistics
        face_areas = mesh.area_faces
        min_face_area = float(np.min(face_areas)) if len(face_areas) > 0 else 0.0
        max_face_area = float(np.max(face_areas)) if len(face_areas) > 0 else 0.0
        avg_face_area = float(np.mean(face_areas)) if len(face_areas) > 0 else 0.0

        # Wall thickness estimation (simplified)
        min_wall_thickness = self._estimate_min_wall_thickness(mesh)

        # Overhang analysis
        overhang_ratio = self._calculate_overhang_ratio(mesh)

        # Cavity detection
        cavity_count = self._count_cavities(mesh)

        # Floating parts
        floating_parts = len(trimesh.graph.connected_components(mesh.face_adjacency)) - 1

        return AIMeshFeatures(
            surface_area=surface_area,
            volume=volume,
            bounding_box_volume=bounding_box_volume,
            aspect_ratio=aspect_ratio,
            compactness=compactness,
            vertex_count=vertex_count,
            face_count=face_count,
            edge_count=edge_count,
            euler_characteristic=euler_characteristic,
            genus=genus,
            min_edge_length=min_edge_length,
            max_edge_length=max_edge_length,
            avg_edge_length=avg_edge_length,
            min_face_area=min_face_area,
            max_face_area=max_face_area,
            avg_face_area=avg_face_area,
            min_wall_thickness=min_wall_thickness,
            overhang_ratio=overhang_ratio,
            cavity_count=cavity_count,
            floating_parts=floating_parts,
        )

    def _estimate_min_wall_thickness(self, mesh: trimesh.Trimesh) -> float:
        """Estimate minimum wall thickness."""
        try:
            # Simple ray casting approach
            bounds = mesh.bounds
            center = (bounds[0] + bounds[1]) / 2

            # Cast rays in different directions
            directions = [
                [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]
            ]

            min_thickness = float('inf')
            for direction in directions:
                # Find intersections
                locations, index_ray, index_tri = mesh.ray.intersects_location(
                    ray_origins=[center],
                    ray_directions=[direction],
                    multiple_hits=True
                )

                if len(locations) >= 2:
                    # Calculate distance between first and last intersection
                    distances = np.linalg.norm(locations - center, axis=1)
                    thickness = abs(distances[-1] - distances[0])
                    min_thickness = min(min_thickness, thickness)

            return min_thickness if min_thickness != float('inf') else 0.8  # Default minimum
        except Exception:
            return 0.8  # Default minimum

    def _calculate_overhang_ratio(self, mesh: trimesh.Trimesh) -> float:
        """Calculate ratio of faces that are overhangs."""
        try:
            # Simple overhang detection (faces with normal Z-component < threshold)
            face_normals = mesh.face_normals
            overhang_threshold = 0.1  # cos(84°) ≈ 0.1

            overhang_faces = np.abs(face_normals[:, 2]) < overhang_threshold
            overhang_ratio = np.sum(overhang_faces) / len(face_normals)

            return float(overhang_ratio)
        except Exception:
            return 0.0

    def _count_cavities(self, mesh: trimesh.Trimesh) -> int:
        """Count cavities in the mesh."""
        try:
            # Use connected components of inverted mesh to find cavities
            if not mesh.is_watertight:
                return 0

            # This is a simplified approach - real cavity detection is complex
            return max(0, mesh.euler_number - 2)  # Euler characteristic based estimate
        except Exception:
            return 0

    def detect_defects(self, mesh: trimesh.Trimesh) -> List[AIDefectDetectionResult]:
        """Detect defects in mesh using AI models."""
        if not SKLEARN_AVAILABLE:
            return []

        results = []
        features = self.extract_features(mesh)
        feature_array = features.to_array().reshape(1, -1)

        for defect_type in AIDefectType:
            if defect_type not in self.models:
                continue

            try:
                # Scale features
                scaler = self.scalers[defect_type]
                scaled_features = scaler.transform(feature_array)

                # Get prediction and probability
                model = self.models[defect_type]
                prediction = model.predict(scaled_features)[0]
                probabilities = model.predict_proba(scaled_features)[0]

                # Get confidence for positive class
                confidence = float(probabilities[1] if len(probabilities) > 1 else probabilities[0])

                if confidence > 0.5:  # Only report if confidence > 50%
                    severity = self._calculate_severity(confidence, defect_type)

                    result = AIDefectDetectionResult(
                        defect_type=defect_type,
                        confidence=confidence,
                        severity=severity,
                        description=self._get_defect_description(defect_type),
                        suggested_fix=self._get_suggested_fix(defect_type),
                        feature_importance=self._get_feature_importance(model, defect_type)
                    )
                    results.append(result)

            except Exception as e:
                logging.warning(f"Error detecting {defect_type.value}: {e}")
                continue

        return results

    def _calculate_severity(self, confidence: float, defect_type: AIDefectType) -> str:
        """Calculate severity based on confidence and defect type."""
        if confidence > 0.8:
            return "critical"
        elif confidence > 0.6:
            return "high"
        elif confidence > 0.4:
            return "medium"
        else:
            return "low"

    def _get_defect_description(self, defect_type: AIDefectType) -> str:
        """Get human-readable description for defect type."""
        descriptions = {
            AIDefectType.NON_MANIFOLD_EDGES: "Non-manifold edges detected that may cause printing issues",
            AIDefectType.HOLES: "Holes in the mesh surface that need repair",
            AIDefectType.SELF_INTERSECTIONS: "Mesh self-intersections that prevent proper printing",
            AIDefectType.THIN_WALLS: "Walls thinner than recommended minimum may break during printing",
            AIDefectType.OVERHANGS: "Large overhangs detected requiring support structures",
            AIDefectType.POOR_SURFACE_QUALITY: "Surface quality issues that may affect print finish",
            AIDefectType.STRUCTURAL_WEAKNESSES: "Structural weaknesses that may compromise part integrity",
            AIDefectType.SCALING_ISSUES: "Scaling problems that may cause dimensional inaccuracies",
            AIDefectType.ORIENTATION_PROBLEMS: "Poor orientation for printing may cause failures",
        }
        return descriptions.get(defect_type, "Unknown defect detected")

    def _get_suggested_fix(self, defect_type: AIDefectType) -> str:
        """Get suggested fix for defect type."""
        fixes = {
            AIDefectType.NON_MANIFOLD_EDGES: "Use mesh repair tools to fix non-manifold geometry",
            AIDefectType.HOLES: "Fill holes using mesh repair software",
            AIDefectType.SELF_INTERSECTIONS: "Resolve self-intersections by separating intersecting parts",
            AIDefectType.THIN_WALLS: "Increase wall thickness or add support structures",
            AIDefectType.OVERHANGS: "Reorient model or add support structures",
            AIDefectType.POOR_SURFACE_QUALITY: "Apply surface smoothing or remeshing",
            AIDefectType.STRUCTURAL_WEAKNESSES: "Add internal supports or change infill pattern",
            AIDefectType.SCALING_ISSUES: "Check and correct model scale",
            AIDefectType.ORIENTATION_PROBLEMS: "Reorient model for better bed adhesion",
        }
        return fixes.get(defect_type, "Manual inspection recommended")

    def _get_feature_importance(self, model, defect_type: AIDefectType) -> Dict[str, float]:
        """Get feature importance from the model."""
        try:
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
                return dict(zip(self.feature_names, importances))
        except Exception:
            pass
        return {}

    def train_models(self, training_data: List[Tuple[AIMeshFeatures, Dict[AIDefectType, bool]]]):
        """Train AI models with labeled data."""
        if not SKLEARN_AVAILABLE:
            logging.warning("Cannot train models: scikit-learn not available")
            return

        # Prepare training data for each defect type
        for defect_type in AIDefectType:
            X = []
            y = []

            for features, labels in training_data:
                X.append(features.to_array())
                y.append(1 if labels.get(defect_type, False) else 0)

            if len(X) == 0 or len(y) == 0:
                continue

            X = np.array(X)
            y = np.array(y)

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Scale features
            scaler = self.scalers[defect_type]
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train model
            model = self.models[defect_type]
            model.fit(X_train_scaled, y_train)

            # Evaluate
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)

            logging.info(f"Model training results for {defect_type.value}:")
            logging.info(f"  Accuracy: {accuracy:.3f}")
            logging.info(f"  Precision: {precision:.3f}")
            logging.info(f"  Recall: {recall:.3f}")
            logging.info(f"  F1-Score: {f1:.3f}")


class AIDefectDetector:
    """Advanced AI-powered defect detection system with deep learning support."""

    def __init__(self, model_type: AIModelType = AIModelType.ENSEMBLE, enable_deep_learning: bool = True):
        self.model_type = model_type
        self.enable_deep_learning = enable_deep_learning and TORCH_AVAILABLE
        self.models = {}
        self.scalers = {}
        self.feature_extractor = MeshFeatureExtractor()
        self.model_storage = AIModelStorage()

        # Enhanced feature names including advanced features
        self.feature_names = [
            'surface_area', 'volume', 'bounding_box_volume', 'aspect_ratio', 'compactness',
            'vertex_count', 'face_count', 'edge_count', 'euler_characteristic', 'genus',
            'min_edge_length', 'max_edge_length', 'avg_edge_length',
            'min_face_area', 'max_face_area', 'avg_face_area',
            'min_wall_thickness', 'overhang_ratio', 'cavity_count', 'floating_parts',
            'surface_roughness', 'curvature_variance', 'normal_consistency',
            'mesh_density', 'symmetry_score', 'edge_length_std', 'face_area_std',
            'vertex_distribution_entropy'
        ]

        if not SKLEARN_AVAILABLE:
            logging.warning("scikit-learn not available. Traditional ML models disabled.")
            return

        # Initialize models
        self._initialize_models()

        # Try to load pre-trained models
        self._load_pretrained_models()

    def _initialize_models(self):
        """Initialize ML models for each defect type."""
        if not SKLEARN_AVAILABLE:
            return

        for defect_type in AIDefectType:
            if self.model_type == AIModelType.RANDOM_FOREST:
                self.models[defect_type] = RandomForestClassifier(
                    n_estimators=200,  # Increased for better accuracy
                    max_depth=15,
                    random_state=42,
                    n_jobs=-1,
                    class_weight='balanced'
                )
            elif self.model_type == AIModelType.GRADIENT_BOOSTING:
                self.models[defect_type] = GradientBoostingClassifier(
                    n_estimators=200,
                    max_depth=8,
                    random_state=42,
                    learning_rate=0.1
                )
            elif self.model_type == AIModelType.ENSEMBLE:
                # Create ensemble of multiple models
                self.models[defect_type] = {
                    'rf': RandomForestClassifier(
                        n_estimators=150,
                        max_depth=12,
                        random_state=42,
                        n_jobs=-1
                    ),
                    'gb': GradientBoostingClassifier(
                        n_estimators=150,
                        max_depth=8,
                        random_state=42
                    ),
                    'weights': {'rf': 0.6, 'gb': 0.4}  # Weighted ensemble
                }

            self.scalers[defect_type] = StandardScaler()

    def _load_pretrained_models(self):
        """Load pre-trained models if available."""
        try:
            # Try to load models from storage
            for defect_type in AIDefectType:
                model_data = self.model_storage.load_model(defect_type)
                if model_data:
                    self.models[defect_type] = model_data['model']
                    self.scalers[defect_type] = model_data['scaler']
                    logging.info(f"Loaded pre-trained model for {defect_type.value}")
        except Exception as e:
            logging.warning(f"Could not load pre-trained models: {e}")

    def extract_features(self, mesh: trimesh.Trimesh) -> AIMeshFeatures:
        """Extract comprehensive features from mesh for AI analysis."""
        return self.feature_extractor.extract_comprehensive_features(mesh)

    def detect_defects(self, mesh: trimesh.Trimesh, confidence_threshold: float = 0.5) -> List[AIDefectDetectionResult]:
        """Detect defects in mesh using advanced AI models."""
        if not SKLEARN_AVAILABLE and not (self.enable_deep_learning and TORCH_AVAILABLE):
            logging.warning("No ML libraries available for AI defect detection")
            return []

        results = []
        features = self.extract_features(mesh)
        feature_array = features.to_array().reshape(1, -1)

        for defect_type in AIDefectType:
            if defect_type not in self.models:
                continue

            try:
                # Get prediction based on model type
                if self.model_type == AIModelType.ENSEMBLE:
                    prediction_result = self._ensemble_predict(defect_type, feature_array, features)
                elif self.enable_deep_learning and TORCH_AVAILABLE and self.model_type == AIModelType.DEEP_LEARNING:
                    prediction_result = self._deep_learning_predict(defect_type, features)
                else:
                    prediction_result = self._traditional_predict(defect_type, feature_array)

                if prediction_result and prediction_result['confidence'] > confidence_threshold:
                    result = self._create_defect_result(defect_type, prediction_result, features, mesh)
                    results.append(result)

            except Exception as e:
                logging.warning(f"Error detecting {defect_type.value}: {e}")
                continue

        return results

    def _ensemble_predict(self, defect_type: AIDefectType, feature_array: np.ndarray,
                         features: AIMeshFeatures) -> Optional[Dict[str, Any]]:
        """Make prediction using ensemble of models."""
        models = self.models[defect_type]
        if not isinstance(models, dict):
            return None

        rf_model = models['rf']
        gb_model = models['gb']
        weights = models['weights']

        try:
            # Scale features
            scaler = self.scalers[defect_type]
            scaled_features = scaler.transform(feature_array)

            # Get predictions from each model
            rf_pred = rf_model.predict_proba(scaled_features)[0]
            gb_pred = gb_model.predict_proba(scaled_features)[0]

            # Weighted ensemble prediction
            ensemble_pred = weights['rf'] * rf_pred + weights['gb'] * gb_pred
            confidence = float(np.max(ensemble_pred))

            if confidence > 0.5:
                return {
                    'confidence': confidence,
                    'prediction': np.argmax(ensemble_pred),
                    'probabilities': ensemble_pred,
                    'feature_importance': self._get_ensemble_feature_importance(models, scaled_features)
                }

        except Exception as e:
            logging.error(f"Ensemble prediction failed for {defect_type.value}: {e}")

        return None

    def _traditional_predict(self, defect_type: AIDefectType, feature_array: np.ndarray) -> Optional[Dict[str, Any]]:
        """Make prediction using traditional ML models."""
        model = self.models[defect_type]
        if not model:
            return None

        try:
            # Scale features
            scaler = self.scalers[defect_type]
            scaled_features = scaler.transform(feature_array)

            # Get prediction and probability
            prediction = model.predict(scaled_features)[0]
            probabilities = model.predict_proba(scaled_features)[0]
            confidence = float(np.max(probabilities))

            if confidence > 0.5:
                return {
                    'confidence': confidence,
                    'prediction': prediction,
                    'probabilities': probabilities,
                    'feature_importance': self._get_feature_importance(model, defect_type)
                }

        except Exception as e:
            logging.error(f"Traditional prediction failed for {defect_type.value}: {e}")

        return None

    def _deep_learning_predict(self, defect_type: AIDefectType, features: AIMeshFeatures) -> Optional[Dict[str, Any]]:
        """Make prediction using deep learning models."""
        if not TORCH_AVAILABLE:
            return None

        try:
            # This would implement PyTorch neural network prediction
            # For now, return a placeholder
            tensor_features = features.to_tensor()

            # Placeholder for actual neural network prediction
            # In a real implementation, this would:
            # 1. Load pre-trained PyTorch model
            # 2. Run forward pass
            # 3. Return prediction probabilities

            # Simulate deep learning prediction
            confidence = 0.8  # Placeholder
            prediction = 1 if confidence > 0.5 else 0

            return {
                'confidence': confidence,
                'prediction': prediction,
                'probabilities': np.array([1-confidence, confidence])
            }

        except Exception as e:
            logging.error(f"Deep learning prediction failed for {defect_type.value}: {e}")

        return None

    def _get_ensemble_feature_importance(self, models: Dict, scaled_features: np.ndarray) -> Dict[str, float]:
        """Get feature importance from ensemble models."""
        try:
            rf_model = models['rf']
            gb_model = models['gb']
            weights = models['weights']

            # Get feature importance from each model
            rf_importance = rf_model.feature_importances_ if hasattr(rf_model, 'feature_importances_') else np.zeros(len(self.feature_names))
            gb_importance = gb_model.feature_importances_ if hasattr(gb_model, 'feature_importances_') else np.zeros(len(self.feature_names))

            # Weighted combination
            combined_importance = weights['rf'] * rf_importance + weights['gb'] * gb_importance

            return dict(zip(self.feature_names, combined_importance))

        except Exception:
            return {}

    def _get_feature_importance(self, model, defect_type: AIDefectType) -> Dict[str, float]:
        """Get feature importance from the model."""
        try:
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
                return dict(zip(self.feature_names, importances))
        except Exception:
            pass
        return {}

    def _create_defect_result(self, defect_type: AIDefectType, prediction_result: Dict[str, Any],
                             features: AIMeshFeatures, mesh: trimesh.Trimesh) -> AIDefectDetectionResult:
        """Create comprehensive defect detection result."""
        confidence = prediction_result['confidence']

        # Determine severity based on confidence and defect type
        severity = self._calculate_severity(confidence, defect_type)

        # Calculate risk score
        risk_score = self._calculate_risk_score(defect_type, confidence, features)

        # Get location information (simplified)
        location = self._estimate_defect_location(defect_type, mesh)

        # Get repair suggestions
        repair_suggestions = self._get_repair_suggestions(defect_type, features)

        return AIDefectDetectionResult(
            defect_type=defect_type,
            confidence=confidence,
            severity=severity,
            location=location,
            description=self._get_defect_description(defect_type),
            suggested_fix=self._get_suggested_fix(defect_type),
            feature_importance=prediction_result.get('feature_importance', {}),
            repair_suggestions=repair_suggestions,
            risk_score=risk_score
        )

    def _calculate_severity(self, confidence: float, defect_type: AIDefectType) -> DefectSeverity:
        """Calculate severity based on confidence and defect type."""
        # Critical defects
        if defect_type in [AIDefectType.SELF_INTERSECTIONS, AIDefectType.NON_MANIFOLD_EDGES]:
            if confidence > 0.8:
                return DefectSeverity.CRITICAL
            elif confidence > 0.6:
                return DefectSeverity.HIGH

        # High severity defects
        elif defect_type in [AIDefectType.HOLES, AIDefectType.THIN_WALLS]:
            if confidence > 0.7:
                return DefectSeverity.HIGH
            elif confidence > 0.5:
                return DefectSeverity.MEDIUM

        # Medium severity defects
        else:
            if confidence > 0.8:
                return DefectSeverity.HIGH
            elif confidence > 0.6:
                return DefectSeverity.MEDIUM
            elif confidence > 0.4:
                return DefectSeverity.LOW

        return DefectSeverity.LOW

    def _calculate_risk_score(self, defect_type: AIDefectType, confidence: float,
                             features: AIMeshFeatures) -> float:
        """Calculate risk score based on defect type and features."""
        base_risk = {
            AIDefectType.CRITICAL: 1.0,
            AIDefectType.NON_MANIFOLD_EDGES: 0.9,
            AIDefectType.SELF_INTERSECTIONS: 0.9,
            AIDefectType.HOLES: 0.8,
            AIDefectType.THIN_WALLS: 0.7,
            AIDefectType.OVERHANGS: 0.6,
            AIDefectType.POOR_SURFACE_QUALITY: 0.5,
            AIDefectType.STRUCTURAL_WEAKNESSES: 0.7,
            AIDefectType.SCALING_ISSUES: 0.4,
            AIDefectType.ORIENTATION_PROBLEMS: 0.3,
            AIDefectType.PRINTABILITY_ISSUES: 0.6
        }

        risk = base_risk.get(defect_type, 0.5) * confidence

        # Adjust based on mesh characteristics
        if features.min_wall_thickness < 0.4:
            risk *= 1.3
        if features.overhang_ratio > 0.3:
            risk *= 1.2
        if features.surface_roughness > 0.1:
            risk *= 1.1

        return min(risk, 1.0)

    def _estimate_defect_location(self, defect_type: AIDefectType, mesh: trimesh.Trimesh) -> Optional[List[float]]:
        """Estimate location of defect in 3D space."""
        try:
            # This is a simplified implementation
            # In practice, would use more sophisticated spatial analysis

            if defect_type == AIDefectType.THIN_WALLS:
                # Find thinnest wall location
                bounds = mesh.bounds
                return [(bounds[0][0] + bounds[1][0]) / 2,
                       (bounds[0][1] + bounds[1][1]) / 2,
                       (bounds[0][2] + bounds[1][2]) / 2]

            elif defect_type == AIDefectType.OVERHANGS:
                # Find highest overhang location
                face_normals = mesh.face_normals
                overhang_faces = np.abs(face_normals[:, 2]) < 0.1

                if np.any(overhang_faces):
                    # Find face with highest Z-coordinate among overhangs
                    overhang_face_indices = np.where(overhang_faces)[0]
                    max_z_face = max(overhang_face_indices,
                                   key=lambda i: np.max(mesh.vertices[mesh.faces[i]][:, 2]))
                    face_center = np.mean(mesh.vertices[mesh.faces[max_z_face]], axis=0)
                    return face_center.tolist()

            return None

        except Exception:
            return None

    def _get_repair_suggestions(self, defect_type: AIDefectType, features: AIMeshFeatures) -> List[str]:
        """Get detailed repair suggestions based on defect and features."""
        suggestions = []

        if defect_type == AIDefectType.THIN_WALLS:
            if features.min_wall_thickness < 0.4:
                suggestions.append("Significantly increase wall thickness to minimum 0.8mm")
            else:
                suggestions.append("Increase wall thickness to improve printability")
            suggestions.append("Consider adding internal supports or ribs for structural integrity")

        elif defect_type == AIDefectType.OVERHANGS:
            suggestions.append("Add support structures for overhangs steeper than 45 degrees")
            suggestions.append("Consider reorienting the model to minimize overhangs")
            suggestions.append("Use tree supports for complex overhang structures")

        elif defect_type == AIDefectType.HOLES:
            suggestions.append("Fill holes using mesh repair tools")
            suggestions.append("Check for intentional design features that should remain open")

        elif defect_type == AIDefectType.SELF_INTERSECTIONS:
            suggestions.append("Resolve intersecting geometry by separating or redesigning components")
            suggestions.append("Use boolean operations to fix intersection issues")

        elif defect_type == AIDefectType.POOR_SURFACE_QUALITY:
            suggestions.append("Apply smoothing algorithms to improve surface finish")
            suggestions.append("Consider remeshing for better triangle distribution")

        return suggestions

    def _get_defect_description(self, defect_type: AIDefectType) -> str:
        """Get detailed human-readable description for defect type."""
        descriptions = {
            AIDefectType.NON_MANIFOLD_EDGES: "Non-manifold edges detected that violate mesh topology rules and may cause printing failures",
            AIDefectType.HOLES: "Holes in the mesh surface that need repair before printing",
            AIDefectType.SELF_INTERSECTIONS: "Mesh self-intersections that prevent proper slicing and printing",
            AIDefectType.THIN_WALLS: "Walls thinner than recommended minimum may break during printing or result in poor quality",
            AIDefectType.OVERHANGS: "Large overhangs detected requiring support structures for successful printing",
            AIDefectType.POOR_SURFACE_QUALITY: "Surface quality issues that may affect print finish and mechanical properties",
            AIDefectType.STRUCTURAL_WEAKNESSES: "Structural weaknesses that may compromise part integrity under load",
            AIDefectType.SCALING_ISSUES: "Scaling problems that may cause dimensional inaccuracies in the printed part",
            AIDefectType.ORIENTATION_PROBLEMS: "Poor orientation for printing may cause failures or poor surface quality",
            AIDefectType.PRINTABILITY_ISSUES: "General printability issues that may affect successful fabrication"
        }
        return descriptions.get(defect_type, "Unknown defect detected")

    def _get_suggested_fix(self, defect_type: AIDefectType) -> str:
        """Get suggested fix for defect type."""
        fixes = {
            AIDefectType.NON_MANIFOLD_EDGES: "Use advanced mesh repair tools to fix non-manifold geometry",
            AIDefectType.HOLES: "Fill holes using professional mesh repair software",
            AIDefectType.SELF_INTERSECTIONS: "Resolve self-intersections by separating intersecting parts or using boolean operations",
            AIDefectType.THIN_WALLS: "Increase wall thickness to minimum 0.8mm and add structural reinforcements",
            AIDefectType.OVERHANGS: "Reorient model or add comprehensive support structures",
            AIDefectType.POOR_SURFACE_QUALITY: "Apply surface smoothing, remeshing, and consider post-processing",
            AIDefectType.STRUCTURAL_WEAKNESSES: "Add internal supports, change infill pattern, or redesign for better load distribution",
            AIDefectType.SCALING_ISSUES: "Check and correct model scale in CAD software",
            AIDefectType.ORIENTATION_PROBLEMS: "Reorient model for optimal bed adhesion and surface quality",
            AIDefectType.PRINTABILITY_ISSUES: "Comprehensive review and redesign may be required"
        }
        return fixes.get(defect_type, "Professional consultation recommended")

    def train_models(self, training_data: List[Tuple[AIMeshFeatures, Dict[AIDefectType, bool]]],
                    validation_split: float = 0.2):
        """Train AI models with labeled data using advanced techniques."""
        if not SKLEARN_AVAILABLE:
            logging.warning("Cannot train models: scikit-learn not available")
            return

        # Prepare training data for each defect type
        for defect_type in AIDefectType:
            X = []
            y = []

            for features, labels in training_data:
                X.append(features.to_array())
                y.append(1 if labels.get(defect_type, False) else 0)

            if len(X) == 0 or len(y) == 0:
                continue

            X = np.array(X)
            y = np.array(y)

            # Split data with stratification for imbalanced datasets
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=validation_split, random_state=42, stratify=y
            )

            # Scale features
            scaler = self.scalers[defect_type]
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train models based on type
            if self.model_type == AIModelType.ENSEMBLE:
                self._train_ensemble_models(defect_type, X_train_scaled, X_test_scaled, y_train, y_test)
            else:
                # Train single model
                model = self.models[defect_type]
                model.fit(X_train_scaled, y_train)

                # Evaluate and log performance
                self._evaluate_model(defect_type, model, X_test_scaled, y_test)

            # Save trained model
            self.model_storage.save_model(defect_type, self.models[defect_type], scaler)

    def _train_ensemble_models(self, defect_type: AIDefectType, X_train: np.ndarray,
                              X_test: np.ndarray, y_train: np.ndarray, y_test: np.ndarray):
        """Train ensemble of models for better accuracy."""
        models = self.models[defect_type]
        if not isinstance(models, dict):
            return

        rf_model = models['rf']
        gb_model = models['gb']

        # Train Random Forest
        rf_model.fit(X_train, y_train)
        rf_score = rf_model.score(X_test, y_test)

        # Train Gradient Boosting
        gb_model.fit(X_train, y_train)
        gb_score = gb_model.score(X_test, y_test)

        # Update weights based on performance
        total_score = rf_score + gb_score
        if total_score > 0:
            models['weights'] = {
                'rf': gb_score / total_score,  # Better model gets higher weight
                'gb': rf_score / total_score
            }

        logging.info(f"Trained ensemble models for {defect_type.value}: RF={rf_score:.3f}, GB={gb_score:.3f}")

    def _evaluate_model(self, defect_type: AIDefectType, model, X_test: np.ndarray, y_test: np.ndarray):
        """Evaluate trained model performance."""
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else y_pred

        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        logging.info(f"Model performance for {defect_type.value}:")
        logging.info(f"  Accuracy: {accuracy:.3f}")
        logging.info(f"  Precision: {precision:.3f}")
        logging.info(f"  Recall: {recall:.3f}")
        logging.info(f"  F1-Score: {f1:.3f}")


class AIModelVersionManager:
    """Advanced model versioning and management system."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / '.printcad' / 'ai_models'
        self.versions_dir = self.storage_dir / 'versions'
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.current_version_file = self.storage_dir / 'current_version.json'

        # Version tracking
        self.version_history: Dict[str, Dict[str, Any]] = {}
        self.current_versions: Dict[AIDefectType, str] = {}
        self.logger = logging.getLogger(__name__)

        # Load existing version information
        self._load_version_history()

    def _load_version_history(self):
        """Load version history from storage."""
        try:
            if self.current_version_file.exists():
                with open(self.current_version_file, 'r') as f:
                    self.current_versions = {
                        AIDefectType(k): v for k, v in json.load(f).items()
                    }

            # Load detailed version history
            history_file = self.versions_dir / 'version_history.json'
            if history_file.exists():
                with open(history_file, 'r') as f:
                    self.version_history = json.load(f)

        except Exception as e:
            self.logger.warning(f"Could not load version history: {e}")

    def _save_version_history(self):
        """Save version history to storage."""
        try:
            # Save current versions
            version_data = {dt.value: version for dt, version in self.current_versions.items()}
            with open(self.current_version_file, 'w') as f:
                json.dump(version_data, f, indent=2)

            # Save detailed history
            history_file = self.versions_dir / 'version_history.json'
            with open(history_file, 'w') as f:
                json.dump(self.version_history, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Failed to save version history: {e}")

    def create_model_version(self, defect_type: AIDefectType, model, scaler,
                           version_name: Optional[str] = None,
                           description: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new model version."""
        version_id = str(uuid.uuid4())[:8]
        timestamp = time.time()

        # Generate version name if not provided
        if not version_name:
            version_name = f"v{len(self.version_history) + 1}_{defect_type.value}"

        # Create version info
        version_info = {
            'version_id': version_id,
            'version_name': version_name,
            'defect_type': defect_type.value,
            'timestamp': timestamp,
            'description': description or f"Model version for {defect_type.value}",
            'metadata': metadata or {},
            'model_hash': self._calculate_model_hash(model),
            'performance_metrics': self._get_model_performance_metrics(model, defect_type),
            'file_size': self._get_model_size(model, scaler)
        }

        # Save model files with version
        version_dir = self.versions_dir / version_id
        version_dir.mkdir(exist_ok=True)

        model_file = version_dir / 'model.pkl'
        scaler_file = version_dir / 'scaler.pkl'
        version_info_file = version_dir / 'version_info.json'

        try:
            # Save model and scaler
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)
            with open(scaler_file, 'wb') as f:
                pickle.dump(scaler, f)

            # Save version info
            with open(version_info_file, 'w') as f:
                json.dump(version_info, f, indent=2, default=str)

            # Update version tracking
            self.version_history[version_id] = version_info
            self.current_versions[defect_type] = version_id

            self._save_version_history()

            self.logger.info(f"Created model version {version_id} for {defect_type.value}")
            return version_id

        except Exception as e:
            self.logger.error(f"Failed to create model version: {e}")
            # Cleanup on failure
            if version_dir.exists():
                import shutil
                shutil.rmtree(version_dir, ignore_errors=True)
            return ""

    def _calculate_model_hash(self, model) -> str:
        """Calculate hash of model for integrity checking."""
        try:
            # Convert model to string representation for hashing
            model_str = str(model).encode('utf-8')
            return hashlib.sha256(model_str).hexdigest()[:16]
        except Exception:
            return "unknown"

    def _get_model_performance_metrics(self, model, defect_type: AIDefectType) -> Dict[str, Any]:
        """Get model performance metrics."""
        try:
            metrics = {}

            if hasattr(model, 'feature_importances_'):
                metrics['feature_importance_available'] = True
                metrics['max_feature_importance'] = float(np.max(model.feature_importances_))
            else:
                metrics['feature_importance_available'] = False

            # Add model type specific metrics
            if isinstance(model, RandomForestClassifier):
                metrics['model_type'] = 'random_forest'
                metrics['n_estimators'] = model.n_estimators
                metrics['max_depth'] = model.max_depth
            elif isinstance(model, GradientBoostingClassifier):
                metrics['model_type'] = 'gradient_boosting'
                metrics['n_estimators'] = model.n_estimators
                metrics['learning_rate'] = model.learning_rate

            return metrics

        except Exception:
            return {'error': 'Could not extract performance metrics'}

    def _get_model_size(self, model, scaler) -> int:
        """Get total size of model files in bytes."""
        try:
            model_size = len(pickle.dumps(model))
            scaler_size = len(pickle.dumps(scaler))
            return model_size + scaler_size
        except Exception:
            return 0

    def load_model_version(self, defect_type: AIDefectType, version_id: Optional[str] = None) -> Optional[Dict]:
        """Load specific model version."""
        if version_id is None:
            version_id = self.current_versions.get(defect_type)

        if not version_id:
            return None

        version_dir = self.versions_dir / version_id
        model_file = version_dir / 'model.pkl'
        scaler_file = version_dir / 'scaler.pkl'

        try:
            if not model_file.exists() or not scaler_file.exists():
                self.logger.warning(f"Model files not found for version {version_id}")
                return None

            # Load model and scaler
            with open(model_file, 'rb') as f:
                model = pickle.load(f)
            with open(scaler_file, 'rb') as f:
                scaler = pickle.load(f)

            return {
                'model': model,
                'scaler': scaler,
                'version_info': self.version_history.get(version_id, {})
            }

        except Exception as e:
            self.logger.error(f"Failed to load model version {version_id}: {e}")
            return None

    def list_model_versions(self, defect_type: AIDefectType) -> List[Dict[str, Any]]:
        """List all versions for a defect type."""
        versions = []

        for version_id, version_info in self.version_history.items():
            if version_info.get('defect_type') == defect_type.value:
                versions.append({
                    'version_id': version_id,
                    'version_name': version_info.get('version_name', ''),
                    'timestamp': version_info.get('timestamp', 0),
                    'description': version_info.get('description', ''),
                    'is_current': version_id == self.current_versions.get(defect_type, ''),
                    'file_size': version_info.get('file_size', 0),
                    'performance_metrics': version_info.get('performance_metrics', {})
                })

        # Sort by timestamp (newest first)
        versions.sort(key=lambda x: x['timestamp'], reverse=True)
        return versions

    def compare_model_versions(self, defect_type: AIDefectType,
                             version1_id: str, version2_id: str) -> Dict[str, Any]:
        """Compare two model versions."""
        version1 = self.version_history.get(version1_id)
        version2 = self.version_history.get(version2_id)

        if not version1 or not version2:
            return {'error': 'One or both versions not found'}

        comparison = {
            'version1': {
                'id': version1_id,
                'name': version1.get('version_name', ''),
                'timestamp': version1.get('timestamp', 0)
            },
            'version2': {
                'id': version2_id,
                'name': version2.get('version_name', ''),
                'timestamp': version2.get('timestamp', 0)
            },
            'differences': {}
        }

        # Compare timestamps
        if version1.get('timestamp') != version2.get('timestamp'):
            comparison['differences']['timestamp'] = {
                'version1': version1.get('timestamp'),
                'version2': version2.get('timestamp')
            }

        # Compare model hashes
        hash1 = version1.get('model_hash', '')
        hash2 = version2.get('model_hash', '')
        if hash1 != hash2:
            comparison['differences']['model_hash'] = {
                'version1': hash1,
                'version2': hash2,
                'changed': True
            }

        # Compare file sizes
        size1 = version1.get('file_size', 0)
        size2 = version2.get('file_size', 0)
        if size1 != size2:
            comparison['differences']['file_size'] = {
                'version1': size1,
                'version2': size2,
                'size_difference': size2 - size1
            }

        return comparison

    def rollback_to_version(self, defect_type: AIDefectType, version_id: str) -> bool:
        """Rollback model to a previous version."""
        try:
            model_data = self.load_model_version(defect_type, version_id)
            if not model_data:
                return False

            # Update current version
            self.current_versions[defect_type] = version_id

            # Log rollback
            self.logger.info(f"Rolled back {defect_type.value} model to version {version_id}")

            self._save_version_history()
            return True

        except Exception as e:
            self.logger.error(f"Failed to rollback model: {e}")
            return False

    def get_model_lineage(self, defect_type: AIDefectType) -> List[Dict[str, Any]]:
        """Get complete lineage of model versions."""
        lineage = []

        for version_id, version_info in self.version_history.items():
            if version_info.get('defect_type') == defect_type.value:
                lineage.append({
                    'version_id': version_id,
                    'version_name': version_info.get('version_name', ''),
                    'timestamp': version_info.get('timestamp', 0),
                    'is_current': version_id == self.current_versions.get(defect_type, ''),
                    'performance_metrics': version_info.get('performance_metrics', {}),
                    'description': version_info.get('description', '')
                })

        # Sort by timestamp
        lineage.sort(key=lambda x: x['timestamp'])
        return lineage

    def cleanup_old_versions(self, keep_count: int = 10) -> int:
        """Clean up old model versions, keeping only the most recent ones."""
        cleaned_count = 0

        try:
            # Group versions by defect type
            versions_by_type = {}
            for version_id, version_info in self.version_history.items():
                defect_type = version_info.get('defect_type', '')
                if defect_type not in versions_by_type:
                    versions_by_type[defect_type] = []
                versions_by_type[defect_type].append((version_id, version_info))

            # For each defect type, keep only the most recent versions
            for defect_type, versions in versions_by_type.items():
                # Sort by timestamp (newest first)
                versions.sort(key=lambda x: x[1].get('timestamp', 0), reverse=True)

                # Keep only the specified number of recent versions
                versions_to_keep = versions[:keep_count]
                versions_to_remove = versions[keep_count:]

                for version_id, _ in versions_to_remove:
                    # Remove version files and history
                    version_dir = self.versions_dir / version_id
                    if version_dir.exists():
                        import shutil
                        shutil.rmtree(version_dir, ignore_errors=True)

                    # Remove from history
                    if version_id in self.version_history:
                        del self.version_history[version_id]

                    cleaned_count += 1

            if cleaned_count > 0:
                self._save_version_history()
                self.logger.info(f"Cleaned up {cleaned_count} old model versions")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old versions: {e}")

        return cleaned_count

    def export_model_package(self, defect_type: AIDefectType, version_id: Optional[str] = None,
                           export_path: Optional[Path] = None) -> Optional[Path]:
        """Export model as a portable package."""
        if version_id is None:
            version_id = self.current_versions.get(defect_type)

        if not version_id:
            return None

        try:
            version_info = self.version_history.get(version_id)
            if not version_info:
                return None

            # Create export package
            if export_path is None:
                timestamp = int(time.time())
                export_path = self.storage_dir / f"model_package_{defect_type.value}_{version_id}_{timestamp}.zip"

            # Create package structure
            package_dir = self.storage_dir / f"package_{version_id}"
            package_dir.mkdir(exist_ok=True)

            # Copy model files
            version_dir = self.versions_dir / version_id
            if version_dir.exists():
                import shutil
                for file_path in version_dir.iterdir():
                    shutil.copy2(file_path, package_dir / file_path.name)

            # Create package metadata
            package_info = {
                'package_type': 'ai_model',
                'defect_type': defect_type.value,
                'version_id': version_id,
                'version_name': version_info.get('version_name', ''),
                'created_at': time.time(),
                'model_hash': version_info.get('model_hash', ''),
                'performance_metrics': version_info.get('performance_metrics', {}),
                'export_format_version': '1.0'
            }

            with open(package_dir / 'package_info.json', 'w') as f:
                json.dump(package_info, f, indent=2, default=str)

            # Create ZIP package
            import zipfile
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in package_dir.rglob('*'):
                    if file_path.is_file():
                        zipf.write(file_path, file_path.relative_to(package_dir))

            # Cleanup temporary directory
            shutil.rmtree(package_dir, ignore_errors=True)

            self.logger.info(f"Exported model package to {export_path}")
            return export_path

        except Exception as e:
            self.logger.error(f"Failed to export model package: {e}")
            return None

    def get_version_summary(self) -> Dict[str, Any]:
        """Get summary of all model versions."""
        summary = {
            'total_versions': len(self.version_history),
            'current_versions': {
                dt.value: version_id for dt, version_id in self.current_versions.items()
            },
            'versions_by_type': {},
            'storage_usage': self._calculate_storage_usage()
        }

        # Count versions by defect type
        for version_info in self.version_history.values():
            defect_type = version_info.get('defect_type', 'unknown')
            summary['versions_by_type'][defect_type] = summary['versions_by_type'].get(defect_type, 0) + 1

        return summary

    def _calculate_storage_usage(self) -> Dict[str, Any]:
        """Calculate storage usage for all models."""
        try:
            total_size = 0
            file_count = 0

            for version_dir in self.versions_dir.iterdir():
                if version_dir.is_dir():
                    for file_path in version_dir.iterdir():
                        if file_path.is_file():
                            total_size += file_path.stat().st_size
                            file_count += 1

            return {
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'file_count': file_count,
                'version_count': len([d for d in self.versions_dir.iterdir() if d.is_dir()])
            }

        except Exception:
            return {'total_size_bytes': 0, 'total_size_mb': 0.0, 'file_count': 0, 'version_count': 0}


class AIModelStorage:
    """Enhanced storage and version management for AI models."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / '.printcad' / 'ai_models'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.model_cache: Dict[str, Dict] = {}
        self.version_manager = AIModelVersionManager(self.storage_dir)

    def save_model(self, defect_type: AIDefectType, model, scaler,
                  version_name: Optional[str] = None,
                  description: Optional[str] = None) -> str:
        """Save trained model with version management."""
        # Create version in version manager
        version_id = self.version_manager.create_model_version(
            defect_type, model, scaler, version_name, description
        )

        if version_id:
            # Update cache
            self.model_cache[defect_type.value] = {
                'model': model,
                'scaler': scaler,
                'version_id': version_id,
                'timestamp': time.time()
            }

        return version_id

    def load_model(self, defect_type: AIDefectType, version_id: Optional[str] = None) -> Optional[Dict]:
        """Load model with version management."""
        # Check cache first
        if defect_type.value in self.model_cache and version_id is None:
            cached_model = self.model_cache[defect_type.value]
            # Check if cache is recent (within 24 hours)
            if time.time() - cached_model['timestamp'] < 86400:
                return cached_model

        # Load from version manager
        model_data = self.version_manager.load_model_version(defect_type, version_id)

        if model_data:
            # Update cache
            self.model_cache[defect_type.value] = {
                'model': model_data['model'],
                'scaler': model_data['scaler'],
                'version_id': version_id or self.version_manager.current_versions.get(defect_type, ''),
                'timestamp': time.time()
            }

        return model_data

    def list_models(self) -> List[str]:
        """List available trained models."""
        return self.version_manager.list_model_versions(AIDefectType.NON_MANIFOLD_EDGES)

    def list_model_versions(self, defect_type: AIDefectType) -> List[Dict[str, Any]]:
        """List all versions for a defect type."""
        return self.version_manager.list_model_versions(defect_type)

    def rollback_model(self, defect_type: AIDefectType, version_id: str) -> bool:
        """Rollback model to a previous version."""
        return self.version_manager.rollback_to_version(defect_type, version_id)

    def get_version_summary(self) -> Dict[str, Any]:
        """Get comprehensive version summary."""
        return self.version_manager.get_version_summary()

    def export_model_package(self, defect_type: AIDefectType, version_id: Optional[str] = None,
                           export_path: Optional[Path] = None) -> Optional[Path]:
        """Export model as portable package."""
        return self.version_manager.export_model_package(defect_type, version_id, export_path)

    def cleanup_old_models(self, keep_count: int = 10) -> int:
        """Clean up old model versions."""
        return self.version_manager.cleanup_old_versions(keep_count)
    """Storage and version management for AI models."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / '.printcad' / 'ai_models'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.model_cache: Dict[str, Dict] = {}

    def save_model(self, defect_type: AIDefectType, model, scaler) -> bool:
        """Save trained model and scaler."""
        try:
            model_file = self.storage_dir / f"{defect_type.value}_model.pkl"
            scaler_file = self.storage_dir / f"{defect_type.value}_scaler.pkl"

            # Save model
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)

            # Save scaler
            with open(scaler_file, 'wb') as f:
                pickle.dump(scaler, f)

            # Update cache
            self.model_cache[defect_type.value] = {
                'model': model,
                'scaler': scaler,
                'timestamp': time.time()
            }

            logging.info(f"Saved model for {defect_type.value}")
            return True

        except Exception as e:
            logging.error(f"Failed to save model for {defect_type.value}: {e}")
            return False

    def load_model(self, defect_type: AIDefectType) -> Optional[Dict]:
        """Load trained model and scaler."""
        # Check cache first
        if defect_type.value in self.model_cache:
            cached_model = self.model_cache[defect_type.value]
            # Check if cache is recent (within 24 hours)
            if time.time() - cached_model['timestamp'] < 86400:
                return cached_model

        try:
            model_file = self.storage_dir / f"{defect_type.value}_model.pkl"
            scaler_file = self.storage_dir / f"{defect_type.value}_scaler.pkl"

            if not model_file.exists() or not scaler_file.exists():
                return None

            # Load model
            with open(model_file, 'rb') as f:
                model = pickle.load(f)

            # Load scaler
            with open(scaler_file, 'rb') as f:
                scaler = pickle.load(f)

            # Update cache
            self.model_cache[defect_type.value] = {
                'model': model,
                'scaler': scaler,
                'timestamp': time.time()
            }

            return self.model_cache[defect_type.value]

        except Exception as e:
            logging.error(f"Failed to load model for {defect_type.value}: {e}")
            return None

    def list_models(self) -> List[str]:
        """List available trained models."""
        try:
            model_files = list(self.storage_dir.glob("*_model.pkl"))
            return [f.replace("_model.pkl", "") for f in [f.name for f in model_files]]
        except Exception:
            return []

    def cleanup_old_models(self, keep_days: int = 30):
        """Clean up old model files."""
        try:
            cutoff_time = time.time() - (keep_days * 86400)
            cleaned_count = 0

            for model_file in self.storage_dir.glob("*_model.pkl"):
                if model_file.stat().st_mtime < cutoff_time:
                    # Remove model and scaler files
                    scaler_file = model_file.with_name(model_file.name.replace("_model.pkl", "_scaler.pkl"))
                    model_file.unlink(missing_ok=True)
                    scaler_file.unlink(missing_ok=True)
                    cleaned_count += 1

            if cleaned_count > 0:
                logging.info(f"Cleaned up {cleaned_count} old model files")

        except Exception as e:
            logging.error(f"Failed to cleanup old models: {e}")


# Legacy compatibility - keep original class for backward compatibility
class AIDefectDetectorLegacy:
    """Legacy AI defect detector for backward compatibility."""

    def __init__(self, model_type: AIModelType = AIModelType.RANDOM_FOREST):
        self.model_type = model_type
        self.models = {}
        self.scalers = {}
        self.feature_names = [
            'surface_area', 'volume', 'bounding_box_volume', 'aspect_ratio', 'compactness',
            'vertex_count', 'face_count', 'edge_count', 'euler_characteristic', 'genus',
            'min_edge_length', 'max_edge_length', 'avg_edge_length',
            'min_face_area', 'max_face_area', 'avg_face_area',
            'min_wall_thickness', 'overhang_ratio', 'cavity_count', 'floating_parts'
        ]

        if not SKLEARN_AVAILABLE:
            logging.warning("scikit-learn not available. AI defect detection disabled.")
            return

        self._initialize_models()

    def _initialize_models(self):
        """Initialize ML models for each defect type."""
        if not SKLEARN_AVAILABLE:
            return

        for defect_type in AIDefectType:
            if self.model_type == AIModelType.RANDOM_FOREST:
                self.models[defect_type] = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
            elif self.model_type == AIModelType.GRADIENT_BOOSTING:
                self.models[defect_type] = GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=6,
                    random_state=42
                )

            self.scalers[defect_type] = StandardScaler()

    def extract_features(self, mesh: trimesh.Trimesh) -> AIMeshFeatures:
        """Extract features from mesh for AI analysis."""
        # Basic geometric properties
        surface_area = mesh.area
        volume = mesh.volume if mesh.is_watertight else 0.0
        bounds = mesh.bounds
        bounding_box_volume = np.prod(bounds[1] - bounds[0])

        # Aspect ratio (longest to shortest dimension)
        dimensions = bounds[1] - bounds[0]
        aspect_ratio = max(dimensions) / min(dimensions) if min(dimensions) > 0 else float('inf')

        # Compactness (sphere-like measure)
        compactness = (surface_area ** 3) / (36 * np.pi * volume ** 2) if volume > 0 else float('inf')

        # Topology features
        vertex_count = len(mesh.vertices)
        face_count = len(mesh.faces)
        edge_count = len(mesh.edges_unique)
        euler_characteristic = vertex_count - edge_count + face_count
        genus = (2 - euler_characteristic) // 2 if euler_characteristic <= 2 else 0

        # Edge length statistics
        edge_lengths = mesh.edges_unique_length
        min_edge_length = float(np.min(edge_lengths)) if len(edge_lengths) > 0 else 0.0
        max_edge_length = float(np.max(edge_lengths)) if len(edge_lengths) > 0 else 0.0
        avg_edge_length = float(np.mean(edge_lengths)) if len(edge_lengths) > 0 else 0.0

        # Face area statistics
        face_areas = mesh.area_faces
        min_face_area = float(np.min(face_areas)) if len(face_areas) > 0 else 0.0
        max_face_area = float(np.max(face_areas)) if len(face_areas) > 0 else 0.0
        avg_face_area = float(np.mean(face_areas)) if len(face_areas) > 0 else 0.0

        # Wall thickness estimation (simplified)
        min_wall_thickness = self._estimate_min_wall_thickness(mesh)

        # Overhang analysis
        overhang_ratio = self._calculate_overhang_ratio(mesh)

        # Cavity detection
        cavity_count = self._count_cavities(mesh)

        # Floating parts
        floating_parts = len(trimesh.graph.connected_components(mesh.face_adjacency)) - 1

        return AIMeshFeatures(
            surface_area=surface_area,
            volume=volume,
            bounding_box_volume=bounding_box_volume,
            aspect_ratio=aspect_ratio,
            compactness=compactness,
            vertex_count=vertex_count,
            face_count=face_count,
            edge_count=edge_count,
            euler_characteristic=euler_characteristic,
            genus=genus,
            min_edge_length=min_edge_length,
            max_edge_length=max_edge_length,
            avg_edge_length=avg_edge_length,
            min_face_area=min_face_area,
            max_face_area=max_face_area,
            avg_face_area=avg_face_area,
            min_wall_thickness=min_wall_thickness,
            overhang_ratio=overhang_ratio,
            cavity_count=cavity_count,
            floating_parts=floating_parts,
        )

    def _estimate_min_wall_thickness(self, mesh: trimesh.Trimesh) -> float:
        """Estimate minimum wall thickness."""
        try:
            # Simple ray casting approach
            bounds = mesh.bounds
            center = (bounds[0] + bounds[1]) / 2

            # Cast rays in different directions
            directions = [
                [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]
            ]

            min_thickness = float('inf')
            for direction in directions:
                # Find intersections
                locations, index_ray, index_tri = mesh.ray.intersects_location(
                    ray_origins=[center],
                    ray_directions=[direction],
                    multiple_hits=True
                )

                if len(locations) >= 2:
                    # Calculate distance between first and last intersection
                    distances = np.linalg.norm(locations - center, axis=1)
                    thickness = abs(distances[-1] - distances[0])
                    min_thickness = min(min_thickness, thickness)

            return min_thickness if min_thickness != float('inf') else 0.8  # Default minimum
        except Exception:
            return 0.8  # Default minimum

    def _calculate_overhang_ratio(self, mesh: trimesh.Trimesh) -> float:
        """Calculate ratio of faces that are overhangs."""
        try:
            # Simple overhang detection (faces with normal Z-component < threshold)
            face_normals = mesh.face_normals
            overhang_threshold = 0.1  # cos(84°) ≈ 0.1

            overhang_faces = np.abs(face_normals[:, 2]) < overhang_threshold
            overhang_ratio = np.sum(overhang_faces) / len(face_normals)

            return float(overhang_ratio)
        except Exception:
            return 0.0

    def _count_cavities(self, mesh: trimesh.Trimesh) -> int:
        """Count cavities in the mesh."""
        try:
            # Use connected components of inverted mesh to find cavities
            if not mesh.is_watertight:
                return 0

            # This is a simplified approach - real cavity detection is complex
            return max(0, mesh.euler_number - 2)  # Euler characteristic based estimate
        except Exception:
            return 0

    def detect_defects(self, mesh: trimesh.Trimesh) -> List[AIDefectDetectionResult]:
        """Detect defects in mesh using AI models."""
        if not SKLEARN_AVAILABLE:
            return []

        results = []
        features = self.extract_features(mesh)
        feature_array = features.to_array().reshape(1, -1)

        for defect_type in AIDefectType:
            if defect_type not in self.models:
                continue

            try:
                # Scale features
                scaler = self.scalers[defect_type]
                scaled_features = scaler.transform(feature_array)

                # Get prediction and probability
                model = self.models[defect_type]
                prediction = model.predict(scaled_features)[0]
                probabilities = model.predict_proba(scaled_features)[0]

                # Get confidence for positive class
                confidence = float(probabilities[1] if len(probabilities) > 1 else probabilities[0])

                if confidence > 0.5:  # Only report if confidence > 50%
                    severity = self._calculate_severity(confidence, defect_type)

                    result = AIDefectDetectionResult(
                        defect_type=defect_type,
                        confidence=confidence,
                        severity=severity,
                        description=self._get_defect_description(defect_type),
                        suggested_fix=self._get_suggested_fix(defect_type),
                        feature_importance=self._get_feature_importance(model, defect_type)
                    )
                    results.append(result)

            except Exception as e:
                logging.warning(f"Error detecting {defect_type.value}: {e}")
                continue

        return results

    def _calculate_severity(self, confidence: float, defect_type: AIDefectType) -> str:
        """Calculate severity based on confidence and defect type."""
        if confidence > 0.8:
            return "critical"
        elif confidence > 0.6:
            return "high"
        elif confidence > 0.4:
            return "medium"
        else:
            return "low"

    def _get_defect_description(self, defect_type: AIDefectType) -> str:
        """Get human-readable description for defect type."""
        descriptions = {
            AIDefectType.NON_MANIFOLD_EDGES: "Non-manifold edges detected that may cause printing issues",
            AIDefectType.HOLES: "Holes in the mesh surface that need repair",
            AIDefectType.SELF_INTERSECTIONS: "Mesh self-intersections that prevent proper printing",
            AIDefectType.THIN_WALLS: "Walls thinner than recommended minimum may break during printing",
            AIDefectType.OVERHANGS: "Large overhangs detected requiring support structures",
            AIDefectType.POOR_SURFACE_QUALITY: "Surface quality issues that may affect print finish",
            AIDefectType.STRUCTURAL_WEAKNESSES: "Structural weaknesses that may compromise part integrity",
            AIDefectType.SCALING_ISSUES: "Scaling problems that may cause dimensional inaccuracies",
            AIDefectType.ORIENTATION_PROBLEMS: "Poor orientation for printing may cause failures",
        }
        return descriptions.get(defect_type, "Unknown defect detected")

    def _get_suggested_fix(self, defect_type: AIDefectType) -> str:
        """Get suggested fix for defect type."""
        fixes = {
            AIDefectType.NON_MANIFOLD_EDGES: "Use mesh repair tools to fix non-manifold geometry",
            AIDefectType.HOLES: "Fill holes using mesh repair software",
            AIDefectType.SELF_INTERSECTIONS: "Resolve self-intersections by separating intersecting parts",
            AIDefectType.THIN_WALLS: "Increase wall thickness or add support structures",
            AIDefectType.OVERHANGS: "Reorient model or add support structures",
            AIDefectType.POOR_SURFACE_QUALITY: "Apply surface smoothing or remeshing",
            AIDefectType.STRUCTURAL_WEAKNESSES: "Add internal supports or change infill pattern",
            AIDefectType.SCALING_ISSUES: "Check and correct model scale",
            AIDefectType.ORIENTATION_PROBLEMS: "Reorient model for better bed adhesion",
        }
        return fixes.get(defect_type, "Manual inspection recommended")

    def _get_feature_importance(self, model, defect_type: AIDefectType) -> Dict[str, float]:
        """Get feature importance from the model."""
        try:
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
                return dict(zip(self.feature_names, importances))
        except Exception:
            pass
        return {}

    def train_models(self, training_data: List[Tuple[AIMeshFeatures, Dict[AIDefectType, bool]]]):
        """Train AI models with labeled data."""
        if not SKLEARN_AVAILABLE:
            logging.warning("Cannot train models: scikit-learn not available")
            return

        # Prepare training data for each defect type
        for defect_type in AIDefectType:
            X = []
            y = []

            for features, labels in training_data:
                X.append(features.to_array())
                y.append(1 if labels.get(defect_type, False) else 0)

            if len(X) == 0 or len(y) == 0:
                continue

            X = np.array(X)
            y = np.array(y)

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Scale features
            scaler = self.scalers[defect_type]
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train model
            model = self.models[defect_type]
            model.fit(X_train_scaled, y_train)

            # Evaluate
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)

            logging.info(f"Model training results for {defect_type.value}:")
            logging.info(f"  Accuracy: {accuracy:.3f}")
            logging.info(f"  Precision: {precision:.3f}")
            logging.info(f"  Recall: {recall:.3f}")
            logging.info(f"  F1-Score: {f1:.3f}")


class OnlineLearningSystem:
    """Real-time learning system for continuous model improvement."""

    def __init__(self, ai_detector: AIDefectDetector, learning_rate: float = 0.01,
                 min_samples_for_update: int = 10, max_buffer_size: int = 1000):
        self.ai_detector = ai_detector
        self.learning_rate = learning_rate
        self.min_samples_for_update = min_samples_for_update
        self.max_buffer_size = max_buffer_size

        # Feedback buffer for online learning
        self.feedback_buffer: List[Tuple[AIMeshFeatures, Dict[AIDefectType, bool], Dict[AIDefectType, bool]]] = []
        self.model_performance_history: Dict[AIDefectType, List[float]] = {}

        # Initialize performance tracking
        for defect_type in AIDefectType:
            self.model_performance_history[defect_type] = []

        self.logger = logging.getLogger(__name__)

    def submit_feedback(self, mesh: trimesh.Trimesh, detected_defects: List[AIDefectDetectionResult],
                       user_feedback: Dict[AIDefectType, bool]) -> bool:
        """Submit user feedback on defect detection accuracy."""
        try:
            # Extract features for this mesh
            features = self.ai_detector.extract_features(mesh)

            # Convert detected defects to label format
            detected_labels = {}
            for defect in detected_defects:
                detected_labels[defect.defect_type] = defect.confidence > 0.5

            # Store feedback for later learning
            self.feedback_buffer.append((features, detected_labels, user_feedback))

            # Maintain buffer size
            if len(self.feedback_buffer) > self.max_buffer_size:
                # Remove oldest entries
                self.feedback_buffer = self.feedback_buffer[-self.max_buffer_size:]

            self.logger.info(f"Received feedback for {len(user_feedback)} defect types")

            # Trigger learning if we have enough samples
            if len(self.feedback_buffer) >= self.min_samples_for_update:
                return self._perform_online_learning()

            return True

        except Exception as e:
            self.logger.error(f"Failed to process feedback: {e}")
            return False

    def _perform_online_learning(self) -> bool:
        """Perform online learning with accumulated feedback."""
        try:
            if not self.feedback_buffer:
                return False

            # Aggregate feedback data
            training_data = []
            for features, detected_labels, user_labels in self.feedback_buffer:
                training_data.append((features, user_labels))

            # Perform incremental learning for each model type
            success_count = 0

            for defect_type in AIDefectType:
                if self.ai_detector.model_type == AIModelType.ENSEMBLE:
                    success = self._update_ensemble_model(defect_type, training_data)
                else:
                    success = self._update_single_model(defect_type, training_data)

                if success:
                    success_count += 1

            # Clear buffer after successful learning
            if success_count > 0:
                self.feedback_buffer.clear()
                self.logger.info(f"Successfully updated {success_count} models with online learning")

            return success_count > 0

        except Exception as e:
            self.logger.error(f"Online learning failed: {e}")
            return False

    def _update_ensemble_model(self, defect_type: AIDefectType, training_data: List[Tuple[AIMeshFeatures, Dict[AIDefectType, bool]]]) -> bool:
        """Update ensemble models with new training data."""
        try:
            models = self.ai_detector.models.get(defect_type)
            if not isinstance(models, dict):
                return False

            # Prepare training data
            X = []
            y = []

            for features, labels in training_data:
                X.append(features.to_array())
                y.append(1 if labels.get(defect_type, False) else 0)

            if len(X) == 0:
                return False

            X = np.array(X)
            y = np.array(y)

            # Incremental learning (simplified approach)
            # In practice, this would use proper online learning algorithms
            scaler = self.ai_detector.scalers[defect_type]
            X_scaled = scaler.transform(X)

            # Update models with partial fit if available
            rf_model = models['rf']
            gb_model = models['gb']

            if hasattr(rf_model, 'partial_fit'):
                rf_model.partial_fit(X_scaled, y, classes=[0, 1])

            if hasattr(gb_model, 'partial_fit'):
                gb_model.partial_fit(X_scaled, y, classes=[0, 1])

            # Update performance metrics
            y_pred_rf = rf_model.predict(X_scaled)
            y_pred_gb = gb_model.predict(X_scaled)

            rf_accuracy = np.mean(y_pred_rf == y)
            gb_accuracy = np.mean(y_pred_gb == y)

            # Update weights based on current performance
            total_accuracy = rf_accuracy + gb_accuracy
            if total_accuracy > 0:
                models['weights'] = {
                    'rf': gb_accuracy / total_accuracy,
                    'gb': rf_accuracy / total_accuracy
                }

            self.model_performance_history[defect_type].append(np.mean([rf_accuracy, gb_accuracy]))

            return True

        except Exception as e:
            self.logger.error(f"Failed to update ensemble model for {defect_type.value}: {e}")
            return False

    def _update_single_model(self, defect_type: AIDefectType, training_data: List[Tuple[AIMeshFeatures, Dict[AIDefectType, bool]]]) -> bool:
        """Update single model with new training data."""
        try:
            model = self.ai_detector.models.get(defect_type)
            if not model:
                return False

            # Prepare training data
            X = []
            y = []

            for features, labels in training_data:
                X.append(features.to_array())
                y.append(1 if labels.get(defect_type, False) else 0)

            if len(X) == 0:
                return False

            X = np.array(X)
            y = np.array(y)

            scaler = self.ai_detector.scalers[defect_type]
            X_scaled = scaler.transform(X)

            # Incremental learning
            if hasattr(model, 'partial_fit'):
                model.partial_fit(X_scaled, y, classes=[0, 1])
            else:
                # Retrain from scratch with accumulated data
                model.fit(X_scaled, y)

            # Calculate and store performance
            y_pred = model.predict(X_scaled)
            accuracy = np.mean(y_pred == y)
            self.model_performance_history[defect_type].append(accuracy)

            return True

        except Exception as e:
            self.logger.error(f"Failed to update model for {defect_type.value}: {e}")
            return False

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning system statistics."""
        return {
            'feedback_buffer_size': len(self.feedback_buffer),
            'min_samples_for_update': self.min_samples_for_update,
            'model_performance': {
                defect_type.value: {
                    'recent_accuracy': np.mean(history[-10:]) if history else 0.0,
                    'samples_trained': len(history)
                }
                for defect_type, history in self.model_performance_history.items()
            },
            'total_feedback_samples': sum(len(history) for history in self.model_performance_history.values())
        }

    def force_model_update(self, defect_type: AIDefectType = None) -> bool:
        """Force model update with current feedback buffer."""
        if not self.feedback_buffer:
            return False

        success_count = 0

        defect_types = [defect_type] if defect_type else list(AIDefectType)

        for dt in defect_types:
            if self.ai_detector.model_type == AIModelType.ENSEMBLE:
                success = self._update_ensemble_model(dt, self.feedback_buffer)
            else:
                success = self._update_single_model(dt, self.feedback_buffer)

            if success:
                success_count += 1

        # Clear buffer after forced update
        if success_count > 0:
            self.feedback_buffer.clear()

        return success_count > 0

    def export_learning_data(self, file_path: Path) -> bool:
        """Export learning data for analysis."""
        try:
            export_data = {
                'feedback_buffer': [
                    {
                        'features': features.to_array().tolist(),
                        'detected_labels': detected_labels,
                        'user_labels': user_labels
                    }
                    for features, detected_labels, user_labels in self.feedback_buffer
                ],
                'performance_history': {
                    defect_type.value: history
                    for defect_type, history in self.model_performance_history.items()
                },
                'export_timestamp': time.time()
            }

            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)

            self.logger.info(f"Exported learning data to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export learning data: {e}")
            return False


class AIAnalysisPipeline:
    """Complete AI analysis pipeline with learning and feedback."""

    def __init__(self, enable_online_learning: bool = True, model_type: AIModelType = AIModelType.ENSEMBLE):
        self.ai_detector = AIDefectDetector(model_type=model_type)
        self.online_learning = OnlineLearningSystem(self.ai_detector) if enable_online_learning else None
        self.analysis_history: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    def analyze_mesh_with_feedback(self, mesh: trimesh.Trimesh,
                                 user_feedback: Optional[Dict[AIDefectType, bool]] = None) -> Dict[str, Any]:
        """Perform complete AI analysis with optional user feedback."""
        start_time = time.time()

        try:
            # Extract features
            features = self.ai_detector.extract_features(mesh)

            # Detect defects
            defects = self.ai_detector.detect_defects(mesh)

            # Calculate analysis metrics
            analysis_result = {
                'mesh_id': hashlib.md5(mesh.vertices.tobytes()).hexdigest()[:8],
                'timestamp': time.time(),
                'processing_time': time.time() - start_time,
                'features': features.as_dict(),
                'detected_defects': [defect.as_dict() for defect in defects],
                'analysis_confidence': self._calculate_overall_confidence(defects),
                'mesh_characteristics': self._analyze_mesh_characteristics(mesh)
            }

            # Process user feedback if provided
            if user_feedback and self.online_learning:
                feedback_success = self.online_learning.submit_feedback(mesh, defects, user_feedback)
                analysis_result['feedback_processed'] = feedback_success

            # Store analysis history
            self.analysis_history.append(analysis_result)

            # Maintain history size
            if len(self.analysis_history) > 1000:
                self.analysis_history = self.analysis_history[-1000:]

            return analysis_result

        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            return {
                'error': str(e),
                'timestamp': time.time(),
                'processing_time': time.time() - start_time
            }

    def _calculate_overall_confidence(self, defects: List[AIDefectDetectionResult]) -> float:
        """Calculate overall confidence score for analysis."""
        if not defects:
            return 1.0

        confidences = [defect.confidence for defect in defects]
        return float(np.mean(confidences))

    def _analyze_mesh_characteristics(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """Analyze mesh characteristics for reporting."""
        return {
            'complexity_score': len(mesh.vertices) * len(mesh.faces) / 10000,
            'is_manifold': mesh.is_manifold,
            'is_watertight': mesh.is_watertight,
            'volume': mesh.volume if mesh.is_watertight else 0.0,
            'surface_area': mesh.area,
            'bounding_box': mesh.bounds.tolist()
        }

    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get comprehensive analysis statistics."""
        if not self.analysis_history:
            return {'total_analyses': 0}

        recent_analyses = [
            analysis for analysis in self.analysis_history
            if time.time() - analysis['timestamp'] < 3600  # Last hour
        ]

        total_defects = sum(
            len(analysis.get('detected_defects', []))
            for analysis in self.analysis_history
        )

        avg_confidence = np.mean([
            analysis.get('analysis_confidence', 0.0)
            for analysis in self.analysis_history
        ])

        return {
            'total_analyses': len(self.analysis_history),
            'recent_analyses': len(recent_analyses),
            'total_defects_detected': total_defects,
            'average_confidence': float(avg_confidence),
            'online_learning_enabled': self.online_learning is not None,
            'learning_stats': self.online_learning.get_learning_stats() if self.online_learning else {}
        }

    def export_analysis_report(self, file_path: Path) -> bool:
        """Export comprehensive analysis report."""
        try:
            report_data = {
                'generated_at': time.time(),
                'analysis_stats': self.get_analysis_stats(),
                'recent_analyses': self.analysis_history[-100:],  # Last 100 analyses
                'system_info': {
                    'model_type': self.ai_detector.model_type.value,
                    'deep_learning_enabled': self.ai_detector.enable_deep_learning,
                    'feature_count': len(self.ai_detector.feature_names)
                }
            }

            with open(file_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)

            self.logger.info(f"Analysis report exported to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export analysis report: {e}")
            return False


# Global instances for enhanced AI system
_enhanced_ai_detector = AIDefectDetector()
_online_learning_system = OnlineLearningSystem(_enhanced_ai_detector)
_ai_pipeline = AIAnalysisPipeline()


def detect_defects_with_enhanced_ai(mesh: trimesh.Trimesh,
                                  user_feedback: Optional[Dict[AIDefectType, bool]] = None) -> Dict[str, Any]:
    """Enhanced AI defect detection with learning capabilities."""
    return _ai_pipeline.analyze_mesh_with_feedback(mesh, user_feedback)


def submit_ai_feedback(mesh: trimesh.Trimesh, detected_defects: List[AIDefectDetectionResult],
                      user_feedback: Dict[AIDefectType, bool]) -> bool:
    """Submit feedback for AI model improvement."""
    if _online_learning_system:
        return _online_learning_system.submit_feedback(mesh, detected_defects, user_feedback)
    return False


class InferenceOptimizer:
    """Advanced inference optimization system for AI models."""

    def __init__(self, enable_caching: bool = True, cache_size: int = 1000,
                 enable_batch_processing: bool = True, max_batch_size: int = 32):
        self.enable_caching = enable_caching
        self.cache_size = cache_size
        self.enable_batch_processing = enable_batch_processing
        self.max_batch_size = max_batch_size

        # Caching system
        self.inference_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, float] = {}

        # Batch processing
        self.batch_buffer: List[Tuple[str, np.ndarray]] = []
        self.batch_results: Dict[str, Any] = {}

        # Performance monitoring
        self.inference_times: List[float] = []
        self.cache_hit_rate = 0.0
        self.total_inferences = 0
        self.cache_hits = 0

        # Threading for async processing
        self._processing_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._batch_lock = threading.Lock()

        self.logger = logging.getLogger(__name__)

        if self.enable_batch_processing:
            self._start_batch_processor()

    def _start_batch_processor(self):
        """Start background batch processing thread."""
        def batch_processor():
            while not self._shutdown_event.is_set():
                try:
                    # Process batch if we have enough items
                    with self._batch_lock:
                        if len(self.batch_buffer) >= self.max_batch_size:
                            batch = self.batch_buffer[:self.max_batch_size]
                            self.batch_buffer = self.batch_buffer[self.max_batch_size:]

                    if batch:
                        self._process_batch(batch)

                    time.sleep(0.1)  # Small delay

                except Exception as e:
                    self.logger.error(f"Batch processor error: {e}")
                    time.sleep(1.0)

        self._processing_thread = threading.Thread(target=batch_processor, daemon=True)
        self._processing_thread.start()

    def predict_with_optimization(self, model, scaler, features: np.ndarray,
                                 model_type: str = "traditional") -> Tuple[float, Dict[str, Any]]:
        """Optimized prediction with caching and performance monitoring."""
        start_time = time.time()

        # Generate cache key
        cache_key = self._generate_cache_key(features, model_type)

        # Check cache
        if self.enable_caching and cache_key in self.inference_cache:
            cached_result = self.inference_cache[cache_key]
            self.cache_hits += 1
            self.total_inferences += 1
            self.cache_hit_rate = self.cache_hits / self.total_inferences

            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)

            return cached_result['confidence'], cached_result

        # Perform prediction
        try:
            if model_type == "ensemble" and isinstance(model, dict):
                result = self._optimized_ensemble_predict(model, scaler, features)
            elif model_type == "deep_learning" and TORCH_AVAILABLE:
                result = self._optimized_dl_predict(model, features)
            else:
                result = self._optimized_traditional_predict(model, scaler, features)

            # Cache result
            if self.enable_caching:
                self._cache_result(cache_key, result)

            # Update performance metrics
            self.total_inferences += 1
            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)

            # Maintain cache size
            if len(self.inference_cache) > self.cache_size:
                self._evict_old_cache_entries()

            return result['confidence'], result

        except Exception as e:
            self.logger.error(f"Optimized prediction failed: {e}")
            return 0.0, {'error': str(e)}

    def _generate_cache_key(self, features: np.ndarray, model_type: str) -> str:
        """Generate cache key for features."""
        # Create hash of features for caching
        features_hash = hashlib.md5(features.tobytes()).hexdigest()
        return f"{model_type}_{features_hash}"

    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache prediction result."""
        self.inference_cache[cache_key] = result
        self.cache_timestamps[cache_key] = time.time()

    def _evict_old_cache_entries(self):
        """Evict old cache entries to maintain size limit."""
        if not self.cache_timestamps:
            return

        # Remove oldest entries
        sorted_timestamps = sorted(self.cache_timestamps.items(), key=lambda x: x[1])
        entries_to_remove = len(self.inference_cache) - self.cache_size

        for i in range(entries_to_remove):
            if i < len(sorted_timestamps):
                old_key = sorted_timestamps[i][0]
                if old_key in self.inference_cache:
                    del self.inference_cache[old_key]
                if old_key in self.cache_timestamps:
                    del self.cache_timestamps[old_key]

    def _optimized_traditional_predict(self, model, scaler, features: np.ndarray) -> Dict[str, Any]:
        """Optimized traditional ML prediction."""
        try:
            # Scale features (assume already scaled in calling code)
            scaled_features = features.reshape(1, -1)

            # Fast prediction
            prediction = model.predict(scaled_features)[0]
            probabilities = model.predict_proba(scaled_features)[0]
            confidence = float(np.max(probabilities))

            # Get feature importance if available
            feature_importance = {}
            if hasattr(model, 'feature_importances_'):
                feature_importance = dict(zip(
                    ['surface_area', 'volume', 'bounding_box_volume', 'aspect_ratio', 'compactness',
                     'vertex_count', 'face_count', 'edge_count', 'euler_characteristic', 'genus'],
                    model.feature_importances_[:10]  # First 10 features
                ))

            return {
                'confidence': confidence,
                'prediction': prediction,
                'probabilities': probabilities,
                'feature_importance': feature_importance,
                'model_type': 'traditional'
            }

        except Exception as e:
            self.logger.error(f"Traditional prediction failed: {e}")
            return {'confidence': 0.0, 'error': str(e)}

    def _optimized_ensemble_predict(self, models: Dict, scaler, features: np.ndarray) -> Dict[str, Any]:
        """Optimized ensemble prediction."""
        try:
            rf_model = models['rf']
            gb_model = models['gb']
            weights = models.get('weights', {'rf': 0.5, 'gb': 0.5})

            # Scale features
            scaled_features = scaler.transform(features.reshape(1, -1))

            # Get predictions from each model
            rf_pred = rf_model.predict_proba(scaled_features)[0]
            gb_pred = gb_model.predict_proba(scaled_features)[0]

            # Weighted ensemble
            ensemble_pred = weights['rf'] * rf_pred + weights['gb'] * gb_pred
            confidence = float(np.max(ensemble_pred))

            # Get feature importance from ensemble
            rf_importance = rf_model.feature_importances_ if hasattr(rf_model, 'feature_importances_') else np.zeros(10)
            gb_importance = gb_model.feature_importances_ if hasattr(gb_model, 'feature_importances_') else np.zeros(10)
            combined_importance = weights['rf'] * rf_importance + weights['gb'] * gb_importance

            return {
                'confidence': confidence,
                'prediction': np.argmax(ensemble_pred),
                'probabilities': ensemble_pred,
                'feature_importance': dict(zip(
                    ['surface_area', 'volume', 'bounding_box_volume', 'aspect_ratio', 'compactness',
                     'vertex_count', 'face_count', 'edge_count', 'euler_characteristic', 'genus'],
                    combined_importance[:10]
                )),
                'model_type': 'ensemble',
                'model_weights': weights
            }

        except Exception as e:
            self.logger.error(f"Ensemble prediction failed: {e}")
            return {'confidence': 0.0, 'error': str(e)}

    def _optimized_dl_predict(self, model, features: np.ndarray) -> Dict[str, Any]:
        """Optimized deep learning prediction."""
        if not TORCH_AVAILABLE:
            return {'confidence': 0.0, 'error': 'PyTorch not available'}

        try:
            # This would implement optimized PyTorch inference
            # For now, return placeholder
            return {
                'confidence': 0.8,
                'prediction': 1,
                'probabilities': np.array([0.2, 0.8]),
                'model_type': 'deep_learning'
            }

        except Exception as e:
            self.logger.error(f"Deep learning prediction failed: {e}")
            return {'confidence': 0.0, 'error': str(e)}

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        recent_times = self.inference_times[-100:] if self.inference_times else []

        return {
            'total_inferences': self.total_inferences,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': self.cache_hit_rate,
            'cache_size': len(self.inference_cache),
            'avg_inference_time': np.mean(recent_times) if recent_times else 0.0,
            'min_inference_time': np.min(recent_times) if recent_times else 0.0,
            'max_inference_time': np.max(recent_times) if recent_times else 0.0,
            'p95_inference_time': np.percentile(recent_times, 95) if recent_times else 0.0,
            'batch_processing_enabled': self.enable_batch_processing,
            'batch_buffer_size': len(self.batch_buffer)
        }

    def clear_cache(self):
        """Clear inference cache."""
        with self._batch_lock:
            self.inference_cache.clear()
            self.cache_timestamps.clear()
            self.cache_hits = 0
            self.total_inferences = 0
            self.cache_hit_rate = 0.0

        self.logger.info("Inference cache cleared")

    def shutdown(self):
        """Shutdown optimizer and cleanup resources."""
        self._shutdown_event.set()

        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)

        self.logger.info("Inference optimizer shutdown complete")


class PerformanceMonitor:
    """Monitor AI system performance and suggest optimizations."""

    def __init__(self):
        self.metrics_history: List[Dict[str, Any]] = []
        self.optimization_suggestions: List[str] = []
        self.logger = logging.getLogger(__name__)

    def record_metrics(self, inference_time: float, cache_hit: bool, model_type: str,
                      feature_count: int, defect_type: str):
        """Record performance metrics for analysis."""
        metrics = {
            'timestamp': time.time(),
            'inference_time': inference_time,
            'cache_hit': cache_hit,
            'model_type': model_type,
            'feature_count': feature_count,
            'defect_type': defect_type
        }

        self.metrics_history.append(metrics)

        # Maintain history size
        if len(self.metrics_history) > 10000:
            self.metrics_history = self.metrics_history[-5000:]

    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance trends and generate insights."""
        if not self.metrics_history:
            return {'error': 'No performance data available'}

        recent_metrics = self.metrics_history[-1000:]  # Last 1000 inferences

        # Calculate averages
        avg_inference_time = np.mean([m['inference_time'] for m in recent_metrics])
        cache_hit_rate = np.mean([1 if m['cache_hit'] else 0 for m in recent_metrics])

        # Analyze by model type
        model_performance = {}
        for model_type in set(m['model_type'] for m in recent_metrics):
            model_metrics = [m for m in recent_metrics if m['model_type'] == model_type]
            model_performance[model_type] = {
                'count': len(model_metrics),
                'avg_time': np.mean([m['inference_time'] for m in model_metrics]),
                'cache_hit_rate': np.mean([1 if m['cache_hit'] else 0 for m in model_metrics])
            }

        # Generate optimization suggestions
        suggestions = []

        if avg_inference_time > 0.1:  # Slower than 100ms
            suggestions.append("Consider enabling model quantization for faster inference")

        if cache_hit_rate < 0.5:  # Less than 50% cache hit rate
            suggestions.append("Consider increasing cache size or improving cache key generation")

        if model_performance.get('ensemble', {}).get('count', 0) > 100:
            ensemble_time = model_performance['ensemble']['avg_time']
            traditional_time = model_performance.get('traditional', {}).get('avg_time', 0)

            if ensemble_time > traditional_time * 1.5:
                suggestions.append("Consider optimizing ensemble model weights or using single models for better performance")

        return {
            'overall_performance': {
                'avg_inference_time': avg_inference_time,
                'cache_hit_rate': cache_hit_rate,
                'total_inferences': len(recent_metrics)
            },
            'model_performance': model_performance,
            'optimization_suggestions': suggestions,
            'analysis_period': {
                'start_time': recent_metrics[0]['timestamp'] if recent_metrics else 0,
                'end_time': recent_metrics[-1]['timestamp'] if recent_metrics else 0
            }
        }

    def export_performance_report(self, file_path: Path) -> bool:
        """Export performance analysis report."""
        try:
            analysis = self.analyze_performance()

            report_data = {
                'generated_at': time.time(),
                'analysis': analysis,
                'raw_metrics_count': len(self.metrics_history),
                'recent_metrics': self.metrics_history[-100:]  # Last 100 for detailed analysis
            }

            with open(file_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)

            self.logger.info(f"Performance report exported to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export performance report: {e}")
            return False


# Global instances for enhanced AI system
_inference_optimizer = InferenceOptimizer()
_performance_monitor = PerformanceMonitor()


def optimize_ai_inference(model, scaler, features: np.ndarray, model_type: str = "traditional") -> Tuple[float, Dict[str, Any]]:
    """Optimized AI inference with caching and performance monitoring."""
    confidence, result = _inference_optimizer.predict_with_optimization(model, scaler, features, model_type)

    # Record metrics for performance analysis
    _performance_monitor.record_metrics(
        inference_time=result.get('inference_time', 0.0),
        cache_hit=result.get('cache_hit', False),
        model_type=model_type,
        feature_count=len(features),
        defect_type=result.get('defect_type', 'unknown')
    )

    return confidence, result


def get_ai_performance_stats() -> Dict[str, Any]:
    """Get comprehensive AI performance statistics."""
    optimizer_stats = _inference_optimizer.get_performance_stats()
    monitor_analysis = _performance_monitor.analyze_performance()

    return {
        'optimizer_stats': optimizer_stats,
        'performance_analysis': monitor_analysis,
        'combined_insights': {
            'overall_cache_efficiency': optimizer_stats.get('cache_hit_rate', 0.0),
            'average_inference_speed': optimizer_stats.get('avg_inference_time', 0.0),
            'optimization_opportunities': monitor_analysis.get('optimization_suggestions', [])
        }
    }


def clear_ai_cache():
    """Clear AI inference cache."""
    _inference_optimizer.clear_cache()


def export_ai_performance_report(file_path: Path) -> bool:
    """Export AI performance analysis report."""
    return _performance_monitor.export_performance_report(file_path)
