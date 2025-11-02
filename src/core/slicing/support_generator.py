"""Advanced support structure generation for 3D printing."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Set
from enum import Enum
import numpy as np
import trimesh
from scipy.spatial import ConvexHull, Delaunay
import logging


class SupportType(Enum):
    """Support structure types."""
    NORMAL = "normal"
    TREE = "tree"
    ORGANIC = "organic"
    SLIM = "slim"
    GRID = "grid"
    SNUG = "snug"
    CONTOUR = "contour"


class SupportPattern(Enum):
    """Support infill patterns."""
    RECTILINEAR = "rectilinear"
    GRID = "grid"
    TRIANGULAR = "triangular"
    HONEYCOMB = "honeycomb"
    CONCENTRIC = "concentric"
    ZIGZAG = "zigzag"
    CROSS = "cross"


class SupportInterface(Enum):
    """Support interface types."""
    NONE = "none"
    AREA = "area"
    LINES = "lines"
    CONCENTRIC = "concentric"
    GRID = "grid"


@dataclass
class SupportSettings:
    """Comprehensive support generation settings."""
    # Basic settings
    support_type: SupportType = SupportType.NORMAL
    support_pattern: SupportPattern = SupportPattern.RECTILINEAR
    overhang_angle: float = 60.0  # degrees
    support_density: float = 15.0  # percentage
    support_everywhere: bool = False  # Build plate only vs everywhere

    # Distance settings
    support_z_distance: float = 0.2  # mm
    support_xy_distance: float = 0.7  # mm
    support_top_distance: float = 0.2  # mm
    support_bottom_distance: float = 0.2  # mm
    support_horizontal_expansion: float = 0.0  # mm

    # Interface settings
    support_interface_enable: bool = True
    support_interface_type: SupportInterface = SupportInterface.AREA
    support_interface_layers: int = 2
    support_interface_density: float = 75.0  # percentage
    support_interface_pattern: SupportPattern = SupportPattern.CONCENTRIC
    support_roof_enable: bool = True
    support_floor_enable: bool = True

    # Tree support settings
    tree_support_branch_angle: float = 45.0  # degrees
    tree_support_branch_distance: float = 5.0  # mm
    tree_support_branch_diameter: float = 2.0  # mm
    tree_support_trunk_diameter: float = 5.0  # mm
    tree_support_collision_resolution: float = 0.2  # mm

    # Advanced settings
    support_brim_enable: bool = False
    support_brim_width: float = 5.0  # mm
    gradual_support_enable: bool = False
    gradual_support_steps: int = 3
    conical_support_enable: bool = False
    conical_support_angle: float = 30.0  # degrees
    support_mesh_clip: bool = True
    support_tower_maximum_diameter: float = 8.0  # mm

    # Optimization
    support_skip_first_layers: int = 0
    support_skip_small_areas: bool = True
    minimum_support_area: float = 1.0  # mm²
    support_remove_small_features: bool = True
    small_feature_size: float = 2.0  # mm

    # Special features
    support_blocker_enable: bool = False
    support_enforcer_enable: bool = False
    custom_support_regions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SupportPoint:
    """Single support point that needs support."""
    position: np.ndarray
    normal: np.ndarray
    overhang_angle: float
    area: float
    layer_height: float
    requires_support: bool = True


@dataclass
class SupportPillar:
    """Support pillar structure."""
    base_position: np.ndarray
    top_position: np.ndarray
    diameter: float
    is_tree_branch: bool = False
    parent_pillar: Optional['SupportPillar'] = None
    child_pillars: List['SupportPillar'] = field(default_factory=list)


@dataclass
class SupportVolume:
    """Support volume structure."""
    mesh: trimesh.Trimesh
    volume: float
    contact_area: float
    support_type: SupportType
    interface_layers: List[np.ndarray]


@dataclass
class SupportGenerationResult:
    """Result of support generation."""
    success: bool
    support_volumes: List[SupportVolume]
    support_pillars: List[SupportPillar]
    total_support_volume: float
    total_contact_area: float
    overhang_areas: List[np.ndarray]
    support_points: List[SupportPoint]
    generation_time: float
    warnings: List[str]
    statistics: Dict[str, Any]


class SupportGenerator:
    """Advanced support structure generator."""

    def __init__(self, settings: SupportSettings = None):
        """Initialize support generator."""
        self.settings = settings or SupportSettings()
        self.logger = logging.getLogger(__name__)
        self.mesh: Optional[trimesh.Trimesh] = None
        self.support_points: List[SupportPoint] = []
        self.support_pillars: List[SupportPillar] = []
        self.support_volumes: List[SupportVolume] = []

    def generate_supports(self, mesh: trimesh.Trimesh) -> SupportGenerationResult:
        """
        Generate support structures for a mesh.

        Args:
            mesh: Trimesh object to generate supports for

        Returns:
            SupportGenerationResult with support structures
        """
        import time
        start_time = time.time()

        self.mesh = mesh
        self.support_points = []
        self.support_pillars = []
        self.support_volumes = []
        warnings = []

        try:
            # Step 1: Identify areas needing support
            self.support_points = self._identify_support_areas()

            if not self.support_points:
                return SupportGenerationResult(
                    success=True,
                    support_volumes=[],
                    support_pillars=[],
                    total_support_volume=0,
                    total_contact_area=0,
                    overhang_areas=[],
                    support_points=[],
                    generation_time=time.time() - start_time,
                    warnings=["No areas requiring support found"],
                    statistics={}
                )

            # Step 2: Generate support structures based on type
            if self.settings.support_type == SupportType.TREE:
                self._generate_tree_supports()
            elif self.settings.support_type == SupportType.ORGANIC:
                self._generate_organic_supports()
            elif self.settings.support_type == SupportType.SLIM:
                self._generate_slim_supports()
            else:
                self._generate_normal_supports()

            # Step 3: Generate support interfaces if enabled
            if self.settings.support_interface_enable:
                self._generate_support_interfaces()

            # Step 4: Optimize supports
            self._optimize_supports()

            # Step 5: Calculate statistics
            statistics = self._calculate_statistics()

            total_volume = sum(v.volume for v in self.support_volumes)
            total_contact = sum(v.contact_area for v in self.support_volumes)

            generation_time = time.time() - start_time

            return SupportGenerationResult(
                success=True,
                support_volumes=self.support_volumes,
                support_pillars=self.support_pillars,
                total_support_volume=total_volume,
                total_contact_area=total_contact,
                overhang_areas=[p.position for p in self.support_points],
                support_points=self.support_points,
                generation_time=generation_time,
                warnings=warnings,
                statistics=statistics
            )

        except Exception as e:
            self.logger.error(f"Support generation failed: {e}")
            return SupportGenerationResult(
                success=False,
                support_volumes=[],
                support_pillars=[],
                total_support_volume=0,
                total_contact_area=0,
                overhang_areas=[],
                support_points=[],
                generation_time=time.time() - start_time,
                warnings=[f"Support generation failed: {str(e)}"],
                statistics={}
            )

    def _identify_support_areas(self) -> List[SupportPoint]:
        """Identify areas that need support."""
        support_points = []
        overhang_threshold = np.cos(np.radians(self.settings.overhang_angle))

        # Analyze each face
        for face_idx, face in enumerate(self.mesh.faces):
            face_normal = self.mesh.face_normals[face_idx]

            # Check if face points downward beyond threshold
            if face_normal[2] < -overhang_threshold:
                # Calculate overhang angle
                overhang_angle = np.degrees(np.arccos(abs(face_normal[2])))

                # Get face center and area
                face_vertices = self.mesh.vertices[face]
                face_center = np.mean(face_vertices, axis=0)
                face_area = self.mesh.area_faces[face_idx]

                # Skip small areas if enabled
                if (self.settings.support_skip_small_areas and
                    face_area < self.settings.minimum_support_area):
                    continue

                # Check if support reaches build plate or existing support
                if self._can_place_support(face_center):
                    support_point = SupportPoint(
                        position=face_center,
                        normal=face_normal,
                        overhang_angle=overhang_angle,
                        area=face_area,
                        layer_height=face_center[2],
                        requires_support=True
                    )
                    support_points.append(support_point)

        # Cluster nearby support points
        support_points = self._cluster_support_points(support_points)

        return support_points

    def _can_place_support(self, position: np.ndarray) -> bool:
        """Check if support can be placed at position."""
        if self.settings.support_everywhere:
            return True

        # Check if there's clear path to build plate
        # Simplified - production would use ray casting
        z_min = self.mesh.bounds[0][2]

        # Cast ray downward
        ray_origin = position
        ray_direction = np.array([0, 0, -1])

        # Check for intersections
        locations, index_ray, index_tri = self.mesh.ray.intersects_location(
            ray_origins=[ray_origin],
            ray_directions=[ray_direction]
        )

        # If no intersections or only intersects at current position, can place support
        if len(locations) <= 1:
            return True

        # Check if path is mostly clear
        for loc in locations:
            if loc[2] < position[2] - self.settings.support_z_distance:
                # There's geometry below, check if it's far enough
                distance = position[2] - loc[2]
                if distance < 1.0:  # Less than 1mm clearance
                    return False

        return True

    def _cluster_support_points(self, points: List[SupportPoint]) -> List[SupportPoint]:
        """Cluster nearby support points to reduce support count."""
        if not points or len(points) < 2:
            return points

        # Convert to numpy array
        positions = np.array([p.position for p in points])

        # Simple clustering based on distance
        cluster_distance = 5.0  # mm
        clustered_points = []
        processed = set()

        for i, point in enumerate(points):
            if i in processed:
                continue

            # Find nearby points
            distances = np.linalg.norm(positions - point.position, axis=1)
            nearby_indices = np.where(distances < cluster_distance)[0]

            # Create merged support point
            nearby_points = [points[idx] for idx in nearby_indices]
            merged_position = np.mean([p.position for p in nearby_points], axis=0)
            merged_area = sum(p.area for p in nearby_points)
            merged_normal = np.mean([p.normal for p in nearby_points], axis=0)
            merged_normal = merged_normal / np.linalg.norm(merged_normal)

            clustered_point = SupportPoint(
                position=merged_position,
                normal=merged_normal,
                overhang_angle=max(p.overhang_angle for p in nearby_points),
                area=merged_area,
                layer_height=merged_position[2]
            )
            clustered_points.append(clustered_point)

            processed.update(nearby_indices)

        return clustered_points

    def _generate_normal_supports(self):
        """Generate normal (pillar-based) supports."""
        for point in self.support_points:
            # Create support pillar
            base_z = 0  # Build plate
            if self.settings.support_everywhere:
                # Find nearest surface below
                base_z = self._find_support_base(point.position)

            base_position = np.array([point.position[0], point.position[1], base_z])
            top_position = point.position - point.normal * self.settings.support_z_distance

            pillar = SupportPillar(
                base_position=base_position,
                top_position=top_position,
                diameter=self._calculate_pillar_diameter(point.area)
            )
            self.support_pillars.append(pillar)

            # Create support volume mesh
            support_mesh = self._create_pillar_mesh(pillar)
            if support_mesh:
                volume = SupportVolume(
                    mesh=support_mesh,
                    volume=support_mesh.volume,
                    contact_area=point.area,
                    support_type=SupportType.NORMAL,
                    interface_layers=[]
                )
                self.support_volumes.append(volume)

    def _generate_tree_supports(self):
        """Generate tree-like support structures."""
        # Build tree structure from support points
        trunk_positions = self._calculate_trunk_positions()

        for trunk_pos in trunk_positions:
            # Create main trunk
            trunk = SupportPillar(
                base_position=np.array([trunk_pos[0], trunk_pos[1], 0]),
                top_position=trunk_pos,
                diameter=self.settings.tree_support_trunk_diameter,
                is_tree_branch=False
            )
            self.support_pillars.append(trunk)

            # Find support points this trunk can reach
            reachable_points = self._find_reachable_points(trunk, self.support_points)

            # Create branches to support points
            for point in reachable_points:
                branch = self._create_tree_branch(trunk, point)
                if branch:
                    trunk.child_pillars.append(branch)
                    self.support_pillars.append(branch)

        # Convert tree structure to mesh volumes
        self._tree_to_volumes()

    def _calculate_trunk_positions(self) -> List[np.ndarray]:
        """Calculate optimal trunk positions for tree supports."""
        if not self.support_points:
            return []

        # Use k-means clustering to find trunk positions
        positions = np.array([p.position for p in self.support_points])

        # Simple implementation - use convex hull centers
        if len(positions) > 3:
            try:
                hull = ConvexHull(positions[:, :2])  # 2D hull in XY plane
                trunk_positions = []

                # Place trunks at hull vertices
                for vertex_idx in hull.vertices[:5]:  # Limit to 5 trunks
                    pos = positions[vertex_idx].copy()
                    pos[2] = self.mesh.bounds[0][2]  # Set to build plate
                    trunk_positions.append(pos)

                return trunk_positions
            except:
                pass

        # Fallback: single trunk at centroid
        centroid = np.mean(positions, axis=0)
        centroid[2] = self.mesh.bounds[0][2]
        return [centroid]

    def _find_reachable_points(self, trunk: SupportPillar,
                               points: List[SupportPoint]) -> List[SupportPoint]:
        """Find support points reachable from a trunk."""
        reachable = []
        max_branch_length = 50.0  # mm

        for point in points:
            # Calculate distance
            distance = np.linalg.norm(point.position[:2] - trunk.top_position[:2])

            # Check if within reach
            if distance < max_branch_length:
                # Check branch angle
                height_diff = point.position[2] - trunk.top_position[2]
                branch_angle = np.degrees(np.arctan2(distance, height_diff))

                if branch_angle <= self.settings.tree_support_branch_angle:
                    reachable.append(point)

        return reachable

    def _create_tree_branch(self, trunk: SupportPillar, point: SupportPoint) -> Optional[SupportPillar]:
        """Create a tree branch from trunk to support point."""
        # Calculate branch path
        start = trunk.top_position
        end = point.position - point.normal * self.settings.support_z_distance

        # Check for collisions
        if self._check_branch_collision(start, end):
            return None

        branch = SupportPillar(
            base_position=start,
            top_position=end,
            diameter=self.settings.tree_support_branch_diameter,
            is_tree_branch=True,
            parent_pillar=trunk
        )

        return branch

    def _check_branch_collision(self, start: np.ndarray, end: np.ndarray) -> bool:
        """Check if branch path collides with model."""
        # Simplified collision check
        direction = end - start
        length = np.linalg.norm(direction)
        direction = direction / length

        # Sample points along branch
        samples = int(length / self.settings.tree_support_collision_resolution)
        for i in range(samples):
            t = i / samples
            point = start + direction * length * t

            # Check if point is inside mesh
            if self.mesh.contains([point])[0]:
                return True

        return False

    def _tree_to_volumes(self):
        """Convert tree structure to mesh volumes."""
        for pillar in self.support_pillars:
            if not pillar.parent_pillar:  # Trunk
                # Create trunk mesh
                trunk_mesh = self._create_tapered_pillar_mesh(
                    pillar,
                    base_diameter=pillar.diameter,
                    top_diameter=pillar.diameter * 0.8
                )

                if trunk_mesh:
                    volume = SupportVolume(
                        mesh=trunk_mesh,
                        volume=trunk_mesh.volume,
                        contact_area=np.pi * (pillar.diameter / 2) ** 2,
                        support_type=SupportType.TREE,
                        interface_layers=[]
                    )
                    self.support_volumes.append(volume)

            # Create branch meshes
            for child in pillar.child_pillars:
                branch_mesh = self._create_tapered_pillar_mesh(
                    child,
                    base_diameter=child.diameter,
                    top_diameter=child.diameter * 0.6
                )

                if branch_mesh:
                    volume = SupportVolume(
                        mesh=branch_mesh,
                        volume=branch_mesh.volume,
                        contact_area=np.pi * (child.diameter / 2) ** 2,
                        support_type=SupportType.TREE,
                        interface_layers=[]
                    )
                    self.support_volumes.append(volume)

    def _generate_organic_supports(self):
        """Generate organic/natural looking supports."""
        # Similar to tree but with curved branches
        self._generate_tree_supports()

        # Apply smoothing to branches
        for volume in self.support_volumes:
            if volume.support_type == SupportType.TREE:
                # Smooth the mesh for organic appearance
                volume.mesh = volume.mesh.smoothed()

    def _generate_slim_supports(self):
        """Generate slim/minimal supports."""
        for point in self.support_points:
            # Create thin support pillar
            base_z = 0
            if self.settings.support_everywhere:
                base_z = self._find_support_base(point.position)

            base_position = np.array([point.position[0], point.position[1], base_z])
            top_position = point.position - point.normal * self.settings.support_z_distance

            # Use minimal diameter
            min_diameter = 1.0  # mm

            pillar = SupportPillar(
                base_position=base_position,
                top_position=top_position,
                diameter=min_diameter
            )
            self.support_pillars.append(pillar)

            # Create slim support mesh
            support_mesh = self._create_pillar_mesh(pillar)
            if support_mesh:
                volume = SupportVolume(
                    mesh=support_mesh,
                    volume=support_mesh.volume,
                    contact_area=np.pi * (min_diameter / 2) ** 2,
                    support_type=SupportType.SLIM,
                    interface_layers=[]
                )
                self.support_volumes.append(volume)

    def _generate_support_interfaces(self):
        """Generate support interface layers."""
        for volume in self.support_volumes:
            # Generate top interface (roof)
            if self.settings.support_roof_enable:
                roof_layers = self._generate_interface_layers(
                    volume.mesh,
                    self.settings.support_interface_layers,
                    is_roof=True
                )
                volume.interface_layers.extend(roof_layers)

            # Generate bottom interface (floor)
            if self.settings.support_floor_enable:
                floor_layers = self._generate_interface_layers(
                    volume.mesh,
                    self.settings.support_interface_layers,
                    is_roof=False
                )
                volume.interface_layers.extend(floor_layers)

    def _generate_interface_layers(self, support_mesh: trimesh.Trimesh,
                                  layer_count: int, is_roof: bool) -> List[np.ndarray]:
        """Generate interface layers for support."""
        layers = []
        layer_height = 0.2  # Default layer height

        for i in range(layer_count):
            if is_roof:
                z = support_mesh.bounds[1][2] - i * layer_height
            else:
                z = support_mesh.bounds[0][2] + i * layer_height

            # Create interface layer at height
            section = support_mesh.section(plane_origin=[0, 0, z],
                                          plane_normal=[0, 0, 1])
            if section:
                layers.append(section.vertices)

        return layers

    def _optimize_supports(self):
        """Optimize support structures."""
        # Remove redundant supports
        self._remove_redundant_supports()

        # Merge nearby supports
        self._merge_nearby_supports()

        # Add conical base if enabled
        if self.settings.conical_support_enable:
            self._add_conical_bases()

        # Add support brim if enabled
        if self.settings.support_brim_enable:
            self._add_support_brim()

    def _remove_redundant_supports(self):
        """Remove redundant support structures."""
        # Check for overlapping supports
        to_remove = []

        for i, vol1 in enumerate(self.support_volumes):
            for j, vol2 in enumerate(self.support_volumes[i+1:], i+1):
                # Check if volumes overlap significantly
                if self._volumes_overlap(vol1, vol2):
                    # Remove smaller volume
                    if vol1.volume < vol2.volume:
                        to_remove.append(i)
                    else:
                        to_remove.append(j)

        # Remove marked volumes
        for idx in sorted(set(to_remove), reverse=True):
            if idx < len(self.support_volumes):
                del self.support_volumes[idx]

    def _volumes_overlap(self, vol1: SupportVolume, vol2: SupportVolume) -> bool:
        """Check if two support volumes overlap."""
        # Simplified check using bounding boxes
        bounds1 = vol1.mesh.bounds
        bounds2 = vol2.mesh.bounds

        # Check if bounding boxes overlap
        return not (bounds1[1][0] < bounds2[0][0] or bounds2[1][0] < bounds1[0][0] or
                   bounds1[1][1] < bounds2[0][1] or bounds2[1][1] < bounds1[0][1] or
                   bounds1[1][2] < bounds2[0][2] or bounds2[1][2] < bounds1[0][2])

    def _merge_nearby_supports(self):
        """Merge nearby support structures."""
        merge_distance = 2.0  # mm

        merged_volumes = []
        processed = set()

        for i, volume in enumerate(self.support_volumes):
            if i in processed:
                continue

            # Find nearby volumes
            nearby = []
            for j, other in enumerate(self.support_volumes[i+1:], i+1):
                if j not in processed:
                    # Check distance between volumes
                    dist = np.linalg.norm(
                        volume.mesh.centroid - other.mesh.centroid
                    )
                    if dist < merge_distance:
                        nearby.append(j)

            if nearby:
                # Merge volumes
                meshes = [volume.mesh] + [self.support_volumes[j].mesh for j in nearby]
                merged_mesh = trimesh.util.concatenate(meshes)

                merged_volume = SupportVolume(
                    mesh=merged_mesh,
                    volume=merged_mesh.volume,
                    contact_area=volume.contact_area + sum(
                        self.support_volumes[j].contact_area for j in nearby
                    ),
                    support_type=volume.support_type,
                    interface_layers=volume.interface_layers
                )
                merged_volumes.append(merged_volume)

                processed.add(i)
                processed.update(nearby)
            else:
                merged_volumes.append(volume)
                processed.add(i)

        self.support_volumes = merged_volumes

    def _add_conical_bases(self):
        """Add conical bases to supports for stability."""
        for pillar in self.support_pillars:
            if pillar.base_position[2] == 0:  # On build plate
                # Create conical base
                cone = self._create_cone_mesh(
                    base_center=pillar.base_position,
                    base_radius=pillar.diameter * 2,
                    top_radius=pillar.diameter / 2,
                    height=min(5.0, pillar.top_position[2] / 2)
                )

                if cone:
                    volume = SupportVolume(
                        mesh=cone,
                        volume=cone.volume,
                        contact_area=np.pi * (pillar.diameter * 2) ** 2,
                        support_type=self.settings.support_type,
                        interface_layers=[]
                    )
                    self.support_volumes.append(volume)

    def _add_support_brim(self):
        """Add brim around support bases."""
        brim_meshes = []

        for volume in self.support_volumes:
            # Check if volume touches build plate
            if volume.mesh.bounds[0][2] < 0.1:
                # Create brim around base
                base_outline = self._get_base_outline(volume.mesh)
                if base_outline:
                    brim = self._create_brim_mesh(
                        base_outline,
                        self.settings.support_brim_width
                    )
                    if brim:
                        brim_meshes.append(brim)

        # Combine all brims
        if brim_meshes:
            combined_brim = trimesh.util.concatenate(brim_meshes)
            volume = SupportVolume(
                mesh=combined_brim,
                volume=combined_brim.volume,
                contact_area=combined_brim.area,
                support_type=self.settings.support_type,
                interface_layers=[]
            )
            self.support_volumes.append(volume)

    def _find_support_base(self, position: np.ndarray) -> float:
        """Find suitable base height for support."""
        # Cast ray downward to find surface
        ray_origin = position
        ray_direction = np.array([0, 0, -1])

        locations, index_ray, index_tri = self.mesh.ray.intersects_location(
            ray_origins=[ray_origin],
            ray_directions=[ray_direction]
        )

        if locations.size > 0:
            # Find closest surface below
            below_locations = locations[locations[:, 2] < position[2] - 1.0]
            if below_locations.size > 0:
                return np.max(below_locations[:, 2])

        return 0  # Default to build plate

    def _calculate_pillar_diameter(self, contact_area: float) -> float:
        """Calculate appropriate pillar diameter based on contact area."""
        # Base diameter on contact area and density
        base_diameter = np.sqrt(contact_area / np.pi) * 2

        # Apply density factor
        density_factor = self.settings.support_density / 100
        diameter = base_diameter * (0.5 + density_factor)

        # Clamp to reasonable range
        return np.clip(diameter, 1.0, self.settings.support_tower_maximum_diameter)

    def _create_pillar_mesh(self, pillar: SupportPillar) -> Optional[trimesh.Trimesh]:
        """Create mesh for support pillar."""
        try:
            height = np.linalg.norm(pillar.top_position - pillar.base_position)
            if height < 0.1:
                return None

            # Create cylinder
            cylinder = trimesh.creation.cylinder(
                radius=pillar.diameter / 2,
                height=height,
                sections=8
            )

            # Position cylinder
            center = (pillar.base_position + pillar.top_position) / 2
            cylinder.apply_translation(center)

            # Align cylinder with pillar direction
            direction = pillar.top_position - pillar.base_position
            direction = direction / np.linalg.norm(direction)

            if not np.allclose(direction, [0, 0, 1]):
                # Calculate rotation to align with direction
                z_axis = np.array([0, 0, 1])
                axis = np.cross(z_axis, direction)
                angle = np.arccos(np.dot(z_axis, direction))

                if np.linalg.norm(axis) > 0:
                    axis = axis / np.linalg.norm(axis)
                    rotation_matrix = trimesh.transformations.rotation_matrix(
                        angle, axis, center
                    )
                    cylinder.apply_transform(rotation_matrix)

            return cylinder

        except Exception as e:
            self.logger.warning(f"Failed to create pillar mesh: {e}")
            return None

    def _create_tapered_pillar_mesh(self, pillar: SupportPillar,
                                   base_diameter: float,
                                   top_diameter: float) -> Optional[trimesh.Trimesh]:
        """Create tapered mesh for support pillar."""
        try:
            height = np.linalg.norm(pillar.top_position - pillar.base_position)
            if height < 0.1:
                return None

            # Create tapered cylinder (frustum)
            cone = trimesh.creation.cone(
                radius=base_diameter / 2,
                height=height
            )

            # Scale top to create taper
            scale_factor = top_diameter / base_diameter
            transform = np.eye(4)
            transform[0, 0] = 1 - (1 - scale_factor) * (cone.vertices[:, 2] / height).reshape(-1, 1)
            transform[1, 1] = transform[0, 0]

            # Apply transformation
            for i, vertex in enumerate(cone.vertices):
                z_ratio = vertex[2] / height
                scale = 1 - (1 - scale_factor) * z_ratio
                cone.vertices[i, 0] *= scale
                cone.vertices[i, 1] *= scale

            # Position cone
            center = (pillar.base_position + pillar.top_position) / 2
            cone.apply_translation(center)

            return cone

        except Exception as e:
            self.logger.warning(f"Failed to create tapered pillar mesh: {e}")
            return None

    def _create_cone_mesh(self, base_center: np.ndarray, base_radius: float,
                         top_radius: float, height: float) -> Optional[trimesh.Trimesh]:
        """Create cone mesh for conical support base."""
        try:
            cone = trimesh.creation.cone(radius=base_radius, height=height)

            # Scale top
            for vertex in cone.vertices:
                if vertex[2] > height * 0.9:
                    scale = top_radius / base_radius
                    vertex[0] *= scale
                    vertex[1] *= scale

            # Position cone
            cone.apply_translation(base_center + np.array([0, 0, height/2]))

            return cone

        except:
            return None

    def _get_base_outline(self, mesh: trimesh.Trimesh) -> Optional[np.ndarray]:
        """Get outline of mesh base."""
        try:
            # Get bottom slice
            z_min = mesh.bounds[0][2]
            section = mesh.section(plane_origin=[0, 0, z_min + 0.01],
                                  plane_normal=[0, 0, 1])
            if section:
                return section.vertices
            return None
        except:
            return None

    def _create_brim_mesh(self, outline: np.ndarray, width: float) -> Optional[trimesh.Trimesh]:
        """Create brim mesh from outline."""
        try:
            from shapely.geometry import Polygon

            # Create polygon from outline
            poly = Polygon(outline[:, :2])

            # Offset outward
            brim_poly = poly.buffer(width)

            # Create thin mesh from polygon
            # This is simplified - production would create proper mesh
            vertices = []
            faces = []

            # Add vertices for outer and inner rings
            outer_coords = list(brim_poly.exterior.coords)
            inner_coords = list(poly.exterior.coords)

            for coord in outer_coords:
                vertices.append([coord[0], coord[1], 0])
            for coord in inner_coords:
                vertices.append([coord[0], coord[1], 0.2])  # Thin brim

            # Create faces connecting rings
            # Simplified triangulation
            n = len(outer_coords)
            for i in range(n - 1):
                faces.append([i, i + n, i + 1])
                faces.append([i + 1, i + n, i + n + 1])

            return trimesh.Trimesh(vertices=vertices, faces=faces)

        except:
            return None

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate support generation statistics."""
        stats = {
            'support_point_count': len(self.support_points),
            'support_pillar_count': len(self.support_pillars),
            'support_volume_count': len(self.support_volumes),
            'tree_branch_count': sum(1 for p in self.support_pillars if p.is_tree_branch),
            'total_contact_points': len(self.support_points),
            'average_overhang_angle': np.mean([p.overhang_angle for p in self.support_points]) if self.support_points else 0,
            'support_type': self.settings.support_type.value,
            'support_density': self.settings.support_density,
        }

        return stats