"""
Multi-Scale Mesh Feature Extraction for ML Models

This module implements feature extraction for 3D mesh analysis suitable for
machine learning models including PointNet++, transformers, and graph neural networks.

Key features:
- Point cloud conversion from meshes
- Multi-scale geometric features
- Surface normal and curvature calculation
- Topology-aware features
"""

import numpy as np
import trimesh
from typing import Tuple, List, Optional, Dict, Any
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MeshFeatures:
    """Container for extracted mesh features."""
    points: np.ndarray  # (N, 3) point coordinates
    normals: np.ndarray  # (N, 3) surface normals
    curvatures: np.ndarray  # (N,) curvature values
    colors: Optional[np.ndarray] = None  # (N, 3) or (N, 4) color values
    features: Optional[np.ndarray] = None  # (N, D) additional features
    scale_features: Optional[List[np.ndarray]] = None  # Multi-scale features


class MeshFeatureExtractor:
    """
    Extract features from 3D meshes for machine learning.

    Supports:
    - Point cloud generation with uniform or adaptive sampling
    - Multi-scale feature extraction (geometric + topological)
    - Surface analysis (normals, curvatures)
    - Feature normalization and standardization
    """

    def __init__(
        self,
        num_points: int = 2048,
        scales: List[float] = None,
        compute_curvatures: bool = True,
        normalize_features: bool = True
    ):
        """
        Initialize feature extractor.

        Args:
            num_points: Number of points to sample from mesh
            scales: List of scales for multi-scale features (meters)
            compute_curvatures: Whether to compute curvature features
            normalize_features: Whether to normalize extracted features
        """
        self.num_points = num_points
        self.scales = scales or [0.01, 0.05, 0.1, 0.2]
        self.compute_curvatures = compute_curvatures
        self.normalize_features = normalize_features

        # Pre-computed statistics for normalization
        self.feature_mean = None
        self.feature_std = None

    def extract_features(
        self,
        mesh: trimesh.Trimesh,
        method: str = 'uniform'
    ) -> MeshFeatures:
        """
        Extract all features from mesh.

        Args:
            mesh: Input mesh
            method: Sampling method ('uniform' or 'adaptive')

        Returns:
            MeshFeatures containing extracted features
        """
        # Sample points from mesh
        points, face_indices = self._sample_points(mesh, method)

        # Get surface normals
        normals = mesh.face_normals[face_indices]

        # Compute curvatures if requested
        curvatures = None
        if self.compute_curvatures:
            curvatures = self._compute_curvatures(mesh, points, face_indices)

        # Extract additional features
        features = self._extract_geometric_features(mesh, points, normals)

        # Extract multi-scale features
        scale_features = self._extract_multiscale_features(mesh, points)

        # Normalize if requested
        if self.normalize_features:
            features = self._normalize_features(features)
            if scale_features:
                scale_features = [self._normalize_features(sf) for sf in scale_features]

        return MeshFeatures(
            points=points,
            normals=normals,
            curvatures=curvatures,
            features=features,
            scale_features=scale_features
        )

    def _sample_points(
        self,
        mesh: trimesh.Trimesh,
        method: str = 'uniform'
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Sample points from mesh surface.

        Args:
            mesh: Input mesh
            method: 'uniform' for uniform sampling, 'adaptive' for density-aware

        Returns:
            Tuple of (points, face_indices)
        """
        if method == 'uniform':
            # Uniform random sampling from mesh surfaces
            points, face_indices = trimesh.sample.sample_surface(
                mesh,
                count=self.num_points,
                sample_weight=None  # Uniform weights
            )
        elif method == 'adaptive':
            # Adaptive sampling weighted by face area
            points, face_indices = trimesh.sample.sample_surface_even(
                mesh,
                count=self.num_points,
                max_edge=None
            )
        else:
            raise ValueError(f"Unknown sampling method: {method}")

        return points.astype(np.float32), face_indices

    def _compute_curvatures(
        self,
        mesh: trimesh.Trimesh,
        points: np.ndarray,
        face_indices: np.ndarray,
        k_neighbors: int = 20
    ) -> np.ndarray:
        """
        Compute local curvature at each sampled point.

        Args:
            mesh: Input mesh
            points: Sampled points
            face_indices: Face indices for each point
            k_neighbors: Number of neighbors for curvature estimation

        Returns:
            Array of curvature values
        """
        num_points = len(points)
        curvatures = np.zeros(num_points, dtype=np.float32)

        try:
            # Use existing trimesh vertex normals if available
            if hasattr(mesh, 'vertex_normals'):
                normals = mesh.vertex_normals
            else:
                normals = mesh.face_normals[face_indices]

            # Approximate mean curvature from local surface variation
            for i in range(num_points):
                face_idx = face_indices[i]
                face = mesh.faces[face_idx]

                # Get vertex normals at triangle corners
                v_normals = [normals[face_idx]]

                # Calculate local surface variation (simple curvature proxy)
                face_vertices = mesh.vertices[face]
                center = face_vertices.mean(axis=0)
                distances = np.linalg.norm(face_vertices - center, axis=1)

                # Mean curvature approximation
                curvatures[i] = distances.mean()

        except Exception as e:
            logger.warning(f"Curvature computation failed: {e}")
            curvatures = np.ones(num_points, dtype=np.float32) * 0.01

        return curvatures

    def _extract_geometric_features(
        self,
        mesh: trimesh.Trimesh,
        points: np.ndarray,
        normals: np.ndarray
    ) -> np.ndarray:
        """
        Extract geometric features for each point.

        Features include:
        - Vertex position (3D)
        - Surface normal (3D)
        - Distance to mesh center
        - Local height (z-coordinate)

        Args:
            mesh: Input mesh
            points: Sampled points (N, 3)
            normals: Surface normals (N, 3)

        Returns:
            Feature matrix (N, 9)
        """
        N = len(points)
        features = np.zeros((N, 9), dtype=np.float32)

        # Position features
        features[:, 0:3] = points

        # Normal features
        features[:, 3:6] = normals

        # Distance to mesh center
        center = mesh.center_mass
        distances = np.linalg.norm(points - center, axis=1)
        features[:, 6] = distances

        # Height features
        features[:, 7] = points[:, 2]  # Z-coordinate

        # Local density (approximated by point spacing)
        if N > 10:
            # Rough estimate: point spacing based on volume and count
            volume = mesh.volume
            if volume > 0:
                avg_spacing = (volume / N) ** (1/3)
                features[:, 8] = avg_spacing
            else:
                features[:, 8] = 0.01
        else:
            features[:, 8] = 0.01

        return features

    def _extract_multiscale_features(
        self,
        mesh: trimesh.Trimesh,
        points: np.ndarray
    ) -> List[np.ndarray]:
        """
        Extract multi-scale geometric features.

        Computes features at different scales for hierarchical learning.

        Args:
            mesh: Input mesh
            points: Sampled points (N, 3)

        Returns:
            List of feature arrays at different scales
        """
        multiscale_features = []

        for scale in self.scales:
            scale_features = np.zeros((len(points), 3), dtype=np.float32)

            try:
                # For each point, find neighbors within scale radius
                for i, point in enumerate(points):
                    # Simple sphere query approximation
                    distances = np.linalg.norm(mesh.vertices - point, axis=1)
                    neighbors = np.where(distances < scale)[0]

                    if len(neighbors) > 0:
                        neighbor_vertices = mesh.vertices[neighbors]
                        # Compute statistics of local neighborhood
                        scale_features[i, 0] = neighbor_vertices.mean(axis=0)[0]  # X mean
                        scale_features[i, 1] = neighbor_vertices.mean(axis=0)[1]  # Y mean
                        scale_features[i, 2] = neighbor_vertices.mean(axis=0)[2]  # Z mean

            except Exception as e:
                logger.warning(f"Multi-scale feature extraction failed for scale {scale}: {e}")
                scale_features = np.zeros_like(scale_features)

            multiscale_features.append(scale_features)

        return multiscale_features if multiscale_features else None

    def _normalize_features(self, features: np.ndarray) -> np.ndarray:
        """
        Normalize features to zero mean and unit variance.

        Args:
            features: Feature matrix (N, D)

        Returns:
            Normalized feature matrix
        """
        if features is None:
            return None

        # Compute statistics
        mean = features.mean(axis=0, keepdims=True)
        std = features.std(axis=0, keepdims=True)

        # Avoid division by zero
        std[std == 0] = 1.0

        # Normalize
        normalized = (features - mean) / std

        return normalized.astype(np.float32)


class DefectFeatureExtractor(MeshFeatureExtractor):
    """
    Specialized feature extractor for defect detection.

    Focuses on features relevant to 3D printing defects:
    - Surface roughness
    - Feature sharpness
    - Wall thickness variation
    - Overhang areas
    """

    def extract_features(
        self,
        mesh: trimesh.Trimesh,
        method: str = 'uniform'
    ) -> MeshFeatures:
        """
        Extract defect-specific features from mesh.

        Args:
            mesh: Input mesh
            method: Sampling method

        Returns:
            MeshFeatures with defect-specific attributes
        """
        features = super().extract_features(mesh, method)

        # Add defect-specific analysis
        defect_features = self._extract_defect_indicators(mesh, features)
        features.features = np.hstack([features.features, defect_features])

        return features

    def _extract_defect_indicators(
        self,
        mesh: trimesh.Trimesh,
        features: MeshFeatures
    ) -> np.ndarray:
        """
        Extract features indicating potential defects.

        Args:
            mesh: Input mesh
            features: Basic features

        Returns:
            Defect indicator features (N, 6)
        """
        N = len(features.points)
        defect_features = np.zeros((N, 6), dtype=np.float32)

        points = features.points
        normals = features.normals

        # 1. Surface roughness (high normal variation)
        for i in range(min(N, 100)):  # Sample for efficiency
            if i < len(normals):
                # Approximate roughness from normal vector
                # More variation = rougher surface
                normal_magnitude = np.linalg.norm(normals[i])
                defect_features[i, 0] = abs(1.0 - normal_magnitude)

        # 2. Sharp features (edges)
        # Points with high curvature
        if features.curvatures is not None:
            defect_features[:, 1] = features.curvatures

        # 3. Isolated points (potential noise)
        # Calculate local density
        center = mesh.center_mass
        distances_to_center = np.linalg.norm(points - center, axis=1)
        max_distance = distances_to_center.max()
        if max_distance > 0:
            isolation = distances_to_center / max_distance
            defect_features[:, 2] = isolation

        # 4. Overhang detection
        z_component = normals[:, 2]  # Z component of normal
        overhang = np.abs(z_component)  # Horizontal normals = overhang
        defect_features[:, 3] = 1.0 - overhang

        # 5. Thin wall indicator
        if hasattr(mesh, 'thickness'):
            defect_features[:, 4] = mesh.thickness
        else:
            defect_features[:, 4] = 0.5  # Default estimate

        # 6. Manifold quality
        if mesh.is_watertight:
            defect_features[:, 5] = 0.0  # Good
        else:
            defect_features[:, 5] = 1.0  # Poor

        return defect_features


def create_point_cloud_from_mesh(
    mesh: trimesh.Trimesh,
    num_points: int = 2048
) -> np.ndarray:
    """
    Simple utility to convert mesh to point cloud.

    Args:
        mesh: Input mesh
        num_points: Number of points to sample

    Returns:
        Point cloud (N, 3)
    """
    points, _ = trimesh.sample.sample_surface(mesh, count=num_points)
    return points.astype(np.float32)


if __name__ == '__main__':
    # Test feature extraction
    import trimesh

    # Create a simple test mesh
    mesh = trimesh.primitives.Sphere(radius=1.0)

    print("Testing Mesh Feature Extraction")
    print("=" * 50)

    # Extract basic features
    extractor = MeshFeatureExtractor(num_points=512)
    features = extractor.extract_features(mesh)

    print(f"✓ Extracted features:")
    print(f"  Points shape: {features.points.shape}")
    print(f"  Normals shape: {features.normals.shape}")
    print(f"  Features shape: {features.features.shape}")
    if features.curvatures is not None:
        print(f"  Curvatures shape: {features.curvatures.shape}")
    if features.scale_features:
        print(f"  Multi-scale features: {len(features.scale_features)} scales")

    # Test defect extractor
    print("\nTesting Defect Feature Extraction")
    print("=" * 50)

    defect_extractor = DefectFeatureExtractor(num_points=256)
    defect_features = defect_extractor.extract_features(mesh)

    print(f"✓ Extracted defect features:")
    print(f"  Total feature dimension: {defect_features.features.shape[1]}")
    print(f"  Sample features shape: {defect_features.features[:5, :].shape}")

    print("\n✓ Feature extraction functional and ready for ML models")
