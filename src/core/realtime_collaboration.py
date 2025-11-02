"""Real-time collaboration system with WebSocket support for 3D Print CAD Assistant."""

import asyncio
import json
import time
import uuid
import logging
from typing import Dict, List, Any, Optional, Set, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
from datetime import datetime


class CollaborationEvent(Enum):
    """Types of collaboration events."""
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    MODEL_UPDATE = "model_update"
    SELECTION_CHANGE = "selection_change"
    VIEWPORT_CHANGE = "viewport_change"
    CHAT_MESSAGE = "chat_message"
    DESIGN_CHANGE = "design_change"
    PARAMETER_UPDATE = "parameter_update"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"


@dataclass
class Collaborator:
    """Information about a collaborator."""
    user_id: str
    username: str
    session_id: str
    role: str = "viewer"  # viewer, editor, admin
    color: str = "#3498db"  # Display color for the user
    cursor_position: Dict[str, float] = field(default_factory=dict)
    viewport_state: Dict[str, Any] = field(default_factory=dict)
    last_activity: float = field(default_factory=time.time)
    permissions: Set[str] = field(default_factory=set)


@dataclass
class CollaborationMessage:
    """Message for collaboration events."""
    event_type: CollaborationEvent
    user_id: str
    session_id: str
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class CollaborationRoom:
    """Manages a collaboration session for a 3D model."""

    def __init__(self, room_id: str, model_id: str, created_by: str):
        """Initialize collaboration room.

        Args:
            room_id: Unique room identifier
            model_id: ID of the 3D model being collaborated on
            created_by: User ID of the room creator
        """
        self.logger = logging.getLogger(__name__)
        self.room_id = room_id
        self.model_id = model_id
        self.created_by = created_by
        self.created_at = time.time()

        # Collaborator management
        self.collaborators: Dict[str, Collaborator] = {}
        self.max_collaborators = 50

        # Message history
        self.message_history: List[CollaborationMessage] = []
        self.max_messages = 1000

        # Model state
        self.model_state = {}
        self.state_version = 0

        # Permissions and settings
        self.settings = {
            'allow_chat': True,
            'allow_model_editing': True,
            'require_approval_for_changes': False,
            'auto_save_interval': 30  # seconds
        }

        # Locks for thread safety
        self._lock = threading.RLock()

    def add_collaborator(self, collaborator: Collaborator) -> bool:
        """Add a collaborator to the room.

        Args:
            collaborator: Collaborator to add

        Returns:
            True if added successfully
        """
        with self._lock:
            if len(self.collaborators) >= self.max_collaborators:
                return False

            if collaborator.session_id in self.collaborators:
                return False

            self.collaborators[collaborator.session_id] = collaborator

            # Create join message
            join_message = CollaborationMessage(
                event_type=CollaborationEvent.USER_JOIN,
                user_id=collaborator.user_id,
                session_id=collaborator.session_id,
                timestamp=time.time(),
                data={
                    'username': collaborator.username,
                    'role': collaborator.role,
                    'color': collaborator.color
                }
            )

            self._add_message(join_message)
            self.logger.info(f"Collaborator {collaborator.username} joined room {self.room_id}")

            return True

    def remove_collaborator(self, session_id: str) -> bool:
        """Remove a collaborator from the room.

        Args:
            session_id: Session ID of collaborator to remove

        Returns:
            True if removed successfully
        """
        with self._lock:
            if session_id not in self.collaborators:
                return False

            collaborator = self.collaborators[session_id]

            # Create leave message
            leave_message = CollaborationMessage(
                event_type=CollaborationEvent.USER_LEAVE,
                user_id=collaborator.user_id,
                session_id=session_id,
                timestamp=time.time(),
                data={'username': collaborator.username}
            )

            self._add_message(leave_message)
            del self.collaborators[session_id]

            self.logger.info(f"Collaborator {collaborator.username} left room {self.room_id}")
            return True

    def update_collaborator_activity(self, session_id: str, activity_data: Dict[str, Any]):
        """Update collaborator activity.

        Args:
            session_id: Session ID of collaborator
            activity_data: Activity data to update
        """
        with self._lock:
            if session_id not in self.collaborators:
                return

            collaborator = self.collaborators[session_id]
            collaborator.last_activity = time.time()

            # Update specific activity data
            if 'cursor_position' in activity_data:
                collaborator.cursor_position = activity_data['cursor_position']

            if 'viewport_state' in activity_data:
                collaborator.viewport_state = activity_data['viewport_state']

    def broadcast_message(self, message: CollaborationMessage, exclude_session: Optional[str] = None):
        """Broadcast a message to all collaborators.

        Args:
            message: Message to broadcast
            exclude_session: Session ID to exclude from broadcast
        """
        with self._lock:
            # Add to message history
            self._add_message(message)

            # Here you would send the message to all connected clients
            # For now, we'll just log it
            if message.event_type != CollaborationEvent.USER_JOIN and message.event_type != CollaborationEvent.USER_LEAVE:
                self.logger.debug(f"Broadcasting {message.event_type.value} in room {self.room_id}")

    def handle_model_update(self, session_id: str, update_data: Dict[str, Any]):
        """Handle model update from a collaborator.

        Args:
            session_id: Session ID of collaborator making the update
            update_data: Model update data
        """
        with self._lock:
            if session_id not in self.collaborators:
                return

            collaborator = self.collaborators[session_id]

            # Check permissions
            if not self._has_permission(collaborator, 'model_edit'):
                return

            # Update model state
            self.state_version += 1
            self.model_state.update(update_data)

            # Create model update message
            update_message = CollaborationMessage(
                event_type=CollaborationEvent.MODEL_UPDATE,
                user_id=collaborator.user_id,
                session_id=session_id,
                timestamp=time.time(),
                data={
                    'update_data': update_data,
                    'state_version': self.state_version,
                    'username': collaborator.username
                }
            )

            self.broadcast_message(update_message, exclude_session=session_id)

    def send_chat_message(self, session_id: str, message: str):
        """Send a chat message.

        Args:
            session_id: Session ID of sender
            message: Chat message content
        """
        with self._lock:
            if session_id not in self.collaborators:
                return

            collaborator = self.collaborators[session_id]

            if not self.settings.get('allow_chat', True):
                return

            chat_message = CollaborationMessage(
                event_type=CollaborationEvent.CHAT_MESSAGE,
                user_id=collaborator.user_id,
                session_id=session_id,
                timestamp=time.time(),
                data={
                    'message': message,
                    'username': collaborator.username
                }
            )

            self.broadcast_message(chat_message)

    def _has_permission(self, collaborator: Collaborator, permission: str) -> bool:
        """Check if collaborator has a specific permission."""
        if collaborator.role == 'admin':
            return True

        if collaborator.role == 'editor':
            return permission in ['model_edit', 'chat', 'view']

        if collaborator.role == 'viewer':
            return permission in ['chat', 'view']

        return False

    def _add_message(self, message: CollaborationMessage):
        """Add message to history."""
        self.message_history.append(message)

        if len(self.message_history) > self.max_messages:
            self.message_history = self.message_history[-self.max_messages:]

    def get_room_info(self) -> Dict[str, Any]:
        """Get room information."""
        with self._lock:
            return {
                'room_id': self.room_id,
                'model_id': self.model_id,
                'created_by': self.created_by,
                'created_at': self.created_at,
                'collaborator_count': len(self.collaborators),
                'collaborators': [
                    {
                        'user_id': c.user_id,
                        'username': c.username,
                        'role': c.role,
                        'color': c.color,
                        'last_activity': c.last_activity
                    }
                    for c in self.collaborators.values()
                ],
                'state_version': self.state_version,
                'settings': self.settings
            }


class CollaborationManager:
    """Manages multiple collaboration rooms and WebSocket connections."""

    def __init__(self):
        """Initialize collaboration manager."""
        self.logger = logging.getLogger(__name__)
        self.rooms: Dict[str, CollaborationRoom] = {}
        self.user_sessions: Dict[str, str] = {}  # session_id -> room_id
        self.websocket_connections: Dict[str, Any] = {}  # session_id -> websocket
        self._lock = threading.RLock()

    def create_room(self, model_id: str, created_by: str) -> str:
        """Create a new collaboration room.

        Args:
            model_id: ID of the 3D model
            created_by: User ID creating the room

        Returns:
            Room ID
        """
        room_id = str(uuid.uuid4())

        with self._lock:
            room = CollaborationRoom(room_id, model_id, created_by)
            self.rooms[room_id] = room

        self.logger.info(f"Created collaboration room {room_id} for model {model_id}")
        return room_id

    def join_room(self, room_id: str, collaborator: Collaborator) -> bool:
        """Join a collaboration room.

        Args:
            room_id: Room ID to join
            collaborator: Collaborator information

        Returns:
            True if joined successfully
        """
        with self._lock:
            if room_id not in self.rooms:
                return False

            room = self.rooms[room_id]

            if room.add_collaborator(collaborator):
                self.user_sessions[collaborator.session_id] = room_id

                # Send current room state to new collaborator
                room_info = room.get_room_info()
                self._send_to_session(collaborator.session_id, {
                    'type': 'room_state',
                    'data': room_info
                })

                return True

            return False

    def leave_room(self, session_id: str):
        """Leave a collaboration room.

        Args:
            session_id: Session ID leaving the room
        """
        with self._lock:
            if session_id not in self.user_sessions:
                return

            room_id = self.user_sessions[session_id]
            room = self.rooms[room_id]

            room.remove_collaborator(session_id)
            del self.user_sessions[session_id]

            # Clean up WebSocket connection if exists
            if session_id in self.websocket_connections:
                del self.websocket_connections[session_id]

    def handle_websocket_message(self, session_id: str, message: Dict[str, Any]):
        """Handle a WebSocket message.

        Args:
            session_id: Session ID of sender
            message: Message data
        """
        with self._lock:
            if session_id not in self.user_sessions:
                return

            room_id = self.user_sessions[session_id]
            room = self.rooms[room_id]

            try:
                message_type = message.get('type')

                if message_type == 'cursor_update':
                    room.update_collaborator_activity(session_id, {
                        'cursor_position': message.get('cursor_position', {})
                    })

                elif message_type == 'viewport_update':
                    room.update_collaborator_activity(session_id, {
                        'viewport_state': message.get('viewport_state', {})
                    })

                elif message_type == 'model_update':
                    room.handle_model_update(session_id, message.get('update_data', {}))

                elif message_type == 'chat_message':
                    room.send_chat_message(session_id, message.get('message', ''))

                elif message_type == 'design_change':
                    room.handle_model_update(session_id, message.get('changes', {}))

                # Broadcast the message to other collaborators
                broadcast_message = CollaborationMessage(
                    event_type=CollaborationEvent.MODEL_UPDATE,  # Generic event type
                    user_id=message.get('user_id', 'unknown'),
                    session_id=session_id,
                    timestamp=time.time(),
                    data=message
                )

                room.broadcast_message(broadcast_message, exclude_session=session_id)

            except Exception as e:
                self.logger.error(f"Error handling WebSocket message: {e}")

    def register_websocket_connection(self, session_id: str, websocket):
        """Register a WebSocket connection.

        Args:
            session_id: Session ID
            websocket: WebSocket connection object
        """
        with self._lock:
            self.websocket_connections[session_id] = websocket
            self.logger.debug(f"Registered WebSocket connection for session {session_id}")

    def unregister_websocket_connection(self, session_id: str):
        """Unregister a WebSocket connection.

        Args:
            session_id: Session ID
        """
        with self._lock:
            self.websocket_connections.pop(session_id, None)
            self.logger.debug(f"Unregistered WebSocket connection for session {session_id}")

    def _send_to_session(self, session_id: str, data: Dict[str, Any]):
        """Send data to a specific session.

        Args:
            session_id: Target session ID
            data: Data to send
        """
        websocket = self.websocket_connections.get(session_id)
        if websocket:
            try:
                message = json.dumps(data)
                # Here you would send via WebSocket
                # asyncio.create_task(websocket.send_text(message))
                self.logger.debug(f"Sending to session {session_id}: {data.get('type', 'unknown')}")
            except Exception as e:
                self.logger.error(f"Failed to send to session {session_id}: {e}")

    def get_room_list(self) -> List[Dict[str, Any]]:
        """Get list of all active rooms.

        Returns:
            List of room information
        """
        with self._lock:
            return [room.get_room_info() for room in self.rooms.values()]

    def cleanup_inactive_rooms(self, max_inactive_minutes: float = 60.0):
        """Clean up inactive collaboration rooms.

        Args:
            max_inactive_minutes: Maximum inactive time before cleanup
        """
        with self._lock:
            current_time = time.time()
            inactive_threshold = max_inactive_minutes * 60

            rooms_to_remove = []
            for room_id, room in self.rooms.items():
                # Check if room has been inactive
                if current_time - room.created_at > inactive_threshold:
                    # Check if all collaborators have been inactive for too long
                    all_inactive = True
                    for collaborator in room.collaborators.values():
                        if current_time - collaborator.last_activity < inactive_threshold:
                            all_inactive = False
                            break

                    if all_inactive:
                        rooms_to_remove.append(room_id)

            for room_id in rooms_to_remove:
                del self.rooms[room_id]
                self.logger.info(f"Cleaned up inactive room: {room_id}")

    def get_collaboration_stats(self) -> Dict[str, Any]:
        """Get collaboration system statistics.

        Returns:
            Dictionary with collaboration statistics
        """
        with self._lock:
            active_users = len(self.user_sessions)
            active_rooms = len(self.rooms)

            return {
                'active_rooms': active_rooms,
                'active_users': active_users,
                'total_rooms_created': len(self.rooms),  # This would need to be tracked separately
                'websocket_connections': len(self.websocket_connections),
                'messages_sent': sum(len(room.message_history) for room in self.rooms.values())
            }


class WebSocketHandler:
    """Handles WebSocket connections for real-time collaboration."""

    def __init__(self, collaboration_manager: CollaborationManager):
        """Initialize WebSocket handler.

        Args:
            collaboration_manager: Collaboration manager instance
        """
        self.logger = logging.getLogger(__name__)
        self.collaboration_manager = collaboration_manager

    async def handle_connection(self, websocket, session_id: str):
        """Handle a WebSocket connection.

        Args:
            websocket: WebSocket connection
            session_id: Session ID
        """
        try:
            # Register connection
            self.collaboration_manager.register_websocket_connection(session_id, websocket)

            async for message in websocket:
                try:
                    # Parse message
                    data = json.loads(message)

                    # Handle message
                    self.collaboration_manager.handle_websocket_message(session_id, data)

                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid JSON message from session {session_id}")
                except Exception as e:
                    self.logger.error(f"Error handling message from session {session_id}: {e}")

        except Exception as e:
            self.logger.error(f"WebSocket connection error for session {session_id}: {e}")
        finally:
            # Clean up connection
            self.collaboration_manager.unregister_websocket_connection(session_id)
            self.collaboration_manager.leave_room(session_id)


class CollaborationAPI:
    """API for managing real-time collaboration."""

    def __init__(self):
        """Initialize collaboration API."""
        self.logger = logging.getLogger(__name__)
        self.collaboration_manager = CollaborationManager()
        self.websocket_handler = WebSocketHandler(self.collaboration_manager)

        # Start cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="CollaborationCleanup"
        )
        self._cleanup_thread.start()

    def create_collaboration_session(self, model_id: str, user_id: str,
                                   username: str, role: str = "viewer") -> Dict[str, Any]:
        """Create a new collaboration session.

        Args:
            model_id: ID of the 3D model
            user_id: User ID
            username: Username
            role: User role

        Returns:
            Session information
        """
        # Create room
        room_id = self.collaboration_manager.create_room(model_id, user_id)

        # Create collaborator
        collaborator = Collaborator(
            user_id=user_id,
            username=username,
            session_id=str(uuid.uuid4()),
            role=role
        )

        # Join room
        success = self.collaboration_manager.join_room(room_id, collaborator)

        if success:
            return {
                'success': True,
                'room_id': room_id,
                'session_id': collaborator.session_id,
                'collaborator': {
                    'user_id': collaborator.user_id,
                    'username': collaborator.username,
                    'role': collaborator.role,
                    'color': collaborator.color
                }
            }
        else:
            return {'success': False, 'error': 'Failed to create collaboration session'}

    def join_collaboration_session(self, room_id: str, user_id: str,
                                 username: str, role: str = "viewer") -> Dict[str, Any]:
        """Join an existing collaboration session.

        Args:
            room_id: Room ID to join
            user_id: User ID
            username: Username
            role: User role

        Returns:
            Session information
        """
        collaborator = Collaborator(
            user_id=user_id,
            username=username,
            session_id=str(uuid.uuid4()),
            role=role
        )

        success = self.collaboration_manager.join_room(room_id, collaborator)

        if success:
            return {
                'success': True,
                'room_id': room_id,
                'session_id': collaborator.session_id,
                'collaborator': {
                    'user_id': collaborator.user_id,
                    'username': collaborator.username,
                    'role': collaborator.role,
                    'color': collaborator.color
                }
            }
        else:
            return {'success': False, 'error': 'Failed to join collaboration session'}

    def leave_collaboration_session(self, session_id: str) -> bool:
        """Leave a collaboration session.

        Args:
            session_id: Session ID

        Returns:
            True if left successfully
        """
        self.collaboration_manager.leave_room(session_id)
        return True

    def send_collaboration_message(self, session_id: str, message_type: str,
                                 data: Dict[str, Any]) -> bool:
        """Send a collaboration message.

        Args:
            session_id: Session ID
            message_type: Type of message
            data: Message data

        Returns:
            True if sent successfully
        """
        message = {
            'type': message_type,
            'timestamp': time.time(),
            **data
        }

        self.collaboration_manager.handle_websocket_message(session_id, message)
        return True

    def get_collaboration_rooms(self) -> List[Dict[str, Any]]:
        """Get list of active collaboration rooms.

        Returns:
            List of room information
        """
        return self.collaboration_manager.get_room_list()

    def get_collaboration_stats(self) -> Dict[str, Any]:
        """Get collaboration system statistics.

        Returns:
            Dictionary with collaboration statistics
        """
        return self.collaboration_manager.get_collaboration_stats()

    def _cleanup_loop(self):
        """Cleanup inactive rooms periodically."""
        while True:
            try:
                self.collaboration_manager.cleanup_inactive_rooms()
                time.sleep(300)  # Clean up every 5 minutes
            except Exception as e:
                self.logger.error(f"Error in collaboration cleanup: {e}")
                time.sleep(60)


# Global collaboration API
collaboration_api = CollaborationAPI()
