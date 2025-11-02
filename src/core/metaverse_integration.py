"""Metaverse integration for immersive VR/AR design and manufacturing processes."""

import asyncio
import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import threading
import uuid
import numpy as np


class MetaverseMode(Enum):
    """Metaverse interaction modes."""
    DESIGN_STUDIO = "design_studio"      # Virtual design workspace
    MANUFACTURING_FLOOR = "manufacturing_floor"  # Virtual factory floor
    COLLABORATION_SPACE = "collaboration_space"  # Multi-user collaboration
    SIMULATION_LAB = "simulation_lab"    # Physics simulation environment
    TRAINING_CENTER = "training_center"  # Educational and training space


class AvatarType(Enum):
    """Avatar representation types."""
    HUMAN_REALISTIC = "human_realistic"
    ROBOTIC = "robotic"
    ABSTRACT = "abstract"
    CUSTOM = "custom"


@dataclass
class MetaverseAvatar:
    """User avatar in the metaverse."""
    avatar_id: str
    user_id: str
    avatar_type: AvatarType
    position: Tuple[float, float, float] = (0, 0, 0)
    rotation: Tuple[float, float, float] = (0, 0, 0)
    scale: float = 1.0
    appearance: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    current_space: Optional[str] = None


@dataclass
class MetaverseSpace:
    """Virtual space in the metaverse."""
    space_id: str
    name: str
    mode: MetaverseMode
    dimensions: Tuple[float, float, float] = (100, 100, 50)
    physics_enabled: bool = True
    gravity: float = 9.81
    lighting: Dict[str, Any] = field(default_factory=dict)
    objects: List[Dict[str, Any]] = field(default_factory=list)
    participants: Set[str] = field(default_factory=set)


class MetaverseRenderer:
    """Advanced 3D renderer for metaverse environments."""

    def __init__(self):
        """Initialize metaverse renderer."""
        self.logger = logging.getLogger(__name__)
        self.scenes: Dict[str, Dict[str, Any]] = {}
        self.rendering_engines = {
            'webgl': 'Three.js WebGL',
            'webgpu': 'WebGPU',
            'ray_tracing': 'Path Tracing',
            'voxel': 'Voxel Rendering'
        }

    def create_metaverse_scene(self, space_id: str, mode: MetaverseMode) -> Dict[str, Any]:
        """Create a metaverse scene.

        Args:
            space_id: Space identifier
            mode: Metaverse mode

        Returns:
            Scene configuration
        """
        scene = {
            'scene_id': space_id,
            'mode': mode.value,
            'rendering_engine': 'webgl',
            'environment': self._create_environment(mode),
            'lighting': self._create_lighting_setup(mode),
            'camera': {
                'type': 'first_person' if mode == MetaverseMode.DESIGN_STUDIO else 'third_person',
                'position': [0, 1.7, 5],  # Average eye height
                'target': [0, 0, 0]
            },
            'physics': {
                'gravity': 9.81,
                'air_resistance': 0.1,
                'collision_detection': True
            },
            'audio': {
                'spatial_audio': True,
                'reverb': True,
                'background_music': self._get_background_audio(mode)
            }
        }

        self.scenes[space_id] = scene
        self.logger.info(f"Created metaverse scene for mode: {mode.value}")

        return scene

    def _create_environment(self, mode: MetaverseMode) -> Dict[str, Any]:
        """Create environment based on mode."""
        environments = {
            MetaverseMode.DESIGN_STUDIO: {
                'skybox': 'design_studio_sky',
                'floor_texture': 'grid_pattern',
                'walls': 'modern_office',
                'ambient_sounds': ['keyboard_typing', 'design_software']
            },
            MetaverseMode.MANUFACTURING_FLOOR: {
                'skybox': 'factory_warehouse',
                'floor_texture': 'concrete_floor',
                'walls': 'industrial_walls',
                'ambient_sounds': ['machinery_hum', 'conveyor_belts']
            },
            MetaverseMode.COLLABORATION_SPACE: {
                'skybox': 'meeting_room',
                'floor_texture': 'carpet_pattern',
                'walls': 'glass_walls',
                'ambient_sounds': ['office_ambience', 'light_conversation']
            },
            MetaverseMode.SIMULATION_LAB: {
                'skybox': 'science_lab',
                'floor_texture': 'lab_floor',
                'walls': 'research_facility',
                'ambient_sounds': ['computer_fans', 'equipment_beeps']
            },
            MetaverseMode.TRAINING_CENTER: {
                'skybox': 'classroom',
                'floor_texture': 'classroom_floor',
                'walls': 'educational',
                'ambient_sounds': ['projector_hum', 'student_activity']
            }
        }

        return environments.get(mode, environments[MetaverseMode.DESIGN_STUDIO])

    def _create_lighting_setup(self, mode: MetaverseMode) -> Dict[str, Any]:
        """Create lighting setup for the mode."""
        base_lighting = {
            'ambient_light': {'color': '#ffffff', 'intensity': 0.4},
            'directional_light': {
                'color': '#ffffff',
                'intensity': 0.8,
                'position': [10, 10, 5]
            }
        }

        # Mode-specific lighting
        if mode == MetaverseMode.MANUFACTURING_FLOOR:
            base_lighting['spot_lights'] = [
                {'position': [0, 10, 0], 'target': [0, 0, 0], 'intensity': 1.0}
            ]

        return base_lighting

    def _get_background_audio(self, mode: MetaverseMode) -> str:
        """Get background audio for the mode."""
        audio_files = {
            MetaverseMode.DESIGN_STUDIO: 'design_studio_ambience.mp3',
            MetaverseMode.MANUFACTURING_FLOOR: 'factory_ambience.mp3',
            MetaverseMode.COLLABORATION_SPACE: 'office_ambience.mp3',
            MetaverseMode.SIMULATION_LAB: 'lab_ambience.mp3',
            MetaverseMode.TRAINING_CENTER: 'classroom_ambience.mp3'
        }

        return audio_files.get(mode, 'default_ambience.mp3')

    def add_interactive_object(self, space_id: str, obj_data: Dict[str, Any]) -> str:
        """Add an interactive object to the metaverse space.

        Args:
            space_id: Space identifier
            obj_data: Object configuration

        Returns:
            Object ID
        """
        object_id = str(uuid.uuid4())

        interactive_object = {
            'id': object_id,
            'name': obj_data.get('name', 'Interactive Object'),
            'type': obj_data.get('type', 'generic'),
            'position': obj_data.get('position', [0, 0, 0]),
            'rotation': obj_data.get('rotation', [0, 0, 0]),
            'scale': obj_data.get('scale', [1, 1, 1]),
            'geometry': obj_data.get('geometry', {}),
            'material': obj_data.get('material', {}),
            'interactions': obj_data.get('interactions', []),
            'physics': obj_data.get('physics', {}),
            'audio': obj_data.get('audio', {})
        }

        if space_id in self.scenes:
            if 'objects' not in self.scenes[space_id]:
                self.scenes[space_id]['objects'] = []
            self.scenes[space_id]['objects'].append(interactive_object)

        return object_id

    def update_object_position(self, space_id: str, object_id: str, position: Tuple[float, float, float]):
        """Update object position in the metaverse.

        Args:
            space_id: Space identifier
            object_id: Object identifier
            position: New position
        """
        if space_id in self.scenes:
            for obj in self.scenes[space_id].get('objects', []):
                if obj['id'] == object_id:
                    obj['position'] = list(position)
                    break


class MetaversePhysicsEngine:
    """Physics engine for metaverse interactions."""

    def __init__(self):
        """Initialize physics engine."""
        self.logger = logging.getLogger(__name__)
        self.physical_objects: Dict[str, Dict[str, Any]] = {}
        self.collision_pairs: Set[Tuple[str, str]] = set()

    def register_physical_object(self, object_id: str, physics_props: Dict[str, Any]):
        """Register an object for physics simulation.

        Args:
            object_id: Object identifier
            physics_props: Physics properties
        """
        self.physical_objects[object_id] = {
            'mass': physics_props.get('mass', 1.0),
            'friction': physics_props.get('friction', 0.3),
            'restitution': physics_props.get('restitution', 0.8),
            'velocity': physics_props.get('velocity', [0, 0, 0]),
            'angular_velocity': physics_props.get('angular_velocity', [0, 0, 0]),
            'constraints': physics_props.get('constraints', [])
        }

        self.logger.debug(f"Registered physical object: {object_id}")

    def simulate_physics_step(self, delta_time: float):
        """Simulate one physics step.

        Args:
            delta_time: Time step in seconds
        """
        # Apply forces
        self._apply_gravity()
        self._apply_forces()

        # Update positions
        self._update_kinematics(delta_time)

        # Handle collisions
        self._detect_collisions()
        self._resolve_collisions()

    def _apply_gravity(self):
        """Apply gravity to all objects."""
        gravity = [0, -9.81, 0]  # m/s²

        for obj_id, obj in self.physical_objects.items():
            if 'fixed' not in obj.get('constraints', []):
                # F = mg
                force = [0, obj['mass'] * gravity[1], 0]
                obj['forces'] = obj.get('forces', [0, 0, 0])
                obj['forces'][1] += force[1]

    def _apply_forces(self):
        """Apply external forces."""
        for obj_id, obj in self.physical_objects.items():
            if 'forces' in obj:
                # F = ma -> a = F/m
                acceleration = [f / obj['mass'] for f in obj['forces']]

                # Update velocity: v = v0 + at
                obj['velocity'] = [
                    obj['velocity'][i] + acceleration[i] * 0.016  # Assume 60fps
                    for i in range(3)
                ]

    def _update_kinematics(self, delta_time: float):
        """Update object positions based on velocity."""
        for obj_id, obj in self.physical_objects.items():
            if 'fixed' not in obj.get('constraints', []):
                # Update position: x = x0 + vt
                obj['position'] = [
                    obj.get('position', [0, 0, 0])[i] + obj['velocity'][i] * delta_time
                    for i in range(3)
                ]

    def _detect_collisions(self):
        """Detect collisions between objects."""
        self.collision_pairs.clear()
        object_ids = list(self.physical_objects.keys())

        for i, obj1_id in enumerate(object_ids):
            for obj2_id in object_ids[i+1:]:
                obj1 = self.physical_objects[obj1_id]
                obj2 = self.physical_objects[obj2_id]

                pos1 = obj1.get('position', [0, 0, 0])
                pos2 = obj2.get('position', [0, 0, 0])

                # Simple distance-based collision detection
                distance = np.linalg.norm(np.array(pos2) - np.array(pos1))

                if distance < 2.0:  # Collision threshold
                    self.collision_pairs.add((obj1_id, obj2_id))

    def _resolve_collisions(self):
        """Resolve collisions between objects."""
        for obj1_id, obj2_id in self.collision_pairs:
            obj1 = self.physical_objects[obj1_id]
            obj2 = self.physical_objects[obj2_id]

            # Simple elastic collision response
            pos1 = obj1.get('position', [0, 0, 0])
            pos2 = obj2.get('position', [0, 0, 0])

            # Calculate collision normal
            collision_vector = np.array(pos2) - np.array(pos1)
            distance = np.linalg.norm(collision_vector)

            if distance > 0:
                normal = collision_vector / distance

                # Separate objects
                separation_distance = 1.0  # Minimum separation
                if distance < separation_distance:
                    # Move objects apart
                    midpoint = (np.array(pos1) + np.array(pos2)) / 2
                    obj1['position'] = (midpoint - normal * separation_distance / 2).tolist()
                    obj2['position'] = (midpoint + normal * separation_distance / 2).tolist()

                # Exchange velocities (simplified)
                temp_vel = obj1['velocity'].copy()
                obj1['velocity'] = obj2['velocity'].copy()
                obj2['velocity'] = temp_vel


class MetaverseInteractionManager:
    """Manages interactions in the metaverse."""

    def __init__(self):
        """Initialize interaction manager."""
        self.logger = logging.getLogger(__name__)
        self.gesture_recognizer = GestureRecognizer()
        self.voice_processor = VoiceProcessor()
        self.haptic_feedback = HapticFeedbackSystem()

    def process_user_input(self, user_id: str, input_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process user input in the metaverse.

        Args:
            user_id: User identifier
            input_type: Type of input (gesture, voice, hmi)
            input_data: Input data

        Returns:
            Processing result
        """
        if input_type == 'gesture':
            return self.gesture_recognizer.process_gesture(input_data)
        elif input_type == 'voice':
            return self.voice_processor.process_voice_command(input_data)
        elif input_type == 'hmi':
            return self._process_hmi_input(input_data)
        else:
            return {'error': f'Unsupported input type: {input_type}'}

    def _process_hmi_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process human-machine interface input."""
        # Process brainwave, eye tracking, etc.
        brainwave_data = input_data.get('brainwave', {})
        eye_tracking = input_data.get('eye_tracking', {})

        # Interpret intent from biological signals
        intent = self._interpret_biological_signals(brainwave_data, eye_tracking)

        return {
            'interpreted_intent': intent,
            'confidence': 0.8,
            'suggested_action': self._get_suggested_action(intent)
        }

    def _interpret_biological_signals(self, brainwave: Dict[str, Any], eye_tracking: Dict[str, Any]) -> str:
        """Interpret biological signals for intent recognition."""
        # Simplified brainwave interpretation
        alpha_waves = brainwave.get('alpha', 0)
        beta_waves = brainwave.get('beta', 0)

        if beta_waves > alpha_waves * 1.5:
            return 'focused_concentration'
        elif alpha_waves > beta_waves:
            return 'relaxed_attention'
        else:
            return 'neutral_state'

    def _get_suggested_action(self, intent: str) -> str:
        """Get suggested action based on intent."""
        actions = {
            'focused_concentration': 'precision_design_mode',
            'relaxed_attention': 'creative_design_mode',
            'neutral_state': 'standard_interaction_mode'
        }

        return actions.get(intent, 'standard_interaction_mode')


class GestureRecognizer:
    """Recognizes gestures for metaverse interaction."""

    def __init__(self):
        """Initialize gesture recognizer."""
        self.logger = logging.getLogger(__name__)
        self.gesture_patterns = self._load_gesture_patterns()

    def _load_gesture_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load predefined gesture patterns."""
        return {
            'pinch_zoom': {
                'finger_positions': 'thumb_index_close',
                'motion_pattern': 'radial_contraction',
                'action': 'zoom_camera'
            },
            'grab_rotate': {
                'finger_positions': 'fist_like',
                'motion_pattern': 'circular_motion',
                'action': 'rotate_object'
            },
            'point_select': {
                'finger_positions': 'index_extended',
                'motion_pattern': 'pointing_gesture',
                'action': 'select_object'
            },
            'swipe_navigate': {
                'finger_positions': 'open_hand',
                'motion_pattern': 'lateral_swipe',
                'action': 'navigate_space'
            }
        }

    def process_gesture(self, gesture_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process gesture input.

        Args:
            gesture_data: Raw gesture data

        Returns:
            Recognized gesture and action
        """
        # Extract gesture features
        hand_positions = gesture_data.get('hand_positions', [])
        finger_angles = gesture_data.get('finger_angles', [])
        motion_vector = gesture_data.get('motion_vector', [0, 0, 0])

        # Match against patterns
        best_match = None
        best_confidence = 0.0

        for gesture_name, pattern in self.gesture_patterns.items():
            confidence = self._calculate_gesture_similarity(
                gesture_data, pattern
            )

            if confidence > best_confidence and confidence > 0.7:
                best_confidence = confidence
                best_match = gesture_name

        if best_match:
            return {
                'gesture_recognized': best_match,
                'confidence': best_confidence,
                'action': self.gesture_patterns[best_match]['action'],
                'parameters': self._extract_gesture_parameters(gesture_data, best_match)
            }
        else:
            return {'gesture_recognized': 'unknown', 'confidence': 0.0}

    def _calculate_gesture_similarity(self, gesture_data: Dict[str, Any],
                                    pattern: Dict[str, Any]) -> float:
        """Calculate similarity between gesture and pattern."""
        # Simplified similarity calculation
        similarity_score = 0.0

        # Compare finger positions
        if 'finger_positions' in gesture_data and 'finger_positions' in pattern:
            similarity_score += 0.4  # Placeholder

        # Compare motion pattern
        if 'motion_vector' in gesture_data:
            similarity_score += 0.3  # Placeholder

        return similarity_score

    def _extract_gesture_parameters(self, gesture_data: Dict[str, Any], gesture_name: str) -> Dict[str, Any]:
        """Extract parameters from gesture."""
        params = {}

        if gesture_name == 'pinch_zoom':
            params['zoom_factor'] = gesture_data.get('pinch_distance', 1.0)

        elif gesture_name == 'grab_rotate':
            params['rotation_axis'] = gesture_data.get('rotation_axis', [0, 0, 1])
            params['rotation_angle'] = gesture_data.get('rotation_angle', 0)

        return params


class VoiceProcessor:
    """Processes voice commands for metaverse interaction."""

    def __init__(self):
        """Initialize voice processor."""
        self.logger = logging.getLogger(__name__)
        self.voice_commands = self._load_voice_commands()

    def _load_voice_commands(self) -> Dict[str, Dict[str, Any]]:
        """Load voice command patterns."""
        return {
            'create_cube': {
                'patterns': ['create cube', 'make cube', 'add cube'],
                'action': 'create_primitive',
                'parameters': {'shape': 'cube'}
            },
            'zoom_in': {
                'patterns': ['zoom in', 'get closer', 'magnify'],
                'action': 'camera_zoom',
                'parameters': {'direction': 'in'}
            },
            'rotate_object': {
                'patterns': ['rotate object', 'turn object', 'spin it'],
                'action': 'object_rotation',
                'parameters': {'angle': 45, 'axis': 'y'}
            },
            'run_simulation': {
                'patterns': ['run simulation', 'start simulation', 'simulate'],
                'action': 'execute_simulation',
                'parameters': {}
            }
        }

    def process_voice_command(self, audio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process voice command.

        Args:
            audio_data: Audio data and transcription

        Returns:
            Command interpretation
        """
        transcription = audio_data.get('transcription', '').lower()
        confidence = audio_data.get('confidence', 0.0)

        if confidence < 0.7:
            return {
                'command_recognized': False,
                'reason': 'Low confidence transcription',
                'confidence': confidence
            }

        # Match against command patterns
        best_match = None
        best_score = 0.0

        for command_name, command_data in self.voice_commands.items():
            for pattern in command_data['patterns']:
                # Simple pattern matching
                if pattern in transcription:
                    score = len(pattern.split()) / len(transcription.split())
                    if score > best_score:
                        best_score = score
                        best_match = command_name

        if best_match:
            command_info = self.voice_commands[best_match]
            return {
                'command_recognized': True,
                'command': best_match,
                'action': command_info['action'],
                'parameters': command_info['parameters'],
                'confidence': min(confidence, best_score)
            }
        else:
            return {
                'command_recognized': False,
                'reason': 'No matching command found',
                'confidence': 0.0
            }


class HapticFeedbackSystem:
    """Provides haptic feedback for metaverse interactions."""

    def __init__(self):
        """Initialize haptic feedback system."""
        self.logger = logging.getLogger(__name__)
        self.feedback_patterns = self._load_feedback_patterns()

    def _load_feedback_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load haptic feedback patterns."""
        return {
            'object_collision': {
                'vibration_pattern': [100, 50, 100],  # ms on/off/on
                'frequency': 250,  # Hz
                'duration': 200    # ms
            },
            'successful_action': {
                'vibration_pattern': [50],
                'frequency': 150,
                'duration': 100
            },
            'warning': {
                'vibration_pattern': [200, 100, 200, 100, 200],
                'frequency': 300,
                'duration': 800
            }
        }

    def trigger_feedback(self, feedback_type: str, intensity: float = 1.0):
        """Trigger haptic feedback.

        Args:
            feedback_type: Type of feedback
            intensity: Feedback intensity (0-1)
        """
        if feedback_type not in self.feedback_patterns:
            return

        pattern = self.feedback_patterns[feedback_type]

        # Adjust pattern based on intensity
        adjusted_pattern = [int(v * intensity) for v in pattern['vibration_pattern']]

        # In real implementation, this would control haptic devices
        self.logger.info(f"Triggered {feedback_type} haptic feedback with intensity {intensity}")


class MetaverseAvatarManager:
    """Manages user avatars in the metaverse."""

    def __init__(self):
        """Initialize avatar manager."""
        self.logger = logging.getLogger(__name__)
        self.avatars: Dict[str, MetaverseAvatar] = {}
        self.avatar_animations: Dict[str, List[Dict[str, Any]]] = {}

    def create_avatar(self, user_id: str, avatar_type: AvatarType = AvatarType.HUMAN_REALISTIC) -> str:
        """Create an avatar for a user.

        Args:
            user_id: User identifier
            avatar_type: Type of avatar

        Returns:
            Avatar ID
        """
        avatar_id = str(uuid.uuid4())

        avatar = MetaverseAvatar(
            avatar_id=avatar_id,
            user_id=user_id,
            avatar_type=avatar_type,
            appearance=self._generate_default_appearance(avatar_type),
            capabilities=self._get_avatar_capabilities(avatar_type)
        )

        self.avatars[avatar_id] = avatar

        # Initialize animations
        self.avatar_animations[avatar_id] = []

        self.logger.info(f"Created avatar {avatar_id} for user {user_id}")
        return avatar_id

    def _generate_default_appearance(self, avatar_type: AvatarType) -> Dict[str, Any]:
        """Generate default appearance for avatar type."""
        appearances = {
            AvatarType.HUMAN_REALISTIC: {
                'height': 1.75,
                'body_type': 'average',
                'skin_tone': 'neutral',
                'hair_style': 'default',
                'clothing': 'business_casual'
            },
            AvatarType.ROBOTIC: {
                'chassis_type': 'humanoid',
                'color_scheme': 'metallic_blue',
                'accessories': ['tool_arm', 'sensor_array']
            },
            AvatarType.ABSTRACT: {
                'shape': 'geometric',
                'color': 'dynamic',
                'particles': True
            }
        }

        return appearances.get(avatar_type, appearances[AvatarType.HUMAN_REALISTIC])

    def _get_avatar_capabilities(self, avatar_type: AvatarType) -> List[str]:
        """Get capabilities for avatar type."""
        capabilities_map = {
            AvatarType.HUMAN_REALISTIC: ['walk', 'run', 'gesture', 'voice_chat'],
            AvatarType.ROBOTIC: ['precise_movement', 'tool_manipulation', 'sensor_scan'],
            AvatarType.ABSTRACT: ['teleport', 'shape_shift', 'energy_manipulation']
        }

        return capabilities_map.get(avatar_type, capabilities_map[AvatarType.HUMAN_REALISTIC])

    def update_avatar_position(self, avatar_id: str, position: Tuple[float, float, float],
                             rotation: Tuple[float, float, float]):
        """Update avatar position and rotation.

        Args:
            avatar_id: Avatar identifier
            position: New position
            rotation: New rotation
        """
        if avatar_id in self.avatars:
            self.avatars[avatar_id].position = position
            self.avatars[avatar_id].rotation = rotation

    def add_avatar_animation(self, avatar_id: str, animation: Dict[str, Any]):
        """Add animation to avatar.

        Args:
            avatar_id: Avatar identifier
            animation: Animation data
        """
        if avatar_id in self.avatar_animations:
            self.avatar_animations[avatar_id].append({
                **animation,
                'start_time': time.time()
            })


class MetaverseIntegration:
    """Main metaverse integration system."""

    def __init__(self):
        """Initialize metaverse integration."""
        self.logger = logging.getLogger(__name__)

        # Core components
        self.renderer = MetaverseRenderer()
        self.physics_engine = MetaversePhysicsEngine()
        self.interaction_manager = MetaverseInteractionManager()
        self.avatar_manager = MetaverseAvatarManager()

        # Active spaces
        self.spaces: Dict[str, MetaverseSpace] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        # Physics simulation
        self.physics_thread: Optional[threading.Thread] = None
        self._stop_physics = threading.Event()

    def create_metaverse_space(self, name: str, mode: MetaverseMode) -> str:
        """Create a new metaverse space.

        Args:
            name: Space name
            mode: Metaverse mode

        Returns:
            Space ID
        """
        space_id = str(uuid.uuid4())

        space = MetaverseSpace(
            space_id=space_id,
            name=name,
            mode=mode,
            physics_enabled=True
        )

        self.spaces[space_id] = space

        # Create scene for the space
        scene_data = self.renderer.create_metaverse_scene(space_id, mode)

        self.logger.info(f"Created metaverse space: {name} ({mode.value})")
        return space_id

    def join_metaverse_space(self, user_id: str, space_id: str,
                           avatar_type: AvatarType = AvatarType.HUMAN_REALISTIC) -> str:
        """Join a metaverse space.

        Args:
            user_id: User identifier
            space_id: Space to join
            avatar_type: Avatar type

        Returns:
            Session ID
        """
        if space_id not in self.spaces:
            return ""

        session_id = str(uuid.uuid4())

        # Create avatar
        avatar_id = self.avatar_manager.create_avatar(user_id, avatar_type)

        # Update space participants
        self.spaces[space_id].participants.add(avatar_id)

        # Create session
        self.active_sessions[session_id] = {
            'user_id': user_id,
            'space_id': space_id,
            'avatar_id': avatar_id,
            'joined_at': time.time(),
            'input_devices': {
                'hmd': True,
                'controllers': 2,
                'haptic_suit': False,
                'brain_interface': False
            }
        }

        self.logger.info(f"User {user_id} joined metaverse space {space_id}")
        return session_id

    def process_metaverse_input(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input from metaverse session.

        Args:
            session_id: Session identifier
            input_data: Input data

        Returns:
            Processing result
        """
        if session_id not in self.active_sessions:
            return {'error': 'Session not found'}

        session = self.active_sessions[session_id]
        input_type = input_data.get('input_type', 'unknown')

        # Process input through interaction manager
        result = self.interaction_manager.process_user_input(
            session['user_id'], input_type, input_data
        )

        # Update avatar if position data is provided
        if 'avatar_position' in input_data:
            self.avatar_manager.update_avatar_position(
                session['avatar_id'],
                tuple(input_data['avatar_position']),
                tuple(input_data.get('avatar_rotation', [0, 0, 0]))
            )

        return result

    def start_physics_simulation(self):
        """Start physics simulation thread."""
        if self.physics_thread:
            return

        self.physics_thread = threading.Thread(
            target=self._physics_simulation_loop,
            daemon=True,
            name="MetaversePhysics"
        )
        self.physics_thread.start()
        self.logger.info("Started metaverse physics simulation")

    def stop_physics_simulation(self):
        """Stop physics simulation thread."""
        if self.physics_thread:
            self._stop_physics.set()
            self.physics_thread.join(timeout=5.0)
            self.physics_thread = None
            self.logger.info("Stopped metaverse physics simulation")

    def _physics_simulation_loop(self):
        """Main physics simulation loop."""
        while not self._stop_physics.is_set():
            try:
                # Run physics step
                self.physics_engine.simulate_physics_step(0.016)  # 60fps

                # Update object positions in renderer
                self._update_rendered_objects()

                time.sleep(0.016)

            except Exception as e:
                self.logger.error(f"Error in physics simulation: {e}")
                time.sleep(1.0)

    def _update_rendered_objects(self):
        """Update rendered object positions based on physics."""
        for space_id, space in self.spaces.items():
            for obj in space.objects:
                obj_id = obj['id']
                if obj_id in self.physics_engine.physical_objects:
                    physics_obj = self.physics_engine.physical_objects[obj_id]
                    position = physics_obj.get('position', obj['position'])
                    self.renderer.update_object_position(space_id, obj_id, tuple(position))

    def get_space_state(self, space_id: str) -> Dict[str, Any]:
        """Get current state of a metaverse space.

        Args:
            space_id: Space identifier

        Returns:
            Space state
        """
        if space_id not in self.spaces:
            return {'error': 'Space not found'}

        space = self.spaces[space_id]
        scene_data = self.renderer.get_scene_data(space_id)

        return {
            'space_info': {
                'space_id': space.space_id,
                'name': space.name,
                'mode': space.mode.value,
                'participant_count': len(space.participants)
            },
            'scene_data': scene_data,
            'physics_objects': len(self.physics_engine.physical_objects),
            'active_avatars': [
                self._get_avatar_info(avatar_id)
                for avatar_id in space.participants
                if avatar_id in self.avatar_manager.avatars
            ]
        }

    def _get_avatar_info(self, avatar_id: str) -> Dict[str, Any]:
        """Get avatar information."""
        avatar = self.avatar_manager.avatars.get(avatar_id)
        if not avatar:
            return {}

        return {
            'avatar_id': avatar.avatar_id,
            'user_id': avatar.user_id,
            'avatar_type': avatar.avatar_type.value,
            'position': avatar.position,
            'capabilities': avatar.capabilities
        }

    def add_collaborative_object(self, space_id: str, object_data: Dict[str, Any]) -> str:
        """Add a collaborative object to the space.

        Args:
            space_id: Space identifier
            object_data: Object configuration

        Returns:
            Object ID
        """
        if space_id not in self.spaces:
            return ""

        # Add to space objects
        object_id = self.renderer.add_interactive_object(space_id, object_data)

        # Register for physics if needed
        if object_data.get('physics', {}).get('enabled', False):
            self.physics_engine.register_physical_object(
                object_id,
                object_data['physics']
            )

        return object_id

    def get_metaverse_capabilities(self) -> Dict[str, Any]:
        """Get metaverse system capabilities.

        Returns:
            System capabilities
        """
        return {
            'supported_modes': [mode.value for mode in MetaverseMode],
            'avatar_types': [avatar_type.value for avatar_type in AvatarType],
            'physics_engine': 'advanced',
            'rendering_engines': list(self.renderer.rendering_engines.keys()),
            'interaction_modes': ['gesture', 'voice', 'hmi', 'traditional'],
            'max_participants_per_space': 50,
            'supported_hardware': [
                'VR_headsets',
                'AR_glasses',
                'haptic_suits',
                'brain_interfaces',
                'gesture_gloves'
            ]
        }


# Global metaverse integration instance
metaverse_integration = MetaverseIntegration()


# Convenience functions
def create_metaverse_space(name: str, mode: str) -> str:
    """Create a metaverse space."""
    mode_enum = MetaverseMode(mode) if mode in [m.value for m in MetaverseMode] else MetaverseMode.DESIGN_STUDIO
    return metaverse_integration.create_metaverse_space(name, mode_enum)


def join_metaverse_space(user_id: str, space_id: str, avatar_type: str = "human_realistic") -> str:
    """Join a metaverse space."""
    avatar_enum = AvatarType(avatar_type) if avatar_type in [a.value for a in AvatarType] else AvatarType.HUMAN_REALISTIC
    return metaverse_integration.join_metaverse_space(user_id, space_id, avatar_enum)


def process_metaverse_input(session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process metaverse input."""
    return metaverse_integration.process_metaverse_input(session_id, input_data)


def add_metaverse_object(space_id: str, object_data: Dict[str, Any]) -> str:
    """Add object to metaverse space."""
    return metaverse_integration.add_collaborative_object(space_id, object_data)


def get_metaverse_capabilities() -> Dict[str, Any]:
    """Get metaverse system capabilities."""
    return metaverse_integration.get_metaverse_capabilities()
