"""WebSocket support for real-time updates."""
from flask_socketio import SocketIO, emit, join_room, leave_room
from typing import Dict, Any, Optional
import json
import time
from ..core.progress import get_progress_tracker, ProgressTask


class WebSocketManager:
    """Manage WebSocket connections and events."""

    def __init__(self, app=None):
        """Initialize WebSocket manager."""
        self.socketio = None
        self.active_connections: Dict[str, set] = {}

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask app."""
        self.socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            async_mode='threading'
        )
        self._register_handlers()
        self._setup_progress_listener()

        return self.socketio

    def _register_handlers(self):
        """Register WebSocket event handlers."""

        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            emit('connected', {
                'message': 'Connected to server',
                'timestamp': time.time()
            })

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            # Remove from all rooms
            for room in list(self.active_connections.keys()):
                if hasattr(request, 'sid'):
                    leave_room(room)
                    if request.sid in self.active_connections.get(room, set()):
                        self.active_connections[room].discard(request.sid)

        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """Subscribe to specific updates."""
            room = data.get('room', 'general')
            join_room(room)

            if room not in self.active_connections:
                self.active_connections[room] = set()

            if hasattr(request, 'sid'):
                self.active_connections[room].add(request.sid)

            emit('subscribed', {
                'room': room,
                'message': f'Subscribed to {room}'
            })

        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """Unsubscribe from updates."""
            room = data.get('room', 'general')
            leave_room(room)

            if hasattr(request, 'sid') and room in self.active_connections:
                self.active_connections[room].discard(request.sid)

            emit('unsubscribed', {
                'room': room,
                'message': f'Unsubscribed from {room}'
            })

        @self.socketio.on('ping')
        def handle_ping():
            """Handle ping for connection keepalive."""
            emit('pong', {'timestamp': time.time()})

    def _setup_progress_listener(self):
        """Setup listener for progress updates."""
        tracker = get_progress_tracker()

        def on_progress_update(task: ProgressTask):
            """Send progress updates via WebSocket."""
            self.broadcast_progress(task)

        tracker.add_listener(on_progress_update)

    def broadcast_progress(self, task: ProgressTask):
        """Broadcast progress update to all connected clients."""
        if not self.socketio:
            return

        data = task.to_dict()

        # Send to task-specific room
        self.socketio.emit(
            'progress_update',
            data,
            room=f'task_{task.task_id}'
        )

        # Send to general progress room
        self.socketio.emit(
            'progress_update',
            data,
            room='progress'
        )

    def send_notification(
        self,
        event: str,
        data: Dict[str, Any],
        room: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Send notification to clients.

        Args:
            event: Event name
            data: Event data
            room: Optional room to send to
            user_id: Optional specific user to send to
        """
        if not self.socketio:
            return

        if user_id:
            # Send to specific user
            self.socketio.emit(event, data, to=user_id)
        elif room:
            # Send to room
            self.socketio.emit(event, data, room=room)
        else:
            # Broadcast to all
            self.socketio.emit(event, data)

    def send_validation_result(self, file_id: str, result: Dict[str, Any]):
        """Send validation result."""
        self.send_notification(
            'validation_complete',
            {
                'file_id': file_id,
                'result': result,
                'timestamp': time.time()
            },
            room=f'file_{file_id}'
        )

    def send_repair_result(self, file_id: str, result: Dict[str, Any]):
        """Send repair result."""
        self.send_notification(
            'repair_complete',
            {
                'file_id': file_id,
                'result': result,
                'timestamp': time.time()
            },
            room=f'file_{file_id}'
        )

    def send_slicing_result(self, file_id: str, result: Dict[str, Any]):
        """Send slicing result."""
        self.send_notification(
            'slicing_complete',
            {
                'file_id': file_id,
                'result': result,
                'timestamp': time.time()
            },
            room=f'file_{file_id}'
        )

    def send_error(self, error: str, details: Optional[Dict[str, Any]] = None):
        """Send error notification."""
        self.send_notification(
            'error',
            {
                'error': error,
                'details': details or {},
                'timestamp': time.time()
            }
        )

    def get_connection_count(self, room: Optional[str] = None) -> int:
        """Get number of connected clients.

        Args:
            room: Optional room to count connections for

        Returns:
            Number of connected clients
        """
        if room:
            return len(self.active_connections.get(room, set()))

        total = 0
        for connections in self.active_connections.values():
            total += len(connections)
        return total


# Global WebSocket manager
_ws_manager = WebSocketManager()


def get_websocket_manager() -> WebSocketManager:
    """Get global WebSocket manager instance."""
    return _ws_manager


def init_websocket(app):
    """Initialize WebSocket support for Flask app."""
    return _ws_manager.init_app(app)