"""Precision measurement and analysis tools for 3D printing."""

import numpy as np
import trimesh
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from scipy.spatial import KDTree, ConvexHull
from scipy.spatial.distance import cdist
import math

@dataclass
class MeasurementPoint:
    """3D measurement point with metadata."""
    position: np.ndarray
    normal: Optional[np.ndarray] = None
    surface_id: Optional[int] = None
    uncertainty: float = 0.0

@dataclass
class DistanceMeasurement:
    """Distance measurement result."""
    distance: float
    point1: MeasurementPoint
    point2: MeasurementPoint
    measurement_type: str  # 'point_to_point', 'point_to_line', 'point_to_plane'
    accuracy: float
    notes: str = ""

@dataclass
class AngleMeasurement:
    """Angle measurement result."""
    angle_degrees: float
    angle_radians: float
    vertex: MeasurementPoint
    point1: MeasurementPoint
    point2: MeasurementPoint
    measurement_type: str  # 'three_point', 'edge_angle', 'dihedral'
    accuracy: float
    notes: str = ""

@dataclass
class RadiusMeasurement:
    """Radius/curvature measurement result."""
    radius: float
    center: MeasurementPoint
    circle_points: List[MeasurementPoint]
    measurement_type: str  # 'arc', 'circle', 'sphere'
    fit_error: float
    notes: str = ""

@dataclass
class ToleranceAnalysis:
    """Tolerance analysis result."""
    nominal_dimension: float
    actual_dimension: float
    tolerance_zone: Tuple[float, float]
    deviation: float
    within_tolerance: bool
    confidence_level: float

class PrecisionMeasurementEngine:
    """High-precision measurement engine for 3D models."""

    def __init__(self, precision: float = 0.001):
        self.precision = precision
        self.measurement_history = []

    def measure_distance_point_to_point(self, mesh: trimesh.Trimesh,
                                       point1: np.ndarray,
                                       point2: np.ndarray) -> DistanceMeasurement:
        """Measure distance between two points."""

        # Find closest surface points
        surface_point1 = self._find_closest_surface_point(mesh, point1)
        surface_point2 = self._find_closest_surface_point(mesh, point2)

        # Calculate distance
        distance = np.linalg.norm(surface_point2.position - surface_point1.position)

        # Estimate measurement accuracy
        accuracy = self._estimate_measurement_accuracy(
            mesh, [surface_point1.position, surface_point2.position]
        )

        measurement = DistanceMeasurement(
            distance=distance,
            point1=surface_point1,
            point2=surface_point2,
            measurement_type='point_to_point',
            accuracy=accuracy
        )

        self.measurement_history.append(measurement)
        return measurement

    def measure_distance_point_to_line(self, mesh: trimesh.Trimesh,
                                      point: np.ndarray,
                                      line_start: np.ndarray,
                                      line_end: np.ndarray) -> DistanceMeasurement:
        """Measure distance from point to line."""

        surface_point = self._find_closest_surface_point(mesh, point)

        # Calculate distance from point to line
        line_vector = line_end - line_start
        point_vector = surface_point.position - line_start

        # Project point onto line
        line_length_sq = np.dot(line_vector, line_vector)
        if line_length_sq < 1e-10:
            # Line is a point
            closest_on_line = line_start
        else:
            t = np.dot(point_vector, line_vector) / line_length_sq
            t = max(0, min(1, t))  # Clamp to line segment
            closest_on_line = line_start + t * line_vector

        distance = np.linalg.norm(surface_point.position - closest_on_line)

        line_point = MeasurementPoint(
            position=closest_on_line,
            normal=None
        )

        accuracy = self._estimate_measurement_accuracy(
            mesh, [surface_point.position, closest_on_line]
        )

        measurement = DistanceMeasurement(
            distance=distance,
            point1=surface_point,
            point2=line_point,
            measurement_type='point_to_line',
            accuracy=accuracy
        )

        self.measurement_history.append(measurement)
        return measurement

    def measure_distance_point_to_plane(self, mesh: trimesh.Trimesh,
                                       point: np.ndarray,
                                       plane_point: np.ndarray,
                                       plane_normal: np.ndarray) -> DistanceMeasurement:
        """Measure distance from point to plane."""

        surface_point = self._find_closest_surface_point(mesh, point)

        # Normalize plane normal
        plane_normal = plane_normal / np.linalg.norm(plane_normal)

        # Calculate distance to plane
        point_to_plane_vector = surface_point.position - plane_point
        distance = abs(np.dot(point_to_plane_vector, plane_normal))

        # Find closest point on plane
        closest_on_plane = surface_point.position - np.dot(point_to_plane_vector, plane_normal) * plane_normal

        plane_measurement_point = MeasurementPoint(
            position=closest_on_plane,
            normal=plane_normal
        )

        accuracy = self._estimate_measurement_accuracy(
            mesh, [surface_point.position, closest_on_plane]
        )

        measurement = DistanceMeasurement(
            distance=distance,
            point1=surface_point,
            point2=plane_measurement_point,
            measurement_type='point_to_plane',
            accuracy=accuracy
        )

        self.measurement_history.append(measurement)
        return measurement

    def measure_angle_three_points(self, mesh: trimesh.Trimesh,
                                  point1: np.ndarray,
                                  vertex: np.ndarray,
                                  point2: np.ndarray) -> AngleMeasurement:
        """Measure angle defined by three points."""

        # Find closest surface points
        surface_point1 = self._find_closest_surface_point(mesh, point1)
        surface_vertex = self._find_closest_surface_point(mesh, vertex)
        surface_point2 = self._find_closest_surface_point(mesh, point2)

        # Calculate vectors
        vec1 = surface_point1.position - surface_vertex.position
        vec2 = surface_point2.position - surface_vertex.position

        # Calculate angle
        cos_angle = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        cos_angle = np.clip(cos_angle, -1, 1)  # Handle numerical errors
        angle_radians = np.arccos(cos_angle)
        angle_degrees = np.degrees(angle_radians)

        accuracy = self._estimate_angle_accuracy(mesh, [point1, vertex, point2])

        measurement = AngleMeasurement(
            angle_degrees=angle_degrees,
            angle_radians=angle_radians,
            vertex=surface_vertex,
            point1=surface_point1,
            point2=surface_point2,
            measurement_type='three_point',
            accuracy=accuracy
        )

        self.measurement_history.append(measurement)
        return measurement

    def measure_edge_angle(self, mesh: trimesh.Trimesh,
                          edge_start: np.ndarray,
                          edge_end: np.ndarray) -> AngleMeasurement:
        """Measure dihedral angle at an edge."""

        # Find edge in mesh
        edge_midpoint = (edge_start + edge_end) / 2
        closest_face_indices = self._find_faces_near_point(mesh, edge_midpoint, radius=self.precision * 10)

        if len(closest_face_indices) < 2:
            raise ValueError("Could not find adjacent faces for edge angle measurement")

        # Get normals of adjacent faces
        face1_normal = mesh.face_normals[closest_face_indices[0]]
        face2_normal = mesh.face_normals[closest_face_indices[1]]

        # Calculate dihedral angle
        cos_angle = np.dot(face1_normal, face2_normal)
        cos_angle = np.clip(cos_angle, -1, 1)
        angle_radians = np.arccos(cos_angle)
        angle_degrees = np.degrees(angle_radians)

        # Interior angle is π - dihedral angle for convex edges
        interior_angle_degrees = 180 - angle_degrees
        interior_angle_radians = np.pi - angle_radians

        vertex_point = MeasurementPoint(position=edge_midpoint)
        point1 = MeasurementPoint(position=edge_start)
        point2 = MeasurementPoint(position=edge_end)

        accuracy = self._estimate_angle_accuracy(mesh, [edge_start, edge_midpoint, edge_end])

        measurement = AngleMeasurement(
            angle_degrees=interior_angle_degrees,
            angle_radians=interior_angle_radians,
            vertex=vertex_point,
            point1=point1,
            point2=point2,
            measurement_type='edge_angle',
            accuracy=accuracy
        )

        self.measurement_history.append(measurement)
        return measurement

    def measure_radius_from_points(self, mesh: trimesh.Trimesh,
                                  points: List[np.ndarray]) -> RadiusMeasurement:
        """Measure radius by fitting circle/sphere to points."""

        if len(points) < 3:
            raise ValueError("Need at least 3 points for radius measurement")

        # Find closest surface points
        surface_points = [self._find_closest_surface_point(mesh, p) for p in points]

        if len(points) == 3:
            # Fit circle through 3 points
            center, radius, fit_error = self._fit_circle_3_points(
                [p.position for p in surface_points]
            )
            measurement_type = 'circle'
        else:
            # Fit circle/sphere to multiple points
            if self._points_are_coplanar([p.position for p in surface_points]):
                center, radius, fit_error = self._fit_circle_least_squares(
                    [p.position for p in surface_points]
                )
                measurement_type = 'circle'
            else:
                center, radius, fit_error = self._fit_sphere_least_squares(
                    [p.position for p in surface_points]
                )
                measurement_type = 'sphere'

        center_point = MeasurementPoint(position=center)

        measurement = RadiusMeasurement(
            radius=radius,
            center=center_point,
            circle_points=surface_points,
            measurement_type=measurement_type,
            fit_error=fit_error
        )

        self.measurement_history.append(measurement)
        return measurement

    def measure_wall_thickness(self, mesh: trimesh.Trimesh,
                              point: np.ndarray,
                              direction: Optional[np.ndarray] = None) -> DistanceMeasurement:
        """Measure wall thickness at a point."""

        surface_point = self._find_closest_surface_point(mesh, point)

        if direction is None:
            # Use surface normal as direction
            direction = surface_point.normal
            if direction is None:
                # Estimate normal from nearby faces
                direction = self._estimate_surface_normal(mesh, surface_point.position)

        # Cast ray in both directions
        ray_origins = np.array([
            surface_point.position + direction * self.precision,
            surface_point.position - direction * self.precision
        ])
        ray_directions = np.array([direction, -direction])

        # Find intersections
        locations, index_ray, index_tri = mesh.ray.intersects_location(
            ray_origins, ray_directions
        )

        if len(locations) >= 2:
            # Find closest opposite surface
            distances = np.linalg.norm(locations - surface_point.position, axis=1)
            opposite_idx = np.argmin(distances[distances > self.precision])
            opposite_point = locations[opposite_idx]

            thickness = np.linalg.norm(opposite_point - surface_point.position)

            opposite_measurement_point = MeasurementPoint(position=opposite_point)

            accuracy = self._estimate_measurement_accuracy(
                mesh, [surface_point.position, opposite_point]
            )

            measurement = DistanceMeasurement(
                distance=thickness,
                point1=surface_point,
                point2=opposite_measurement_point,
                measurement_type='wall_thickness',
                accuracy=accuracy,
                notes="Wall thickness measurement"
            )

            self.measurement_history.append(measurement)
            return measurement

        raise ValueError("Could not find opposite surface for wall thickness measurement")

    def analyze_tolerance(self, nominal: float, actual: float,
                         tolerance_plus: float, tolerance_minus: float,
                         confidence: float = 0.95) -> ToleranceAnalysis:
        """Analyze dimensional tolerance."""

        upper_limit = nominal + tolerance_plus
        lower_limit = nominal - tolerance_minus
        deviation = actual - nominal

        within_tolerance = lower_limit <= actual <= upper_limit

        return ToleranceAnalysis(
            nominal_dimension=nominal,
            actual_dimension=actual,
            tolerance_zone=(lower_limit, upper_limit),
            deviation=deviation,
            within_tolerance=within_tolerance,
            confidence_level=confidence
        )

    def measure_surface_roughness(self, mesh: trimesh.Trimesh,
                                 center_point: np.ndarray,
                                 sample_radius: float = 1.0) -> Dict[str, float]:
        """Measure surface roughness in a local area."""

        # Find vertices in sample area
        distances = np.linalg.norm(mesh.vertices - center_point, axis=1)
        sample_indices = np.where(distances <= sample_radius)[0]

        if len(sample_indices) < 10:
            raise ValueError("Not enough sample points for roughness measurement")

        sample_points = mesh.vertices[sample_indices]

        # Fit plane to sample points
        centroid = np.mean(sample_points, axis=0)
        centered_points = sample_points - centroid

        # SVD to find best fit plane
        u, s, vt = np.linalg.svd(centered_points)
        normal = vt[-1]

        # Calculate deviations from plane
        deviations = np.abs(np.dot(centered_points, normal))

        # Calculate roughness parameters
        ra = np.mean(deviations)  # Average roughness
        rq = np.sqrt(np.mean(deviations ** 2))  # RMS roughness
        rz = np.max(deviations) - np.min(deviations)  # Peak-to-valley

        return {
            'Ra': ra,  # Average roughness
            'Rq': rq,  # RMS roughness
            'Rz': rz,  # Peak-to-valley height
            'sample_count': len(sample_indices),
            'sample_area': np.pi * sample_radius ** 2
        }

    def measure_flatness(self, mesh: trimesh.Trimesh,
                        points: List[np.ndarray]) -> Dict[str, float]:
        """Measure flatness of a surface defined by points."""

        if len(points) < 4:
            raise ValueError("Need at least 4 points for flatness measurement")

        surface_points = [self._find_closest_surface_point(mesh, p) for p in points]
        positions = np.array([p.position for p in surface_points])

        # Fit best-fit plane
        centroid = np.mean(positions, axis=0)
        centered_points = positions - centroid

        u, s, vt = np.linalg.svd(centered_points)
        normal = vt[-1]

        # Calculate deviations from plane
        deviations = np.dot(centered_points, normal)
        flatness = np.max(deviations) - np.min(deviations)

        return {
            'flatness': flatness,
            'max_deviation': np.max(np.abs(deviations)),
            'rms_deviation': np.sqrt(np.mean(deviations ** 2)),
            'plane_normal': normal.tolist(),
            'plane_center': centroid.tolist()
        }

    def measure_cylindricity(self, mesh: trimesh.Trimesh,
                           axis_start: np.ndarray,
                           axis_end: np.ndarray,
                           sample_radius: float = 2.0) -> Dict[str, float]:
        """Measure cylindricity of a cylindrical surface."""

        axis_vector = axis_end - axis_start
        axis_length = np.linalg.norm(axis_vector)
        axis_unit = axis_vector / axis_length

        # Find points near the axis
        axis_center = (axis_start + axis_end) / 2
        distances_to_center = np.linalg.norm(mesh.vertices - axis_center, axis=1)
        candidate_indices = np.where(distances_to_center <= sample_radius * 2)[0]

        # Filter points by distance to axis line
        sample_points = []
        for idx in candidate_indices:
            vertex = mesh.vertices[idx]
            # Distance from point to axis line
            point_to_start = vertex - axis_start
            projection_length = np.dot(point_to_start, axis_unit)

            if 0 <= projection_length <= axis_length:
                projection_point = axis_start + projection_length * axis_unit
                radial_distance = np.linalg.norm(vertex - projection_point)

                if radial_distance <= sample_radius:
                    sample_points.append({
                        'position': vertex,
                        'radial_distance': radial_distance,
                        'axial_position': projection_length
                    })

        if len(sample_points) < 10:
            raise ValueError("Not enough sample points for cylindricity measurement")

        # Calculate cylindricity
        radial_distances = [p['radial_distance'] for p in sample_points]
        cylindricity = max(radial_distances) - min(radial_distances)
        average_radius = np.mean(radial_distances)

        return {
            'cylindricity': cylindricity,
            'average_radius': average_radius,
            'max_radius': max(radial_distances),
            'min_radius': min(radial_distances),
            'sample_count': len(sample_points)
        }

    # Helper methods
    def _find_closest_surface_point(self, mesh: trimesh.Trimesh,
                                   point: np.ndarray) -> MeasurementPoint:
        """Find closest point on mesh surface."""

        closest_point, distance, face_id = mesh.nearest.on_surface([point])

        # Get surface normal at closest point
        face_normal = mesh.face_normals[face_id[0]]

        return MeasurementPoint(
            position=closest_point[0],
            normal=face_normal,
            surface_id=face_id[0],
            uncertainty=distance[0]
        )

    def _find_faces_near_point(self, mesh: trimesh.Trimesh,
                              point: np.ndarray,
                              radius: float) -> List[int]:
        """Find face indices near a point."""

        face_centers = mesh.triangles_center
        distances = np.linalg.norm(face_centers - point, axis=1)
        return np.where(distances <= radius)[0].tolist()

    def _estimate_surface_normal(self, mesh: trimesh.Trimesh,
                                point: np.ndarray) -> np.ndarray:
        """Estimate surface normal at a point."""

        nearby_faces = self._find_faces_near_point(mesh, point, self.precision * 5)

        if nearby_faces:
            # Average normals of nearby faces
            normals = mesh.face_normals[nearby_faces]
            return np.mean(normals, axis=0)

        # Fallback: use closest face normal
        _, _, face_id = mesh.nearest.on_surface([point])
        return mesh.face_normals[face_id[0]]

    def _estimate_measurement_accuracy(self, mesh: trimesh.Trimesh,
                                     points: List[np.ndarray]) -> float:
        """Estimate measurement accuracy based on mesh resolution."""

        # Find average edge length near measurement points
        edge_lengths = []

        for point in points:
            nearby_faces = self._find_faces_near_point(mesh, point, self.precision * 10)
            for face_idx in nearby_faces[:5]:  # Sample few faces
                face = mesh.faces[face_idx]
                for i in range(3):
                    edge = mesh.vertices[face[(i+1)%3]] - mesh.vertices[face[i]]
                    edge_lengths.append(np.linalg.norm(edge))

        if edge_lengths:
            avg_edge_length = np.mean(edge_lengths)
            return max(self.precision, avg_edge_length / 10)

        return self.precision

    def _estimate_angle_accuracy(self, mesh: trimesh.Trimesh,
                                points: List[np.ndarray]) -> float:
        """Estimate angle measurement accuracy."""

        linear_accuracy = self._estimate_measurement_accuracy(mesh, points)

        # Convert linear accuracy to angular accuracy (rough estimate)
        # For small angles, angular error ≈ linear error / distance
        distances = [np.linalg.norm(points[i] - points[0])
                    for i in range(1, len(points))]

        if distances:
            avg_distance = np.mean(distances)
            angular_accuracy_rad = linear_accuracy / avg_distance
            return np.degrees(angular_accuracy_rad)

        return 0.1  # Default 0.1 degree accuracy

    def _fit_circle_3_points(self, points: List[np.ndarray]) -> Tuple[np.ndarray, float, float]:
        """Fit circle through exactly 3 points."""

        p1, p2, p3 = points

        # Check if points are collinear
        v1 = p2 - p1
        v2 = p3 - p1
        cross = np.cross(v1, v2)

        if np.linalg.norm(cross) < 1e-10:
            raise ValueError("Points are collinear, cannot fit circle")

        # Calculate circumcenter
        ax, ay = p1[0], p1[1]
        bx, by = p2[0], p2[1]
        cx, cy = p3[0], p3[1]

        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))

        if abs(d) < 1e-10:
            raise ValueError("Cannot calculate circle center")

        ux = ((ax*ax + ay*ay) * (by - cy) + (bx*bx + by*by) * (cy - ay) + (cx*cx + cy*cy) * (ay - by)) / d
        uy = ((ax*ax + ay*ay) * (cx - bx) + (bx*bx + by*by) * (ax - cx) + (cx*cx + cy*cy) * (bx - ax)) / d

        center = np.array([ux, uy, (p1[2] + p2[2] + p3[2]) / 3])
        radius = np.linalg.norm(center[:2] - p1[:2])

        # Calculate fit error
        distances = [abs(np.linalg.norm(center[:2] - p[:2]) - radius) for p in points]
        fit_error = max(distances)

        return center, radius, fit_error

    def _fit_circle_least_squares(self, points: List[np.ndarray]) -> Tuple[np.ndarray, float, float]:
        """Fit circle using least squares method."""

        # Convert to 2D for circle fitting
        points_2d = np.array([[p[0], p[1]] for p in points])

        # Initial guess: centroid and average distance
        centroid = np.mean(points_2d, axis=0)
        distances = np.linalg.norm(points_2d - centroid, axis=1)
        initial_radius = np.mean(distances)

        # Algebraic circle fit
        x = points_2d[:, 0]
        y = points_2d[:, 1]

        # Set up system: (x-a)² + (y-b)² = r²
        # Expanded: x² + y² - 2ax - 2by + a² + b² - r² = 0
        A = np.column_stack([x, y, np.ones(len(x))])
        b = x**2 + y**2

        try:
            coeffs = np.linalg.lstsq(A, b, rcond=None)[0]
            center_x = coeffs[0] / 2
            center_y = coeffs[1] / 2
            radius = np.sqrt(coeffs[2] + center_x**2 + center_y**2)

            center = np.array([center_x, center_y, np.mean([p[2] for p in points])])

            # Calculate fit error
            distances = np.linalg.norm(points_2d - center[:2], axis=1)
            fit_error = np.std(distances)

            return center, radius, fit_error

        except np.linalg.LinAlgError:
            # Fallback to centroid method
            radius = np.mean(np.linalg.norm(points_2d - centroid, axis=1))
            center = np.array([centroid[0], centroid[1], np.mean([p[2] for p in points])])
            distances = np.linalg.norm(points_2d - centroid, axis=1)
            fit_error = np.std(distances)

            return center, radius, fit_error

    def _fit_sphere_least_squares(self, points: List[np.ndarray]) -> Tuple[np.ndarray, float, float]:
        """Fit sphere using least squares method."""

        points_array = np.array(points)

        # Initial guess
        centroid = np.mean(points_array, axis=0)
        distances = np.linalg.norm(points_array - centroid, axis=1)
        initial_radius = np.mean(distances)

        # Algebraic sphere fit
        x = points_array[:, 0]
        y = points_array[:, 1]
        z = points_array[:, 2]

        A = np.column_stack([x, y, z, np.ones(len(x))])
        b = x**2 + y**2 + z**2

        try:
            coeffs = np.linalg.lstsq(A, b, rcond=None)[0]
            center = coeffs[:3] / 2
            radius = np.sqrt(coeffs[3] + np.sum(center**2))

            # Calculate fit error
            distances = np.linalg.norm(points_array - center, axis=1)
            fit_error = np.std(distances)

            return center, radius, fit_error

        except np.linalg.LinAlgError:
            # Fallback to centroid method
            radius = np.mean(distances)
            distances = np.linalg.norm(points_array - centroid, axis=1)
            fit_error = np.std(distances)

            return centroid, radius, fit_error

    def _points_are_coplanar(self, points: List[np.ndarray], tolerance: float = 1e-6) -> bool:
        """Check if points are approximately coplanar."""

        if len(points) < 4:
            return True

        points_array = np.array(points)
        centroid = np.mean(points_array, axis=0)
        centered = points_array - centroid

        # SVD to find principal components
        u, s, vt = np.linalg.svd(centered)

        # If smallest singular value is near zero, points are coplanar
        return s[-1] < tolerance * s[0]

    def get_measurement_report(self) -> Dict[str, Any]:
        """Generate comprehensive measurement report."""

        if not self.measurement_history:
            return {'error': 'No measurements recorded'}

        distance_measurements = [m for m in self.measurement_history if isinstance(m, DistanceMeasurement)]
        angle_measurements = [m for m in self.measurement_history if isinstance(m, AngleMeasurement)]
        radius_measurements = [m for m in self.measurement_history if isinstance(m, RadiusMeasurement)]

        report = {
            'summary': {
                'total_measurements': len(self.measurement_history),
                'distance_measurements': len(distance_measurements),
                'angle_measurements': len(angle_measurements),
                'radius_measurements': len(radius_measurements)
            },
            'precision_settings': {
                'measurement_precision': self.precision
            },
            'measurements': {
                'distances': [
                    {
                        'distance': m.distance,
                        'type': m.measurement_type,
                        'accuracy': m.accuracy,
                        'notes': m.notes
                    } for m in distance_measurements
                ],
                'angles': [
                    {
                        'angle_degrees': m.angle_degrees,
                        'type': m.measurement_type,
                        'accuracy': m.accuracy,
                        'notes': m.notes
                    } for m in angle_measurements
                ],
                'radii': [
                    {
                        'radius': m.radius,
                        'type': m.measurement_type,
                        'fit_error': m.fit_error,
                        'notes': m.notes
                    } for m in radius_measurements
                ]
            }
        }

        # Calculate statistics
        if distance_measurements:
            distances = [m.distance for m in distance_measurements]
            report['statistics'] = {
                'distance_stats': {
                    'min': min(distances),
                    'max': max(distances),
                    'mean': np.mean(distances),
                    'std': np.std(distances)
                }
            }

        return report