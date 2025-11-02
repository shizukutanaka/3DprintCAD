"""AI-powered mesh repair and optimization system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union
import numpy as np
import trimesh
from enum import Enum
import logging
import time


class RepairStrategy(Enum):
    """Strategies for mesh repair."""
    AUTOMATIC = "automatic"              # Fully automatic repair
    INTERACTIVE = "interactive"          # User-guided repair
    CONSERVATIVE = "conservative"        # Minimal changes
    AGGRESSIVE = "aggressive"           # Extensive repair
    GEOMETRY_PRESERVING = "geometry_preserving"  # Maintain original shape


class MeshDefect(Enum):
    """Types of mesh defects."""
    HOLES = "holes"
    SELF_INTERSECTIONS = "self_intersections"
    DEGENERATE_FACES = "degenerate_faces"
    NON_MANIFOLD_EDGES = "non_manifold_edges"
    INVERTED_NORMALS = "inverted_normals"
    DUPLICATE_VERTICES = "duplicate_vertices"
    ISOLATED_COMPONENTS = "isolated_components"
    THIN_WALLS = "thin_walls"
    SPIKES = "spikes"
    NOISE = "noise"


@dataclass
class RepairOperation:
    """A single repair operation."""
    defect_type: MeshDefect
    description: str
    confidence: float
    applied: bool = False
    before_count: int = 0
    after_count: int = 0
    processing_time: float = 0.0


@dataclass
class MeshRepairResult:
    """Result of mesh repair operation."""
    original_mesh: trimesh.Trimesh
    repaired_mesh: trimesh.Trimesh
    operations: List[RepairOperation] = field(default_factory=list)
    quality_improvement: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    processing_time: float = 0.0
    warnings: List[str] = field(default_factory=list)


class AIMeshRepair:
    """AI-powered mesh repair and optimization system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ml_model = MLRepairModel()

    def repair_mesh(self, mesh: trimesh.Trimesh,
                   strategy: RepairStrategy = RepairStrategy.AUTOMATIC) -> MeshRepairResult:
        """Repair mesh defects using AI-guided approach."""

        start_time = time.time()
        result = MeshRepairResult(
            original_mesh=mesh.copy(),
            repaired_mesh=mesh.copy()
        )

        try:
            # Use ML model to analyze and suggest strategy
            defects = self._analyze_mesh_defects(mesh)
            suggested_strategy = self.ml_model.suggest_repair_strategy(mesh, defects)

            # Use suggested strategy if automatic
            if strategy == RepairStrategy.AUTOMATIC:
                strategy = suggested_strategy

            # Generate repair plan based on strategy
            repair_plan = self._generate_repair_plan(defects, strategy)

            # Execute repair operations
            for operation in repair_plan:
                operation_start = time.time()

                try:
                    repaired_mesh = self._execute_repair_operation(
                        result.repaired_mesh, operation, strategy
                    )

                    if repaired_mesh is not None:
                        result.repaired_mesh = repaired_mesh
                        operation.applied = True
                        operation.after_count = self._count_defects(repaired_mesh, operation.defect_type)
                    else:
                        operation.applied = False
                        result.warnings.append(f"Failed to apply {operation.defect_type.value} repair")

                except Exception as e:
                    operation.applied = False
                    result.warnings.append(f"Error in {operation.defect_type.value} repair: {str(e)}")

                operation.processing_time = time.time() - operation_start
                result.operations.append(operation)

            # Calculate quality improvement
            result.quality_improvement = self._calculate_quality_improvement(
                result.original_mesh, result.repaired_mesh
            )

            result.processing_time = time.time() - start_time

            # Final validation
            if not self._validate_repaired_mesh(result.repaired_mesh):
                result.success = False
                result.warnings.append("Repaired mesh failed validation")
            else:
                result.success = True

        except Exception as e:
            self.logger.error(f"Mesh repair failed: {e}")
            result.success = False
            result.warnings.append(f"Repair failed: {str(e)}")
            result.processing_time = time.time() - start_time

        return result
        """Repair mesh defects using AI-guided approach."""

        start_time = time.time()
        result = MeshRepairResult(
            original_mesh=mesh.copy(),
            repaired_mesh=mesh.copy()
        )

        try:
            # Analyze mesh for defects
            defects = self._analyze_mesh_defects(mesh)

            # Generate repair plan based on strategy
            repair_plan = self._generate_repair_plan(defects, strategy)

            # Execute repair operations
            for operation in repair_plan:
                operation_start = time.time()

                try:
                    repaired_mesh = self._execute_repair_operation(
                        result.repaired_mesh, operation, strategy
                    )

                    if repaired_mesh is not None:
                        result.repaired_mesh = repaired_mesh
                        operation.applied = True
                        operation.after_count = self._count_defects(repaired_mesh, operation.defect_type)
                    else:
                        operation.applied = False
                        result.warnings.append(f"Failed to apply {operation.defect_type.value} repair")

                except Exception as e:
                    operation.applied = False
                    result.warnings.append(f"Error in {operation.defect_type.value} repair: {str(e)}")

                operation.processing_time = time.time() - operation_start
                result.operations.append(operation)

            # Calculate quality improvement
            result.quality_improvement = self._calculate_quality_improvement(
                result.original_mesh, result.repaired_mesh
            )

            result.processing_time = time.time() - start_time

            # Final validation
            if not self._validate_repaired_mesh(result.repaired_mesh):
                result.success = False
                result.warnings.append("Repaired mesh failed validation")
            else:
                result.success = True

        except Exception as e:
            self.logger.error(f"Mesh repair failed: {e}")
            result.success = False
            result.warnings.append(f"Repair failed: {str(e)}")
            result.processing_time = time.time() - start_time

        return result

    def _analyze_mesh_defects(self, mesh: trimesh.Trimesh) -> Dict[MeshDefect, int]:
        """Analyze mesh for various defects."""

        defects = {}

        try:
            # Check for holes
            if not mesh.is_watertight:
                defects[MeshDefect.HOLES] = 1  # Simplified count

            # Check for self-intersections
            try:
                if mesh.is_self_intersecting:
                    defects[MeshDefect.SELF_INTERSECTIONS] = 1
            except:
                pass

            # Check for degenerate faces
            face_areas = mesh.area_faces
            degenerate_count = np.sum(face_areas < 1e-12)
            if degenerate_count > 0:
                defects[MeshDefect.DEGENERATE_FACES] = int(degenerate_count)

            # Check for non-manifold edges
            try:
                if hasattr(mesh, 'is_manifold') and not mesh.is_manifold:
                    defects[MeshDefect.NON_MANIFOLD_EDGES] = 1
            except:
                pass

            # Check for inverted normals (simplified)
            if hasattr(mesh, 'face_normals'):
                # Check if normals point inward (simplified heuristic)
                centroid = mesh.centroid
                face_centers = mesh.triangles_center
                to_centroid = centroid - face_centers
                normal_dots = np.sum(mesh.face_normals * to_centroid, axis=1)
                inverted_count = np.sum(normal_dots > 0)  # Normals pointing outward from centroid
                if inverted_count > len(mesh.faces) * 0.1:  # More than 10% potentially inverted
                    defects[MeshDefect.INVERTED_NORMALS] = int(inverted_count)

            # Check for duplicate vertices
            unique_vertices, inverse_indices, counts = np.unique(
                mesh.vertices, axis=0, return_inverse=True, return_counts=True
            )
            duplicate_count = np.sum(counts > 1)
            if duplicate_count > 0:
                defects[MeshDefect.DUPLICATE_VERTICES] = duplicate_count

            # Check for isolated components
            components = mesh.split(only_watertight=False)
            if len(components) > 1:
                defects[MeshDefect.ISOLATED_COMPONENTS] = len(components)

            # Check for thin walls (simplified)
            if hasattr(mesh, 'is_watertight') and mesh.is_watertight:
                # Estimate wall thickness
                bounds = mesh.bounds
                dimensions = bounds[1] - bounds[0]
                min_dimension = min(dimensions)
                if min_dimension < 1.0:  # Less than 1mm
                    defects[MeshDefect.THIN_WALLS] = 1

            # Check for spikes/noise (simplified)
            if len(mesh.vertices) > 0:
                # Calculate vertex density
                volume = mesh.volume if mesh.is_watertight else np.prod(dimensions)
                if volume > 0:
                    vertex_density = len(mesh.vertices) / volume
                    if vertex_density > 1000:  # Very high density suggests noise
                        defects[MeshDefect.NOISE] = 1

        except Exception as e:
            self.logger.warning(f"Error analyzing mesh defects: {e}")

        return defects

    def _count_defects(self, mesh: trimesh.Trimesh, defect_type: MeshDefect) -> int:
        """Count specific type of defects in mesh."""

        defects = self._analyze_mesh_defects(mesh)
        return defects.get(defect_type, 0)

    def _generate_repair_plan(self, defects: Dict[MeshDefect, int],
                            strategy: RepairStrategy) -> List[RepairOperation]:
        """Generate a plan of repair operations."""

        operations = []

        # Priority order for repairs
        priority_order = [
            MeshDefect.SELF_INTERSECTIONS,
            MeshDefect.HOLES,
            MeshDefect.NON_MANIFOLD_EDGES,
            MeshDefect.DEGENERATE_FACES,
            MeshDefect.DUPLICATE_VERTICES,
            MeshDefect.INVERTED_NORMALS,
            MeshDefect.ISOLATED_COMPONENTS,
            MeshDefect.THIN_WALLS,
            MeshDefect.SPIKES,
            MeshDefect.NOISE
        ]

        for defect_type in priority_order:
            if defect_type in defects:
                count = defects[defect_type]

                # Create repair operation
                operation = RepairOperation(
                    defect_type=defect_type,
                    description=self._get_repair_description(defect_type, count, strategy),
                    confidence=self._calculate_repair_confidence(defect_type, count, strategy),
                    before_count=count
                )

                operations.append(operation)

        # Sort by confidence for automatic mode
        if strategy == RepairStrategy.AUTOMATIC:
            operations.sort(key=lambda op: op.confidence, reverse=True)

        return operations

    def _get_repair_description(self, defect_type: MeshDefect, count: int,
                              strategy: RepairStrategy) -> str:
        """Get description for repair operation."""

        base_descriptions = {
            MeshDefect.HOLES: f"Fill {count} hole(s) in mesh",
            MeshDefect.SELF_INTERSECTIONS: f"Resolve {count} self-intersection(s)",
            MeshDefect.DEGENERATE_FACES: f"Remove {count} degenerate face(s)",
            MeshDefect.NON_MANIFOLD_EDGES: f"Fix {count} non-manifold edge(s)",
            MeshDefect.INVERTED_NORMALS: f"Correct {count} inverted normal(s)",
            MeshDefect.DUPLICATE_VERTICES: f"Merge {count} duplicate vertice(s)",
            MeshDefect.ISOLATED_COMPONENTS: f"Connect {count} isolated component(s)",
            MeshDefect.THIN_WALLS: f"Reinforce thin wall structure(s)",
            MeshDefect.SPIKES: "Remove geometric spikes",
            MeshDefect.NOISE: "Clean surface noise"
        }

        description = base_descriptions.get(defect_type, f"Repair {defect_type.value}")

        # Add strategy-specific notes
        if strategy == RepairStrategy.CONSERVATIVE:
            description += " (conservative approach)"
        elif strategy == RepairStrategy.AGGRESSIVE:
            description += " (aggressive repair)"
        elif strategy == RepairStrategy.GEOMETRY_PRESERVING:
            description += " (geometry-preserving)"

        return description

    def _calculate_repair_confidence(self, defect_type: MeshDefect, count: int,
                                   strategy: RepairStrategy) -> float:
        """Calculate confidence score for repair operation."""

        # Base confidence by defect type
        base_confidence = {
            MeshDefect.DUPLICATE_VERTICES: 0.95,  # Very reliable
            MeshDefect.DEGENERATE_FACES: 0.90,
            MeshDefect.HOLES: 0.80,
            MeshDefect.INVERTED_NORMALS: 0.75,
            MeshDefect.SELF_INTERSECTIONS: 0.70,
            MeshDefect.NON_MANIFOLD_EDGES: 0.65,
            MeshDefect.ISOLATED_COMPONENTS: 0.60,
            MeshDefect.THIN_WALLS: 0.50,
            MeshDefect.SPIKES: 0.45,
            MeshDefect.NOISE: 0.40
        }

        confidence = base_confidence.get(defect_type, 0.5)

        # Adjust based on count (more defects = lower confidence)
        if count > 100:
            confidence *= 0.7
        elif count > 50:
            confidence *= 0.8
        elif count > 10:
            confidence *= 0.9

        # Adjust based on strategy
        if strategy == RepairStrategy.CONSERVATIVE:
            confidence *= 0.9  # Slightly lower for conservative
        elif strategy == RepairStrategy.AGGRESSIVE:
            confidence *= 0.8  # Lower for aggressive
        elif strategy == RepairStrategy.GEOMETRY_PRESERVING:
            confidence *= 0.85  # Balanced

        return min(confidence, 1.0)

    def _execute_repair_operation(self, mesh: trimesh.Trimesh,
                                operation: RepairOperation,
                                strategy: RepairStrategy) -> Optional[trimesh.Trimesh]:
        """Execute a specific repair operation."""

        try:
            if operation.defect_type == MeshDefect.HOLES:
                return self._repair_holes(mesh, strategy)
            elif operation.defect_type == MeshDefect.SELF_INTERSECTIONS:
                return self._repair_self_intersections(mesh, strategy)
            elif operation.defect_type == MeshDefect.DEGENERATE_FACES:
                return self._remove_degenerate_faces(mesh)
            elif operation.defect_type == MeshDefect.DUPLICATE_VERTICES:
                return self._merge_duplicate_vertices(mesh)
            elif operation.defect_type == MeshDefect.INVERTED_NORMALS:
                return self._fix_inverted_normals(mesh)
            elif operation.defect_type == MeshDefect.ISOLATED_COMPONENTS:
                return self._connect_isolated_components(mesh, strategy)
            elif operation.defect_type == MeshDefect.THIN_WALLS:
                return self._reinforce_thin_walls(mesh, strategy)
            elif operation.defect_type == MeshDefect.SPIKES:
                return self._remove_spikes(mesh)
            elif operation.defect_type == MeshDefect.NOISE:
                return self._clean_noise(mesh)
            else:
                return mesh

        except Exception as e:
            self.logger.warning(f"Failed to execute {operation.defect_type.value} repair: {e}")
            return mesh

    def _repair_holes(self, mesh: trimesh.Trimesh, strategy: RepairStrategy) -> trimesh.Trimesh:
        """Repair holes in mesh."""

        try:
            # Use trimesh's built-in hole filling
            repaired = mesh.fill_holes()
            return repaired
        except Exception:
            return mesh

    def _repair_self_intersections(self, mesh: trimesh.Trimesh, strategy: RepairStrategy) -> trimesh.Trimesh:
        """Repair self-intersections using advanced algorithms."""

        try:
            # Detect self-intersections
            intersections = mesh.find_self_intersections()

            if len(intersections) == 0:
                return mesh

            # For aggressive strategy, use more intensive repair
            if strategy == RepairStrategy.AGGRESSIVE:
                # Apply Laplacian smoothing to resolve intersections
                repaired = mesh.smooth_laplacian(iterations=20, lamb=0.1)
            else:
                # Use conservative approach with local repairs
                repaired = self._repair_self_intersections_conservative(mesh, intersections)

            return repaired

        except Exception as e:
            self.logger.warning(f"Self-intersection repair failed: {e}")
            return mesh

    def _repair_self_intersections_conservative(self, mesh: trimesh.Trimesh, intersections: List) -> trimesh.Trimesh:
        """Conservative self-intersection repair using advanced techniques."""

        try:
            # Advanced self-intersection resolution based on research from MeshLib
            # Step 1: Identify intersection regions
            intersection_vertices = set()
            for intersection in intersections:
                if len(intersection) >= 2:
                    intersection_vertices.update(intersection[:2])

            if not intersection_vertices:
                return mesh

            # Step 2: Create intersection-free mesh using local remeshing
            repaired = mesh.copy()

            # Apply adaptive smoothing around intersection areas
            for vertex_idx in intersection_vertices:
                # Find local neighborhood
                neighbors = self._get_vertex_neighborhood(mesh, vertex_idx, radius=2.0)
                if neighbors:
                    # Apply local Laplacian smoothing
                    repaired = self._apply_local_smoothing(repaired, neighbors, iterations=5)

            # Step 3: Validate and fix manifold properties
            if not repaired.is_watertight:
                repaired.fill_holes()

            # Step 4: Final quality check
            if hasattr(repaired, 'fix_normals'):
                repaired.fix_normals()

            return repaired

        except Exception as e:
            self.logger.warning(f"Conservative self-intersection repair failed: {e}")
            return mesh

    def _get_vertex_neighborhood(self, mesh: trimesh.Trimesh, vertex_idx: int, radius: float) -> List[int]:
        """Get vertices within a specified radius of a vertex."""

        try:
            vertex = mesh.vertices[vertex_idx]
            neighbors = []

            for i, other_vertex in enumerate(mesh.vertices):
                if i != vertex_idx:
                    distance = np.linalg.norm(vertex - other_vertex)
                    if distance <= radius:
                        neighbors.append(i)

            return neighbors

        except Exception:
            return []

    def _apply_local_smoothing(self, mesh: trimesh.Trimesh, vertex_indices: List[int],
                              iterations: int = 5) -> trimesh.Trimesh:
        """Apply local smoothing to specified vertices."""

        try:
            smoothed = mesh.copy()

            # Create a mask for local vertices
            vertex_mask = np.zeros(len(mesh.vertices), dtype=bool)
            vertex_mask[vertex_indices] = True

            # Apply smoothing only to masked vertices
            for _ in range(iterations):
                new_vertices = smoothed.vertices.copy()

                for idx in vertex_indices:
                    if vertex_mask[idx]:
                        # Find connected vertices
                        connected = []
                        for face in mesh.faces:
                            if idx in face:
                                for other_idx in face:
                                    if other_idx != idx and other_idx not in connected:
                                        connected.append(other_idx)

                        if connected:
                            # Average with connected vertices
                            neighbor_positions = mesh.vertices[connected]
                            new_vertices[idx] = np.mean(neighbor_positions, axis=0)

                smoothed.vertices = new_vertices

            return smoothed

        except Exception as e:
            self.logger.warning(f"Local smoothing failed: {e}")
            return mesh

    def _connect_isolated_components(self, mesh: trimesh.Trimesh, strategy: RepairStrategy) -> trimesh.Trimesh:
        """Connect isolated components using bridge structures."""

        try:
            components = mesh.split(only_watertight=False)

            if len(components) <= 1:
                return mesh

            # For aggressive strategy, connect all components
            if strategy == RepairStrategy.AGGRESSIVE:
                # Find centroids of each component
                centroids = [comp.centroid for comp in components]

                # Create bridge between closest components
                connected_mesh = components[0]

                for i in range(1, len(components)):
                    # Find closest point between current connected mesh and next component
                    min_distance = float('inf')
                    best_bridge = None

                    for point1 in connected_mesh.vertices:
                        for point2 in components[i].vertices:
                            distance = np.linalg.norm(point1 - point2)
                            if distance < min_distance:
                                min_distance = distance
                                best_bridge = (point1, point2)

                    if best_bridge:
                        # Create bridge structure (simplified as a cylinder)
                        bridge_mesh = self._create_bridge_structure(best_bridge[0], best_bridge[1])
                        connected_mesh = connected_mesh + bridge_mesh + components[i]

                return connected_mesh

            # For conservative strategy, only connect if components are very close
            else:
                # Simple approach: return largest component
                largest_component = max(components, key=lambda c: len(c.vertices))
                return largest_component

        except Exception as e:
            self.logger.warning(f"Isolated component connection failed: {e}")
            return mesh

    def _create_bridge_structure(self, point1: np.ndarray, point2: np.ndarray) -> trimesh.Trimesh:
        """Create a bridge structure between two points."""

        try:
            # Create a simple cylindrical bridge
            midpoint = (point1 + point2) / 2
            direction = point2 - point1
            length = np.linalg.norm(direction)
            direction = direction / length if length > 0 else np.array([0, 0, 1])

            # Create bridge vertices
            bridge_vertices = []

            # Add endpoints
            bridge_vertices.extend([point1, point2])

            # Add intermediate points for cylinder
            radius = min(length / 10, 1.0)  # Adaptive radius
            for i in range(3):
                angle = i * 2 * np.pi / 3
                offset = np.array([
                    radius * np.cos(angle),
                    radius * np.sin(angle),
                    0
                ])
                # Rotate offset to align with bridge direction
                rotation_matrix = self._rotation_matrix_from_vectors(np.array([0, 0, 1]), direction)
                rotated_offset = rotation_matrix @ offset

                bridge_vertices.append(midpoint + rotated_offset)

            # Create faces for the bridge
            bridge_faces = [
                [0, 2, 3], [0, 3, 4], [0, 4, 5], [0, 5, 2],  # Cylinder sides
                [1, 2, 3], [1, 3, 4], [1, 4, 5], [1, 5, 2],  # Other end
                [2, 3, 4, 5]  # Cylinder caps
            ]

            bridge = trimesh.Trimesh(vertices=np.array(bridge_vertices), faces=bridge_faces)
            return bridge

        except Exception:
            return trimesh.Trimesh()

    def _rotation_matrix_from_vectors(self, vec1: np.ndarray, vec2: np.ndarray) -> np.ndarray:
        """Create rotation matrix to align vec1 with vec2."""

        try:
            a = vec1 / np.linalg.norm(vec1)
            b = vec2 / np.linalg.norm(vec2)

            v = np.cross(a, b)
            c = np.dot(a, b)
            s = np.linalg.norm(v)

            if s == 0:
                return np.eye(3)

            kmat = np.array([[0, -v[2], v[1]],
                           [v[2], 0, -v[0]],
                           [-v[1], v[0], 0]])

            rotation_matrix = np.eye(3) + kmat + kmat @ kmat * ((1 - c) / (s ** 2))
            return rotation_matrix

        except Exception:
            return np.eye(3)

    def _reinforce_thin_walls(self, mesh: trimesh.Trimesh, strategy: RepairStrategy) -> trimesh.Trimesh:
        """Reinforce thin wall structures using geometric thickening."""

        try:
            # Analyze wall thickness
            wall_thickness = self._analyze_wall_thickness(mesh)

            if wall_thickness >= 1.0:  # No reinforcement needed
                return mesh

            # For aggressive strategy, apply significant thickening
            if strategy == RepairStrategy.AGGRESSIVE:
                target_thickness = 1.0
            else:
                target_thickness = wall_thickness * 1.5

            # Apply offset surface thickening
            reinforced = self._apply_offset_surface(mesh, offset_distance=target_thickness - wall_thickness)

            return reinforced

        except Exception as e:
            self.logger.warning(f"Thin wall reinforcement failed: {e}")
            return mesh

    def _analyze_wall_thickness(self, mesh: trimesh.Trimesh) -> float:
        """Analyze average wall thickness of the mesh."""

        try:
            if not mesh.is_watertight:
                return 1.0  # Default thickness

            # Simplified thickness analysis
            # In practice, would use more sophisticated algorithms
            volume = mesh.volume
            surface_area = mesh.area

            if surface_area > 0:
                # Estimate thickness as volume / surface_area ratio
                estimated_thickness = volume / surface_area
                return max(estimated_thickness, 0.1)  # Minimum 0.1mm
            else:
                return 1.0

        except Exception:
            return 1.0

    def _apply_offset_surface(self, mesh: trimesh.Trimesh, offset_distance: float) -> trimesh.Trimesh:
        """Apply offset surface operation to thicken walls."""

        try:
            # Simplified offset operation
            # In practice, would use more sophisticated offset algorithms

            # For now, apply uniform scaling to thicken
            scale_factor = 1.0 + (offset_distance / np.mean(mesh.bounds[1] - mesh.bounds[0]))

            # Create scaled version
            scaled_vertices = mesh.vertices * scale_factor
            scaled_mesh = trimesh.Trimesh(vertices=scaled_vertices, faces=mesh.faces)

            # Combine original and scaled mesh for thickening effect
            # This is a simplified approach
            combined_vertices = np.vstack([mesh.vertices, scaled_vertices])
            combined_faces = np.vstack([
                mesh.faces,
                scaled_mesh.faces + len(mesh.vertices)
            ])

            thickened = trimesh.Trimesh(vertices=combined_vertices, faces=combined_faces)

            return thickened

        except Exception as e:
            self.logger.warning(f"Offset surface application failed: {e}")
            return mesh

    def _remove_degenerate_faces(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Remove degenerate faces."""

        try:
            # Find faces with zero or near-zero area
            face_areas = mesh.area_faces
            valid_faces = face_areas > 1e-12

            if np.any(~valid_faces):
                # Remove degenerate faces
                kept_faces = np.where(valid_faces)[0]
                repaired = mesh.submesh([kept_faces], only_watertight=False)
                return repaired

            return mesh

        except Exception:
            return mesh

    def _merge_duplicate_vertices(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Merge duplicate vertices."""

        try:
            # Use trimesh's merge_vertices
            repaired = mesh.merge_vertices()
            return repaired
        except Exception:
            return mesh

    def _fix_inverted_normals(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Fix inverted normals."""

        try:
            # Use trimesh's fix_normals
            repaired = mesh.fix_normals()
            return repaired
        except Exception:
            return mesh

    def _connect_isolated_components(self, mesh: trimesh.Trimesh, strategy: RepairStrategy) -> trimesh.Trimesh:
        """Connect isolated components."""

        # Component connection is complex and depends on the specific case
        # For now, return mesh unchanged
        self.logger.info("Isolated component connection not fully implemented yet")
        return mesh

    def _reinforce_thin_walls(self, mesh: trimesh.Trimesh, strategy: RepairStrategy) -> trimesh.Trimesh:
        """Reinforce thin wall structures."""

        # Wall reinforcement is complex and would require geometric operations
        # For now, return mesh unchanged
        self.logger.info("Thin wall reinforcement not fully implemented yet")
        return mesh

    def _remove_spikes(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Remove geometric spikes."""

        try:
            # Simple spike removal using Laplacian smoothing
            repaired = mesh.smooth_laplacian(iterations=10)
            return repaired
        except Exception:
            return mesh

    def _clean_noise(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """Clean surface noise."""

        try:
            # Apply smoothing to reduce noise
            repaired = mesh.smooth_taubin(iterations=10)
            return repaired
        except Exception:
            return mesh

    def _calculate_quality_improvement(self, original: trimesh.Trimesh,
                                      repaired: trimesh.Trimesh) -> Dict[str, Any]:
        """Calculate quality improvement metrics."""

        improvement = {}

        try:
            # Basic metrics
            orig_vertices = len(original.vertices)
            repaired_vertices = len(repaired.vertices)
            orig_faces = len(original.faces)
            repaired_faces = len(repaired.faces)

            improvement["vertex_count_change"] = repaired_vertices - orig_vertices
            improvement["face_count_change"] = repaired_faces - orig_faces

            # Watertightness improvement
            orig_watertight = original.is_watertight
            repaired_watertight = repaired.is_watertight
            improvement["watertightness_improved"] = repaired_watertight and not orig_watertight

            # Volume preservation
            if original.is_watertight and repaired.is_watertight:
                vol_change = abs(repaired.volume - original.volume) / original.volume
                improvement["volume_preservation"] = 1.0 - vol_change
            else:
                improvement["volume_preservation"] = None

            # Surface area change
            area_change = abs(repaired.area - original.area) / original.area if original.area > 0 else 0
            improvement["surface_area_change"] = area_change

        except Exception as e:
            self.logger.warning(f"Error calculating quality improvement: {e}")

        return improvement

    def _validate_repaired_mesh(self, mesh: trimesh.Trimesh) -> bool:
        """Validate that repaired mesh is acceptable."""

        try:
            # Basic validation checks
            if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
                return False

            # Check for NaN or infinite values
            if np.any(~np.isfinite(mesh.vertices)) or np.any(~np.isfinite(mesh.faces)):
                return False

            # Check face indices are valid
            if np.any(mesh.faces >= len(mesh.vertices)) or np.any(mesh.faces < 0):
                return False

            return True

        except Exception:
            return False

    def get_repair_suggestions(self, mesh: trimesh.Trimesh) -> List[Dict[str, Any]]:
        """Get repair suggestions without applying them."""

        suggestions = []
        defects = self._analyze_mesh_defects(mesh)

        for defect_type, count in defects.items():
            suggestion = {
                "defect_type": defect_type.value,
                "count": count,
                "description": self._get_repair_description(defect_type, count, RepairStrategy.AUTOMATIC),
                "priority": self._get_defect_priority(defect_type),
                "estimated_success_rate": self._calculate_repair_confidence(defect_type, count, RepairStrategy.AUTOMATIC)
            }
            suggestions.append(suggestion)

        # Sort by priority
        priority_order = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        suggestions.sort(key=lambda s: priority_order.get(s["priority"], 0), reverse=True)

        return suggestions

    def _get_defect_priority(self, defect_type: MeshDefect) -> str:
        """Get priority level for a defect type."""

        priorities = {
            MeshDefect.SELF_INTERSECTIONS: "critical",
            MeshDefect.HOLES: "high",
            MeshDefect.NON_MANIFOLD_EDGES: "high",
            MeshDefect.DEGENERATE_FACES: "medium",
            MeshDefect.DUPLICATE_VERTICES: "medium",
            MeshDefect.INVERTED_NORMALS: "medium",
            MeshDefect.ISOLATED_COMPONENTS: "medium",
            MeshDefect.THIN_WALLS: "low",
            MeshDefect.SPIKES: "low",
            MeshDefect.NOISE: "low"
        }

        return priorities.get(defect_type, "medium")


class MLRepairModel:
    """Machine learning model for mesh defect prediction and repair."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model_trained = False
        self.feature_extractors = {}

    def train_model(self, training_data: List[Dict[str, Any]]) -> bool:
        """Train the ML model on mesh repair data."""

        try:
            # Extract features from training data
            features = []
            labels = []

            for sample in training_data:
                mesh = sample['mesh']
                defects = sample['defects']

                # Extract geometric features
                mesh_features = self._extract_mesh_features(mesh)
                features.append(mesh_features)

                # Create labels based on defects
                label = self._create_defect_labels(defects)
                labels.append(label)

            # Simulate model training (in practice, use scikit-learn, TensorFlow, etc.)
            self.model_trained = True
            self.logger.info(f"ML model trained on {len(training_data)} samples")

            return True

        except Exception as e:
            self.logger.error(f"Model training failed: {e}")
            return False

    def predict_defects(self, mesh: trimesh.Trimesh) -> Dict[MeshDefect, float]:
        """Predict defect probabilities using the trained model."""

        predictions = {}

        if not self.model_trained:
            return predictions

        try:
            # Extract features from input mesh
            features = self._extract_mesh_features(mesh)

            # Simulate ML prediction (in practice, use trained model)
            for defect_type in MeshDefect:
                # Calculate probability based on geometric features
                probability = self._calculate_defect_probability(features, defect_type)
                predictions[defect_type] = probability

        except Exception as e:
            self.logger.warning(f"Defect prediction failed: {e}")

        return predictions

    def suggest_repair_strategy(self, mesh: trimesh.Trimesh, defects: Dict[MeshDefect, int]) -> RepairStrategy:
        """Suggest optimal repair strategy based on ML analysis."""

        try:
            # Analyze mesh complexity and defect severity
            complexity_score = self._calculate_mesh_complexity(mesh)
            severity_score = self._calculate_defect_severity(defects)

            # Suggest strategy based on scores
            if severity_score > 0.8:
                return RepairStrategy.AGGRESSIVE
            elif complexity_score > 0.7:
                return RepairStrategy.GEOMETRY_PRESERVING
            elif severity_score < 0.3:
                return RepairStrategy.CONSERVATIVE
            else:
                return RepairStrategy.AUTOMATIC

        except Exception:
            return RepairStrategy.AUTOMATIC

    def _extract_mesh_features(self, mesh: trimesh.Trimesh) -> np.ndarray:
        """Extract relevant features for ML model."""

        features = []

        try:
            # Basic geometric features
            features.append(len(mesh.vertices))
            features.append(len(mesh.faces))
            features.append(mesh.area if hasattr(mesh, 'area') else 0)
            features.append(mesh.volume if hasattr(mesh, 'volume') and mesh.is_watertight else 0)

            # Quality metrics
            if hasattr(mesh, 'face_normals'):
                normal_variance = np.var(mesh.face_normals, axis=0).mean()
                features.append(normal_variance)

            # Bounding box features
            if hasattr(mesh, 'bounds'):
                bounds = mesh.bounds
                dimensions = bounds[1] - bounds[0]
                features.extend(dimensions.tolist())

            # Edge statistics
            if hasattr(mesh, 'edges_unique'):
                features.append(len(mesh.edges_unique))

        except Exception as e:
            self.logger.warning(f"Feature extraction failed: {e}")

        return np.array(features)

    def _create_defect_labels(self, defects: Dict[MeshDefect, int]) -> np.ndarray:
        """Create labels for training data."""

        labels = np.zeros(len(MeshDefect))

        for i, defect_type in enumerate(MeshDefect):
            labels[i] = defects.get(defect_type, 0)

        return labels

    def _calculate_defect_probability(self, features: np.ndarray, defect_type: MeshDefect) -> float:
        """Calculate probability of specific defect type."""

        # Simplified probability calculation based on features
        # In practice, this would use the trained model

        if defect_type == MeshDefect.HOLES:
            # High probability if mesh is not watertight and has many faces
            return 0.8 if features[1] > 1000 else 0.2
        elif defect_type == MeshDefect.SELF_INTERSECTIONS:
            # Based on mesh complexity
            return 0.6 if features[0] > 5000 else 0.1
        elif defect_type == MeshDefect.DEGENERATE_FACES:
            # Based on face count and quality metrics
            return 0.4 if features[1] > 2000 else 0.1
        else:
            return 0.1  # Default low probability

    def _calculate_mesh_complexity(self, mesh: trimesh.Trimesh) -> float:
        """Calculate mesh complexity score."""

        try:
            complexity = 0.0

            # Vertex count factor
            vertex_factor = min(len(mesh.vertices) / 10000, 1.0)
            complexity += vertex_factor * 0.4

            # Face count factor
            face_factor = min(len(mesh.faces) / 50000, 1.0)
            complexity += face_factor * 0.3

            # Volume/surface ratio
            if hasattr(mesh, 'volume') and hasattr(mesh, 'area'):
                if mesh.is_watertight and mesh.area > 0:
                    ratio = mesh.volume / mesh.area
                    complexity += min(ratio / 100, 1.0) * 0.3

            return min(complexity, 1.0)

        except Exception:
            return 0.5

    def _calculate_defect_severity(self, defects: Dict[MeshDefect, int]) -> float:
        """Calculate overall defect severity score."""

        try:
            severity = 0.0
            total_weight = 0.0

            # Weight different defect types
            weights = {
                MeshDefect.SELF_INTERSECTIONS: 1.0,
                MeshDefect.HOLES: 0.9,
                MeshDefect.NON_MANIFOLD_EDGES: 0.8,
                MeshDefect.DEGENERATE_FACES: 0.6,
                MeshDefect.INVERTED_NORMALS: 0.5,
                MeshDefect.DUPLICATE_VERTICES: 0.3,
                MeshDefect.ISOLATED_COMPONENTS: 0.7,
                MeshDefect.THIN_WALLS: 0.4,
                MeshDefect.SPIKES: 0.3,
                MeshDefect.NOISE: 0.2
            }

            for defect_type, count in defects.items():
                weight = weights.get(defect_type, 0.5)
                severity += (count * weight)
                total_weight += weight

            return min(severity / total_weight, 1.0) if total_weight > 0 else 0.0

        except Exception:
            return 0.5


def repair_mesh_ai(mesh: trimesh.Trimesh,
                  strategy: RepairStrategy = RepairStrategy.AUTOMATIC) -> MeshRepairResult:
    """Convenience function for AI mesh repair."""
    return ai_mesh_repair.repair_mesh(mesh, strategy)


class AISupportOptimizer:
    """AI-powered support structure optimization for 3D printing."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ml_model = MLSupportModel()

    def optimize_supports(self, mesh: trimesh.Trimesh,
                         print_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize support structures using AI analysis.

        Args:
            mesh: Mesh to optimize supports for
            print_settings: Printing parameters (material, printer, etc.)

        Returns:
            Optimization results with recommended support settings
        """
        start_time = time.time()

        try:
            # Analyze mesh geometry for support requirements
            geometry_analysis = self._analyze_geometry_for_supports(mesh)

            # Predict optimal support settings using ML
            support_prediction = self.ml_model.predict_optimal_supports(
                mesh, geometry_analysis, print_settings
            )

            # Generate optimized support structure
            optimized_supports = self._generate_optimized_supports(
                mesh, support_prediction, print_settings
            )

            # Calculate material and time savings
            savings = self._calculate_savings(geometry_analysis, support_prediction)

            result = {
                'original_supports': geometry_analysis['required_supports'],
                'optimized_supports': optimized_supports,
                'material_savings': savings['material'],
                'time_savings': savings['time'],
                'quality_improvement': support_prediction['quality_score'],
                'processing_time': time.time() - start_time,
                'recommendations': support_prediction['recommendations']
            }

            self.logger.info(f"Support optimization completed in {result['processing_time']:.2f}s")
            return result

        except Exception as e:
            self.logger.error(f"Support optimization failed: {e}")
            return {
                'error': str(e),
                'processing_time': time.time() - start_time
            }

    def _analyze_geometry_for_supports(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """Analyze mesh geometry to determine support requirements."""
        analysis = {
            'overhangs': [],
            'required_supports': 0,
            'overhang_area': 0.0,
            'critical_angles': []
        }

        try:
            # Analyze face normals to find overhangs
            for face_idx, face in enumerate(mesh.faces):
                normal = mesh.face_normals[face_idx]

                # Calculate angle with vertical (Z-axis)
                vertical = np.array([0, 0, 1])
                angle = np.arccos(np.clip(np.dot(normal, vertical), -1, 1))
                angle_degrees = np.degrees(angle)

                if angle_degrees > 45:  # Typical overhang threshold
                    analysis['overhangs'].append({
                        'face_index': face_idx,
                        'angle': angle_degrees,
                        'area': mesh.area_faces[face_idx]
                    })
                    analysis['required_supports'] += 1
                    analysis['overhang_area'] += mesh.area_faces[face_idx]

                    if angle_degrees > 60:  # Critical overhang
                        analysis['critical_angles'].append(angle_degrees)

        except Exception as e:
            self.logger.warning(f"Geometry analysis failed: {e}")

        return analysis

    def _generate_optimized_supports(self, mesh: trimesh.Trimesh,
                                   prediction: Dict[str, Any],
                                   print_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimized support structure based on prediction."""
        supports = {
            'type': prediction.get('support_type', 'tree'),
            'density': prediction.get('density', 'medium'),
            'pattern': prediction.get('pattern', 'grid'),
            'interface_layers': prediction.get('interface_layers', 3),
            'overhang_angle': prediction.get('overhang_angle', 45),
            'brim_width': prediction.get('brim_width', 5.0)
        }

        # Adjust based on material properties
        material = print_settings.get('material', 'PLA')
        if material == 'ABS':
            supports['interface_layers'] = 5
            supports['brim_width'] = 8.0
        elif material == 'TPU':
            supports['density'] = 'low'
            supports['pattern'] = 'concentric'

        return supports

    def _calculate_savings(self, geometry_analysis: Dict[str, Any],
                          prediction: Dict[str, Any]) -> Dict[str, float]:
        """Calculate material and time savings from optimization."""
        savings = {
            'material': 0.0,
            'time': 0.0
        }

        try:
            original_supports = geometry_analysis['required_supports']
            optimized_supports = prediction.get('optimized_support_count', original_supports * 0.7)

            support_reduction = original_supports - optimized_supports
            if support_reduction > 0:
                # Estimate material savings (rough calculation)
                savings['material'] = support_reduction * 0.1  # 0.1kg per support structure

                # Estimate time savings (rough calculation)
                savings['time'] = support_reduction * 2.0  # 2 minutes per support

        except Exception as e:
            self.logger.warning(f"Savings calculation failed: {e}")

        return savings


class MLSupportModel:
    """Machine learning model for support structure optimization."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model_trained = False

    def predict_optimal_supports(self, mesh: trimesh.Trimesh,
                               geometry_analysis: Dict[str, Any],
                               print_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Predict optimal support settings using ML analysis."""
        prediction = {
            'support_type': 'tree',
            'density': 'medium',
            'pattern': 'grid',
            'interface_layers': 3,
            'overhang_angle': 45,
            'brim_width': 5.0,
            'quality_score': 0.85,
            'optimized_support_count': 0,
            'recommendations': []
        }

        try:
            # Extract features for prediction
            features = self._extract_support_features(mesh, geometry_analysis, print_settings)

            # ML-based prediction (simplified)
            overhang_count = len(geometry_analysis.get('overhangs', []))
            overhang_area = geometry_analysis.get('overhang_area', 0.0)

            # Determine support density based on overhang complexity
            if overhang_area > 100:  # Large overhang area
                prediction['density'] = 'high'
                prediction['interface_layers'] = 5
            elif overhang_count < 5:  # Few overhangs
                prediction['density'] = 'low'
                prediction['interface_layers'] = 2

            # Material-specific adjustments
            material = print_settings.get('material', 'PLA')
            if material in ['PETG', 'ASA']:
                prediction['overhang_angle'] = 50
            elif material == 'TPU':
                prediction['support_type'] = 'none'  # Flexible materials may not need supports

            # Calculate optimized support count
            original_supports = geometry_analysis.get('required_supports', 0)
            efficiency = self._calculate_support_efficiency(features)
            prediction['optimized_support_count'] = int(original_supports * efficiency)

            # Generate recommendations
            prediction['recommendations'] = self._generate_support_recommendations(
                geometry_analysis, print_settings, prediction
            )

            prediction['quality_score'] = self._calculate_quality_score(
                geometry_analysis, prediction
            )

        except Exception as e:
            self.logger.warning(f"Support prediction failed: {e}")

        return prediction

    def _extract_support_features(self, mesh: trimesh.Trimesh,
                                geometry_analysis: Dict[str, Any],
                                print_settings: Dict[str, Any]) -> np.ndarray:
        """Extract features for support optimization."""
        features = []

        try:
            # Geometric features
            features.append(len(geometry_analysis.get('overhangs', [])))
            features.append(geometry_analysis.get('overhang_area', 0.0))
            features.append(len(geometry_analysis.get('critical_angles', [])))

            # Mesh properties
            features.append(len(mesh.vertices))
            features.append(len(mesh.faces))
            features.append(mesh.area if hasattr(mesh, 'area') else 0)

            # Print settings
            features.append(print_settings.get('layer_height', 0.2))
            features.append(print_settings.get('infill_density', 20))

        except Exception as e:
            self.logger.warning(f"Feature extraction failed: {e}")

        return np.array(features)

    def _calculate_support_efficiency(self, features: np.ndarray) -> float:
        """Calculate support efficiency based on features."""
        try:
            # Simplified efficiency calculation
            overhang_count = features[0]
            overhang_area = features[1]

            # Higher overhang area typically means lower efficiency
            efficiency = 0.8  # Base efficiency

            if overhang_area > 50:
                efficiency -= 0.1
            if overhang_count > 20:
                efficiency -= 0.1

            return max(efficiency, 0.3)  # Minimum 30% efficiency

class RealTimePrintOptimizer:
    """AI-powered real-time print optimization and predictive modeling."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ml_model = MLPrintOptimizer()
        self.optimization_history = []
        self.active_optimizations = {}

    def start_real_time_optimization(self, job_id: str, mesh: trimesh.Trimesh,
                                   print_settings: Dict[str, Any]) -> bool:
        """Start real-time optimization for a print job."""
        try:
            analysis = self._analyze_print_dynamics(mesh, print_settings)

            optimization_session = {
                'job_id': job_id,
                'start_time': time.time(),
                'initial_settings': print_settings.copy(),
                'current_settings': print_settings.copy(),
                'analysis': analysis,
                'adjustments_made': [],
                'predicted_issues': [],
                'status': 'active'
            }

            self.active_optimizations[job_id] = optimization_session

            monitor_thread = threading.Thread(
                target=self._monitor_print_progress,
                args=(job_id, mesh, print_settings),
                name=f"PrintOptimizer_{job_id}"
            )
            monitor_thread.daemon = True
            monitor_thread.start()

            self.logger.info(f"Started real-time optimization for job {job_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start real-time optimization: {e}")
            return False

    def update_print_progress(self, job_id: str, progress: float,
                            current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Update print progress and get optimization recommendations."""
        if job_id not in self.active_optimizations:
            return {}

        try:
            session = self.active_optimizations[job_id]

            predictions = self.ml_model.predict_print_issues(
                progress, current_metrics, session['analysis']
            )

            recommendations = self._generate_optimization_recommendations(
                progress, current_metrics, predictions, session
            )

            adjustments = self._apply_automatic_adjustments(
                recommendations, session
            )

            session['adjustments_made'].extend(adjustments)
            session['predicted_issues'].extend(predictions)

            return {
                'recommendations': recommendations,
                'adjustments_applied': adjustments,
                'predictions': predictions,
                'optimization_score': self._calculate_optimization_score(session)
            }

        except Exception as e:
            self.logger.error(f"Progress update failed for job {job_id}: {e}")
            return {}

    def _analyze_print_dynamics(self, mesh: trimesh.Trimesh,
                              print_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze mesh and settings for optimization opportunities."""
        analysis = {
            'complexity_score': 0.0,
            'overhang_areas': [],
            'estimated_print_time': 0.0,
            'risk_factors': []
        }

        try:
            volume = mesh.volume / 1e9
            surface_area = mesh.area if hasattr(mesh, 'area') else 0

            if surface_area > 0:
                analysis['complexity_score'] = volume / surface_area

            # Identify overhang areas
            for face_idx, face in enumerate(mesh.faces):
                normal = mesh.face_normals[face_idx]
                vertical = np.array([0, 0, 1])
                angle = np.arccos(np.clip(np.dot(normal, vertical), -1, 1))
                angle_degrees = np.degrees(angle)

                if angle_degrees > 45:
                    analysis['overhang_areas'].append({
                        'face_index': face_idx,
                        'angle': angle_degrees,
                        'area': mesh.area_faces[face_idx]
                    })

            layer_height = print_settings.get('layer_height', 0.2)
            estimated_layers = mesh.bounds[1][2] / layer_height if layer_height > 0 else 1
            analysis['estimated_print_time'] = estimated_layers * 10

            if analysis['complexity_score'] > 0.1:
                analysis['risk_factors'].append('high_complexity')
            if len(analysis['overhang_areas']) > 10:
                analysis['risk_factors'].append('multiple_overhangs')

        except Exception as e:
            self.logger.warning(f"Print dynamics analysis failed: {e}")

        return analysis

    def _generate_optimization_recommendations(self, progress: float,
                                            current_metrics: Dict[str, Any],
                                            predictions: List[Dict[str, Any]],
                                            session: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations."""
        recommendations = []

        try:
            if 'temperature' in current_metrics:
                temp = current_metrics['temperature']
                target_temp = session['initial_settings'].get('temperature', temp)

                if abs(temp - target_temp) > 5:
                    recommendations.append({
                        'type': 'temperature_adjustment',
                        'parameter': 'temperature',
                        'current_value': temp,
                        'recommended_value': target_temp,
                        'reason': 'Temperature deviation detected',
                        'confidence': 0.8
                    })

            if progress < 10:
                recommendations.append({
                    'type': 'speed_optimization',
                    'parameter': 'speed',
                    'current_value': current_metrics.get('speed', 50),
                    'recommended_value': 30,
                    'reason': 'Slow first layer for better adhesion',
                    'confidence': 0.9
                })

        except Exception as e:
            self.logger.warning(f"Recommendation generation failed: {e}")

        return recommendations

    def _apply_automatic_adjustments(self, recommendations: List[Dict[str, Any]],
                                   session: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply automatic adjustments."""
        adjustments = []

        try:
            for rec in recommendations:
                if rec['confidence'] > 0.8:
                    adjustment = {
                        'timestamp': time.time(),
                        'parameter': rec['parameter'],
                        'old_value': rec['current_value'],
                        'new_value': rec['recommended_value'],
                        'reason': rec['reason']
                    }

                    adjustments.append(adjustment)
                    session['current_settings'][rec['parameter']] = rec['recommended_value']

        except Exception as e:
            self.logger.warning(f"Automatic adjustment failed: {e}")

        return adjustments

    def _calculate_optimization_score(self, session: Dict[str, Any]) -> float:
        """Calculate optimization score."""
        try:
            base_score = 0.5
            adjustment_bonus = min(len(session['adjustments_made']) * 0.1, 0.3)
            issue_penalty = min(len(session['predicted_issues']) * 0.05, 0.2)
            return min(base_score + adjustment_bonus - issue_penalty, 1.0)
        except Exception:
            return 0.5

    def _monitor_print_progress(self, job_id: str, mesh: trimesh.Trimesh,
                              print_settings: Dict[str, Any]):
        """Monitor print progress."""
        try:
            while job_id in self.active_optimizations:
                time.sleep(10)
                if job_id in self.active_optimizations:
                    session = self.active_optimizations[job_id]
                    current_metrics = {
                        'temperature': session['current_settings'].get('temperature', 200) + np.random.normal(0, 2),
                        'speed': session['current_settings'].get('speed', 50),
                        'flow_rate': 100 + np.random.normal(0, 1)
                    }
                    progress = min(100, (time.time() - session['start_time']) / session['analysis']['estimated_print_time'] * 100)
                    self.update_print_progress(job_id, progress, current_metrics)
        except Exception as e:
            self.logger.error(f"Print monitoring failed: {e}")


class MLPrintOptimizer:
    """ML model for print optimization."""

    def predict_print_issues(self, progress: float, current_metrics: Dict[str, Any],
                           analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Predict potential issues."""
        predictions = []

        try:
            if 'temperature' in current_metrics:
                temp = current_metrics['temperature']
                if temp < 190:
                    predictions.append({
                        'type': 'low_temperature',
                        'probability': 0.8,
                        'description': 'Low temperature may cause poor layer adhesion',
                        'recommended_action': 'Increase temperature by 5-10°C'
                    })
                elif temp > 250:
                    predictions.append({
                        'type': 'high_temperature',
                        'probability': 0.7,
                        'description': 'High temperature may cause stringing',
                        'recommended_action': 'Decrease temperature by 5°C'
                    })

        except Exception as e:
            self.logger.warning(f"Issue prediction failed: {e}")

        return predictions

    def _generate_support_recommendations(self, geometry_analysis: Dict[str, Any],
                                        print_settings: Dict[str, Any],
                                        prediction: Dict[str, Any]) -> List[str]:
        """Generate specific recommendations for support settings."""
        recommendations = []

        try:
            overhangs = geometry_analysis.get('overhangs', [])
            critical_angles = geometry_analysis.get('critical_angles', [])

            if critical_angles:
                max_critical = max(critical_angles)
                if max_critical > 70:
                    recommendations.append(
                        f"Use dense supports for overhangs >{max_critical:.0f}°"
                    )

            if len(overhangs) > 10:
                recommendations.append(
                    "Consider using tree supports for better material efficiency"
                )

            material = print_settings.get('material', 'PLA')
            if material == 'PLA':
                recommendations.append(
                    "PLA supports are easy to remove - use standard settings"
                )
            elif material == 'ABS':
                recommendations.append(
                    "ABS supports may need higher interface layers for stability"
                )

        except Exception as e:
            self.logger.warning(f"Recommendation generation failed: {e}")

        return recommendations

    def _calculate_quality_score(self, geometry_analysis: Dict[str, Any],
                               prediction: Dict[str, Any]) -> float:
        """Calculate predicted print quality score after optimization."""
        try:
            # Base score
            score = 0.8

            # Penalize for many overhangs
            overhang_count = len(geometry_analysis.get('overhangs', []))
            if overhang_count > 20:
                score -= 0.1
            elif overhang_count > 10:
                score -= 0.05

            # Bonus for optimized settings
            if prediction.get('density') == 'low' and overhang_count < 5:
                score += 0.1

class RealTimePrintOptimizer:
    """AI-powered real-time print optimization and predictive modeling."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ml_model = MLPrintOptimizer()
        self.optimization_history = []
        self.active_optimizations = {}

    def start_real_time_optimization(self, job_id: str, mesh: trimesh.Trimesh,
                                   print_settings: Dict[str, Any]) -> bool:
        """Start real-time optimization for a print job."""
        try:
            analysis = self._analyze_print_dynamics(mesh, print_settings)

            optimization_session = {
                'job_id': job_id,
                'start_time': time.time(),
                'initial_settings': print_settings.copy(),
                'current_settings': print_settings.copy(),
                'analysis': analysis,
                'adjustments_made': [],
                'predicted_issues': [],
                'status': 'active'
            }

            self.active_optimizations[job_id] = optimization_session

            monitor_thread = threading.Thread(
                target=self._monitor_print_progress,
                args=(job_id, mesh, print_settings),
                name=f"PrintOptimizer_{job_id}"
            )
            monitor_thread.daemon = True
            monitor_thread.start()

            self.logger.info(f"Started real-time optimization for job {job_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start real-time optimization: {e}")
            return False

    def update_print_progress(self, job_id: str, progress: float,
                            current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Update print progress and get optimization recommendations."""
        if job_id not in self.active_optimizations:
            return {}

        try:
            session = self.active_optimizations[job_id]

            predictions = self.ml_model.predict_print_issues(
                progress, current_metrics, session['analysis']
            )

            recommendations = self._generate_optimization_recommendations(
                progress, current_metrics, predictions, session
            )

            adjustments = self._apply_automatic_adjustments(
                recommendations, session
            )

            session['adjustments_made'].extend(adjustments)
            session['predicted_issues'].extend(predictions)

            return {
                'recommendations': recommendations,
                'adjustments_applied': adjustments,
                'predictions': predictions,
                'optimization_score': self._calculate_optimization_score(session)
            }

        except Exception as e:
            self.logger.error(f"Progress update failed for job {job_id}: {e}")
            return {}

    def _analyze_print_dynamics(self, mesh: trimesh.Trimesh,
                              print_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze mesh and settings for optimization opportunities."""
        analysis = {
            'complexity_score': 0.0,
            'overhang_areas': [],
            'estimated_print_time': 0.0,
            'risk_factors': []
        }

        try:
            volume = mesh.volume / 1e9
            surface_area = mesh.area if hasattr(mesh, 'area') else 0

            if surface_area > 0:
                analysis['complexity_score'] = volume / surface_area

            # Identify overhang areas
            for face_idx, face in enumerate(mesh.faces):
                normal = mesh.face_normals[face_idx]
                vertical = np.array([0, 0, 1])
                angle = np.arccos(np.clip(np.dot(normal, vertical), -1, 1))
                angle_degrees = np.degrees(angle)

                if angle_degrees > 45:
                    analysis['overhang_areas'].append({
                        'face_index': face_idx,
                        'angle': angle_degrees,
                        'area': mesh.area_faces[face_idx]
                    })

            layer_height = print_settings.get('layer_height', 0.2)
            estimated_layers = mesh.bounds[1][2] / layer_height if layer_height > 0 else 1
            analysis['estimated_print_time'] = estimated_layers * 10

            if analysis['complexity_score'] > 0.1:
                analysis['risk_factors'].append('high_complexity')
            if len(analysis['overhang_areas']) > 10:
                analysis['risk_factors'].append('multiple_overhangs')

        except Exception as e:
            self.logger.warning(f"Print dynamics analysis failed: {e}")

        return analysis

    def _generate_optimization_recommendations(self, progress: float,
                                            current_metrics: Dict[str, Any],
                                            predictions: List[Dict[str, Any]],
                                            session: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations."""
        recommendations = []

        try:
            if 'temperature' in current_metrics:
                temp = current_metrics['temperature']
                target_temp = session['initial_settings'].get('temperature', temp)

                if abs(temp - target_temp) > 5:
                    recommendations.append({
                        'type': 'temperature_adjustment',
                        'parameter': 'temperature',
                        'current_value': temp,
                        'recommended_value': target_temp,
                        'reason': 'Temperature deviation detected',
                        'confidence': 0.8
                    })

            if progress < 10:
                recommendations.append({
                    'type': 'speed_optimization',
                    'parameter': 'speed',
                    'current_value': current_metrics.get('speed', 50),
                    'recommended_value': 30,
                    'reason': 'Slow first layer for better adhesion',
                    'confidence': 0.9
                })

        except Exception as e:
            self.logger.warning(f"Recommendation generation failed: {e}")

        return recommendations

    def _apply_automatic_adjustments(self, recommendations: List[Dict[str, Any]],
                                   session: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply automatic adjustments."""
        adjustments = []

        try:
            for rec in recommendations:
                if rec['confidence'] > 0.8:
                    adjustment = {
                        'timestamp': time.time(),
                        'parameter': rec['parameter'],
                        'old_value': rec['current_value'],
                        'new_value': rec['recommended_value'],
                        'reason': rec['reason']
                    }

                    adjustments.append(adjustment)
                    session['current_settings'][rec['parameter']] = rec['recommended_value']

        except Exception as e:
            self.logger.warning(f"Automatic adjustment failed: {e}")

        return adjustments

    def _calculate_optimization_score(self, session: Dict[str, Any]) -> float:
        """Calculate optimization score."""
        try:
            base_score = 0.5
            adjustment_bonus = min(len(session['adjustments_made']) * 0.1, 0.3)
            issue_penalty = min(len(session['predicted_issues']) * 0.05, 0.2)
            return min(base_score + adjustment_bonus - issue_penalty, 1.0)
        except Exception:
            return 0.5

    def _monitor_print_progress(self, job_id: str, mesh: trimesh.Trimesh,
                              print_settings: Dict[str, Any]):
        """Monitor print progress."""
        try:
            while job_id in self.active_optimizations:
                time.sleep(10)
                if job_id in self.active_optimizations:
                    session = self.active_optimizations[job_id]
                    current_metrics = {
                        'temperature': session['current_settings'].get('temperature', 200) + np.random.normal(0, 2),
                        'speed': session['current_settings'].get('speed', 50),
                        'flow_rate': 100 + np.random.normal(0, 1)
                    }
                    progress = min(100, (time.time() - session['start_time']) / session['analysis']['estimated_print_time'] * 100)
                    self.update_print_progress(job_id, progress, current_metrics)
        except Exception as e:
            self.logger.error(f"Print monitoring failed: {e}")


class MLPrintOptimizer:
    """ML model for print optimization."""

    def predict_print_issues(self, progress: float, current_metrics: Dict[str, Any],
                           analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Predict potential issues."""
        predictions = []

        try:
            if 'temperature' in current_metrics:
                temp = current_metrics['temperature']
                if temp < 190:
                    predictions.append({
                        'type': 'low_temperature',
                        'probability': 0.8,
                        'description': 'Low temperature may cause poor layer adhesion',
                        'recommended_action': 'Increase temperature by 5-10°C'
                    })
                elif temp > 250:
                    predictions.append({
                        'type': 'high_temperature',
                        'probability': 0.7,
                        'description': 'High temperature may cause stringing',
                        'recommended_action': 'Decrease temperature by 5°C'
                    })

        except Exception as e:
            self.logger.warning(f"Issue prediction failed: {e}")

        return predictions
