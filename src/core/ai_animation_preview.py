"""AI-powered animation and video preview for 3D models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union
import numpy as np
import trimesh
from enum import Enum
import logging
import time
import json


class AnimationType(Enum):
    """Types of animations for 3D model preview."""
    ROTATION = "rotation"
    ZOOM = "zoom"
    PAN = "pan"
    ORBIT = "orbit"
    EXPLODE = "explode"
    ASSEMBLY = "assembly"
    CROSS_SECTION = "cross_section"
    MORPHING = "morphing"
    TEXTURE_ANIMATION = "texture_animation"
    LIGHTING_ANIMATION = "lighting_animation"


class VideoQuality(Enum):
    """Video quality presets."""
    LOW = "low"          # 720p, 30fps
    MEDIUM = "medium"    # 1080p, 30fps
    HIGH = "high"        # 1080p, 60fps
    ULTRA = "ultra"      # 4K, 60fps


@dataclass
class CameraKeyframe:
    """A camera keyframe for animation."""

    time: float  # Time in seconds
    position: np.ndarray  # Camera position [x, y, z]
    target: np.ndarray    # Look-at target [x, y, z]
    up: np.ndarray = field(default_factory=lambda: np.array([0, 0, 1]))  # Up vector
    fov: float = 45.0    # Field of view in degrees


@dataclass
class AnimationSequence:
    """A sequence of animation keyframes."""

    name: str
    duration: float  # Total duration in seconds
    keyframes: List[CameraKeyframe] = field(default_factory=list)
    animation_type: AnimationType = AnimationType.ROTATION
    easing: str = "linear"  # linear, ease_in, ease_out, ease_in_out


@dataclass
class VideoSettings:
    """Settings for video generation."""

    width: int = 1920
    height: int = 1080
    fps: int = 30
    duration: float = 10.0  # seconds
    quality: VideoQuality = VideoQuality.MEDIUM
    format: str = "mp4"  # mp4, webm, gif
    background_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)  # RGBA


@dataclass
class AnimationResult:
    """Result of animation generation."""

    success: bool
    animation_data: Optional[Dict[str, Any]] = None
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    duration: float = 0.0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIAnimationPreview:
    """AI-powered 3D model animation and video preview system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_smart_preview(self, mesh: trimesh.Trimesh,
                             animation_type: AnimationType = AnimationType.ROTATION,
                             duration: float = 10.0) -> AnimationResult:
        """Generate an intelligent animation preview based on mesh analysis."""

        try:
            # Analyze mesh to determine optimal animation
            mesh_analysis = self._analyze_mesh_for_animation(mesh)

            # Generate appropriate animation sequence
            sequence = self._create_optimal_animation_sequence(
                mesh, mesh_analysis, animation_type, duration
            )

            # Convert to animation data
            animation_data = self._sequence_to_animation_data(sequence)

            result = AnimationResult(
                success=True,
                animation_data=animation_data,
                duration=duration,
                metadata={
                    "mesh_analysis": mesh_analysis,
                    "animation_type": animation_type.value,
                    "keyframes_count": len(sequence.keyframes)
                }
            )

            return result

        except Exception as e:
            self.logger.error(f"Error generating smart preview: {e}")
            return AnimationResult(
                success=False,
                errors=[str(e)]
            )

    def create_custom_animation(self, mesh: trimesh.Trimesh,
                              keyframes: List[CameraKeyframe],
                              settings: VideoSettings) -> AnimationResult:
        """Create a custom animation from user-defined keyframes."""

        try:
            sequence = AnimationSequence(
                name="Custom Animation",
                duration=max(kf.time for kf in keyframes),
                keyframes=keyframes,
                animation_type=AnimationType.ORBIT
            )

            animation_data = self._sequence_to_animation_data(sequence)

            result = AnimationResult(
                success=True,
                animation_data=animation_data,
                duration=sequence.duration,
                metadata={
                    "custom_keyframes": len(keyframes),
                    "video_settings": {
                        "width": settings.width,
                        "height": settings.height,
                        "fps": settings.fps
                    }
                }
            )

            return result

        except Exception as e:
            self.logger.error(f"Error creating custom animation: {e}")
            return AnimationResult(
                success=False,
                errors=[str(e)]
            )

    def generate_exploded_view(self, mesh: trimesh.Trimesh,
                             duration: float = 8.0) -> AnimationResult:
        """Generate an exploded view animation for assembly visualization."""

        try:
            # This would require mesh segmentation
            # For now, create a simple rotation animation
            sequence = self._create_rotation_animation(mesh, duration)

            animation_data = self._sequence_to_animation_data(sequence)
            animation_data["type"] = "exploded_view"

            result = AnimationResult(
                success=True,
                animation_data=animation_data,
                duration=duration,
                metadata={
                    "animation_type": "exploded_view",
                    "note": "Full exploded view requires mesh segmentation"
                }
            )

            return result

        except Exception as e:
            self.logger.error(f"Error generating exploded view: {e}")
            return AnimationResult(
                success=False,
                errors=[str(e)]
            )

    def create_cross_section_animation(self, mesh: trimesh.Trimesh,
                                     duration: float = 6.0) -> AnimationResult:
        """Create a cross-section reveal animation."""

        try:
            # Analyze mesh bounds for cutting plane
            bounds = mesh.bounds
            center = (bounds[0] + bounds[1]) / 2

            # Create keyframes that move a cutting plane through the model
            keyframes = []

            # Start position (before model)
            keyframes.append(CameraKeyframe(
                time=0.0,
                position=np.array([center[0], center[1] - 20, center[2]]),
                target=center
            ))

            # Move through model
            for i in range(11):  # 11 keyframes for smooth motion
                t = i / 10.0
                time_pos = t * duration
                y_pos = center[1] - 20 + t * 40  # Move from -20 to +20

                keyframes.append(CameraKeyframe(
                    time=time_pos,
                    position=np.array([center[0], y_pos, center[2]]),
                    target=center
                ))

            sequence = AnimationSequence(
                name="Cross Section",
                duration=duration,
                keyframes=keyframes,
                animation_type=AnimationType.CROSS_SECTION
            )

            animation_data = self._sequence_to_animation_data(sequence)

            result = AnimationResult(
                success=True,
                animation_data=animation_data,
                duration=duration,
                metadata={
                    "animation_type": "cross_section",
                    "cutting_plane": "YZ"
                }
            )

            return result

        except Exception as e:
            self.logger.error(f"Error creating cross-section animation: {e}")
            return AnimationResult(
                success=False,
                errors=[str(e)]
            )

    def _analyze_mesh_for_animation(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """Analyze mesh properties for optimal animation generation."""

        analysis = {}

        try:
            bounds = mesh.bounds
            dimensions = bounds[1] - bounds[0]
            center = (bounds[0] + bounds[1]) / 2

            analysis["dimensions"] = dimensions.tolist()
            analysis["center"] = center.tolist()
            analysis["volume"] = float(mesh.volume) if mesh.is_watertight else 0.0
            analysis["surface_area"] = float(mesh.area)
            analysis["face_count"] = len(mesh.faces)
            analysis["vertex_count"] = len(mesh.vertices)

            # Determine optimal viewing distance
            max_dimension = max(dimensions)
            analysis["optimal_distance"] = max_dimension * 2.5

            # Determine if mesh is tall/thin, wide/flat, etc.
            aspect_ratios = dimensions / max_dimension
            analysis["shape_type"] = self._classify_shape(aspect_ratios)

            # Check for symmetries
            analysis["symmetries"] = self._detect_symmetries(mesh)

            # Determine optimal rotation axis
            analysis["rotation_axis"] = self._determine_rotation_axis(mesh, dimensions)

        except Exception as e:
            self.logger.warning(f"Error analyzing mesh for animation: {e}")
            analysis = {
                "dimensions": [10, 10, 10],
                "center": [0, 0, 0],
                "optimal_distance": 25.0,
                "shape_type": "cube",
                "symmetries": [],
                "rotation_axis": [0, 0, 1]
            }

        return analysis

    def _classify_shape(self, aspect_ratios: np.ndarray) -> str:
        """Classify shape based on aspect ratios."""

        sorted_ratios = np.sort(aspect_ratios)

        if sorted_ratios[2] / sorted_ratios[1] > 3.0:
            return "elongated"  # Tall/thin
        elif sorted_ratios[1] / sorted_ratios[0] < 1.5:
            return "flat"  # Wide/flat
        else:
            return "balanced"

    def _detect_symmetries(self, mesh: trimesh.Trimesh) -> List[str]:
        """Detect basic symmetries in the mesh."""

        symmetries = []

        try:
            bounds = mesh.bounds
            center = (bounds[0] + bounds[1]) / 2

            # Check for rotational symmetries (simplified)
            # This would require more sophisticated analysis in practice

            symmetries.append("none_detected")  # Placeholder

        except Exception:
            pass

        return symmetries

    def _determine_rotation_axis(self, mesh: trimesh.Trimesh, dimensions: np.ndarray) -> List[float]:
        """Determine the best axis for rotation animation."""

        # Use the axis with the middle dimension for most interesting rotation
        sorted_dims = np.argsort(dimensions)

        # Prefer Y axis for most models, Z for tall models
        if dimensions[2] > dimensions[1] * 1.5:  # Tall model
            return [0, 0, 1]  # Z axis
        else:
            return [0, 1, 0]  # Y axis

    def _create_optimal_animation_sequence(self, mesh: trimesh.Trimesh,
                                        analysis: Dict[str, Any],
                                        animation_type: AnimationType,
                                        duration: float) -> AnimationSequence:
        """Create an optimal animation sequence based on mesh analysis."""

        if animation_type == AnimationType.ROTATION:
            return self._create_rotation_animation(mesh, duration)
        elif animation_type == AnimationType.ORBIT:
            return self._create_orbit_animation(mesh, analysis, duration)
        elif animation_type == AnimationType.ZOOM:
            return self._create_zoom_animation(mesh, analysis, duration)
        else:
            # Default to rotation
            return self._create_rotation_animation(mesh, duration)

    def _create_rotation_animation(self, mesh: trimesh.Trimesh, duration: float) -> AnimationSequence:
        """Create a smooth rotation animation."""

        bounds = mesh.bounds
        center = (bounds[0] + bounds[1]) / 2
        distance = np.linalg.norm(bounds[1] - bounds[0]) * 2.5

        keyframes = []

        # Create keyframes for full rotation
        num_keyframes = 60  # 2 seconds at 30fps
        for i in range(num_keyframes + 1):
            angle = (i / num_keyframes) * 2 * np.pi
            time_pos = (i / num_keyframes) * duration

            # Position camera in circle around model
            x = center[0] + distance * np.cos(angle)
            z = center[2] + distance * np.sin(angle)
            y = center[1] + distance * 0.5  # Slightly above center

            keyframes.append(CameraKeyframe(
                time=time_pos,
                position=np.array([x, y, z]),
                target=center,
                fov=45.0
            ))

        return AnimationSequence(
            name="Smart Rotation",
            duration=duration,
            keyframes=keyframes,
            animation_type=AnimationType.ROTATION,
            easing="ease_in_out"
        )

    def _create_orbit_animation(self, mesh: trimesh.Trimesh,
                              analysis: Dict[str, Any],
                              duration: float) -> AnimationSequence:
        """Create an orbital camera animation."""

        center = np.array(analysis["center"])
        distance = analysis["optimal_distance"]

        keyframes = []

        # Orbital motion
        num_keyframes = 120  # 4 seconds at 30fps
        for i in range(num_keyframes + 1):
            time_pos = (i / num_keyframes) * duration

            # Complex orbital path
            angle1 = (i / num_keyframes) * 2 * np.pi
            angle2 = (i / num_keyframes) * 4 * np.pi  # Faster vertical motion

            x = center[0] + distance * np.cos(angle1) * np.cos(angle2 * 0.5)
            y = center[1] + distance * 0.7 * np.sin(angle2)
            z = center[2] + distance * np.sin(angle1) * np.cos(angle2 * 0.5)

            keyframes.append(CameraKeyframe(
                time=time_pos,
                position=np.array([x, y, z]),
                target=center,
                fov=50.0
            ))

        return AnimationSequence(
            name="Smart Orbit",
            duration=duration,
            keyframes=keyframes,
            animation_type=AnimationType.ORBIT,
            easing="linear"
        )

    def _create_zoom_animation(self, mesh: trimesh.Trimesh,
                             analysis: Dict[str, Any],
                             duration: float) -> AnimationSequence:
        """Create a zoom in/out animation."""

        center = np.array(analysis["center"])
        max_distance = analysis["optimal_distance"]
        min_distance = max_distance * 0.3

        keyframes = []

        # Zoom out then in
        num_keyframes = 60
        for i in range(num_keyframes + 1):
            t = i / num_keyframes
            time_pos = t * duration

            # Smooth zoom curve (ease in-out)
            if t < 0.5:
                zoom_t = 2 * t * t  # Ease in
            else:
                zoom_t = 1 - 2 * (1 - t) * (1 - t)  # Ease out

            distance = max_distance - (max_distance - min_distance) * zoom_t

            # Position camera along viewing axis
            position = center + np.array([0, distance, distance * 0.5])

            keyframes.append(CameraKeyframe(
                time=time_pos,
                position=position,
                target=center,
                fov=45.0 + zoom_t * 20.0  # Zoom in FOV
            ))

        return AnimationSequence(
            name="Smart Zoom",
            duration=duration,
            keyframes=keyframes,
            animation_type=AnimationType.ZOOM,
            easing="ease_in_out"
        )

    def _sequence_to_animation_data(self, sequence: AnimationSequence) -> Dict[str, Any]:
        """Convert animation sequence to JSON-serializable data."""

        keyframes_data = []
        for kf in sequence.keyframes:
            keyframes_data.append({
                "time": kf.time,
                "position": kf.position.tolist(),
                "target": kf.target.tolist(),
                "up": kf.up.tolist(),
                "fov": kf.fov
            })

        return {
            "name": sequence.name,
            "duration": sequence.duration,
            "type": sequence.animation_type.value,
            "easing": sequence.easing,
            "keyframes": keyframes_data
        }

    def export_animation_to_json(self, result: AnimationResult, file_path: str) -> bool:
        """Export animation data to JSON file."""

        try:
            data = {
                "success": result.success,
                "animation": result.animation_data,
                "metadata": result.metadata,
                "duration": result.duration,
                "errors": result.errors
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            self.logger.error(f"Error exporting animation to JSON: {e}")
            return False


# Global instance
ai_animation_preview = AIAnimationPreview()


def generate_smart_animation(mesh: trimesh.Trimesh,
                           animation_type: AnimationType = AnimationType.ROTATION,
                           duration: float = 10.0) -> AnimationResult:
    """Convenience function for smart animation generation."""
    return ai_animation_preview.generate_smart_preview(mesh, animation_type, duration)


def create_exploded_view_animation(mesh: trimesh.Trimesh, duration: float = 8.0) -> AnimationResult:
    """Convenience function for exploded view animation."""
    return ai_animation_preview.generate_exploded_view(mesh, duration)


def create_cross_section_animation(mesh: trimesh.Trimesh, duration: float = 6.0) -> AnimationResult:
    """Convenience function for cross-section animation."""
    return ai_animation_preview.create_cross_section_animation(mesh, duration)
