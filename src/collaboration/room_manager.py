"""Collaboration room management for real-time teamwork."""
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid
import time
import threading
from datetime import datetime, timedelta


class RoomStatus(Enum):
    """Room status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class UserStatus(Enum):
    """User status in room."""
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"


@dataclass
class User:
    """User in collaboration room."""
    id: str
    name: str
    avatar: Optional[str] = None
    role: str = "member"
    status: UserStatus = UserStatus.OFFLINE
    last_seen: datetime = field(default_factory=datetime.now)
    cursor_position: Optional[Dict[str, Any]] = None
    current_file: Optional[str] = None


@dataclass
class RoomMessage:
    """Message in collaboration room."""
    id: str
    user_id: str
    content: str
    timestamp: datetime
    message_type: str = "chat"  # chat, system, notification
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileReference:
    """Reference to a file in the room."""
    id: str
    name: str
    path: str
    size: int
    uploaded_by: str
    uploaded_at: datetime
    last_modified: datetime
    version: int = 1
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None


class CollaborationRoom:
    """Real-time collaboration room for 3D print projects."""

    def __init__(
        self,
        room_id: str,
        name: str,
        created_by: str,
        max_users: int = 50
    ):
        """Initialize collaboration room.

        Args:
            room_id: Unique room identifier
            name: Room name
            created_by: User ID who created the room
            max_users: Maximum number of users
        """
        self.id = room_id
        self.name = name
        self.created_by = created_by
        self.created_at = datetime.now()
        self.max_users = max_users
        self.status = RoomStatus.ACTIVE

        # Room state
        self.users: Dict[str, User] = {}
        self.messages: List[RoomMessage] = []
        self.files: Dict[str, FileReference] = {}
        self.settings: Dict[str, Any] = {
            'allow_file_upload': True,
            'allow_guest_access': False,
            'auto_save_interval': 30,  # seconds
            'max_file_size': 100,  # MB
            'allowed_file_types': ['.stl', '.obj', '.ply', '.3mf', '.amf']
        }

        # Synchronization
        self._lock = threading.RLock()
        self._last_activity = datetime.now()

    def add_user(self, user: User) -> bool:
        """Add user to room.

        Args:
            user: User to add

        Returns:
            True if added successfully
        """
        with self._lock:
            if len(self.users) >= self.max_users:
                return False

            self.users[user.id] = user
            user.status = UserStatus.ONLINE
            user.last_seen = datetime.now()

            # Send system message
            self._add_system_message(f"{user.name} joined the room")
            self._update_activity()

            return True

    def remove_user(self, user_id: str) -> bool:
        """Remove user from room.

        Args:
            user_id: User ID to remove

        Returns:
            True if removed successfully
        """
        with self._lock:
            if user_id not in self.users:
                return False

            user = self.users[user_id]

            # Release any file locks
            self._release_user_locks(user_id)

            # Update status and remove
            user.status = UserStatus.OFFLINE
            del self.users[user_id]

            # Send system message
            self._add_system_message(f"{user.name} left the room")
            self._update_activity()

            return True

    def update_user_status(self, user_id: str, status: UserStatus) -> bool:
        """Update user status.

        Args:
            user_id: User ID
            status: New status

        Returns:
            True if updated successfully
        """
        with self._lock:
            if user_id not in self.users:
                return False

            user = self.users[user_id]
            old_status = user.status
            user.status = status
            user.last_seen = datetime.now()

            # Notify status change if significant
            if old_status != status and status in [UserStatus.ONLINE, UserStatus.OFFLINE]:
                status_text = "online" if status == UserStatus.ONLINE else "offline"
                self._add_system_message(f"{user.name} is now {status_text}")

            self._update_activity()
            return True

    def update_user_cursor(self, user_id: str, position: Dict[str, Any]) -> bool:
        """Update user cursor position.

        Args:
            user_id: User ID
            position: Cursor position data

        Returns:
            True if updated successfully
        """
        with self._lock:
            if user_id not in self.users:
                return False

            self.users[user_id].cursor_position = position
            self.users[user_id].last_seen = datetime.now()
            self._update_activity()

            return True

    def add_message(self, user_id: str, content: str, message_type: str = "chat") -> Optional[RoomMessage]:
        """Add message to room.

        Args:
            user_id: User ID sending message
            content: Message content
            message_type: Type of message

        Returns:
            Created message or None if failed
        """
        with self._lock:
            if user_id not in self.users:
                return None

            message = RoomMessage(
                id=str(uuid.uuid4()),
                user_id=user_id,
                content=content,
                timestamp=datetime.now(),
                message_type=message_type
            )

            self.messages.append(message)

            # Keep only last 1000 messages
            if len(self.messages) > 1000:
                self.messages = self.messages[-1000:]

            self._update_activity()
            return message

    def add_file(self, file_ref: FileReference) -> bool:
        """Add file to room.

        Args:
            file_ref: File reference to add

        Returns:
            True if added successfully
        """
        with self._lock:
            if not self.settings['allow_file_upload']:
                return False

            # Check file type
            file_ext = file_ref.name.lower().split('.')[-1]
            if f".{file_ext}" not in self.settings['allowed_file_types']:
                return False

            # Check file size
            if file_ref.size > self.settings['max_file_size'] * 1024 * 1024:
                return False

            self.files[file_ref.id] = file_ref

            # Add system message
            uploader = self.users.get(file_ref.uploaded_by)
            uploader_name = uploader.name if uploader else "Unknown"
            self._add_system_message(f"{uploader_name} uploaded {file_ref.name}")

            self._update_activity()
            return True

    def lock_file(self, file_id: str, user_id: str) -> bool:
        """Lock file for editing.

        Args:
            file_id: File ID to lock
            user_id: User ID requesting lock

        Returns:
            True if locked successfully
        """
        with self._lock:
            if file_id not in self.files:
                return False

            file_ref = self.files[file_id]

            # Check if already locked
            if file_ref.locked_by and file_ref.locked_by != user_id:
                # Check if lock is expired (5 minutes)
                if file_ref.locked_at and datetime.now() - file_ref.locked_at < timedelta(minutes=5):
                    return False

            file_ref.locked_by = user_id
            file_ref.locked_at = datetime.now()

            # Update user's current file
            if user_id in self.users:
                self.users[user_id].current_file = file_id

            self._update_activity()
            return True

    def unlock_file(self, file_id: str, user_id: str) -> bool:
        """Unlock file.

        Args:
            file_id: File ID to unlock
            user_id: User ID requesting unlock

        Returns:
            True if unlocked successfully
        """
        with self._lock:
            if file_id not in self.files:
                return False

            file_ref = self.files[file_id]

            # Only owner can unlock or if lock expired
            if file_ref.locked_by != user_id:
                if file_ref.locked_at and datetime.now() - file_ref.locked_at < timedelta(minutes=5):
                    return False

            file_ref.locked_by = None
            file_ref.locked_at = None

            # Clear user's current file
            if user_id in self.users:
                self.users[user_id].current_file = None

            self._update_activity()
            return True

    def update_file_version(self, file_id: str, user_id: str) -> bool:
        """Update file version.

        Args:
            file_id: File ID to update
            user_id: User making the update

        Returns:
            True if updated successfully
        """
        with self._lock:
            if file_id not in self.files:
                return False

            file_ref = self.files[file_id]

            # Check if user has lock
            if file_ref.locked_by != user_id:
                return False

            file_ref.version += 1
            file_ref.last_modified = datetime.now()

            self._update_activity()
            return True

    def get_online_users(self) -> List[User]:
        """Get list of online users.

        Returns:
            List of online users
        """
        with self._lock:
            return [
                user for user in self.users.values()
                if user.status == UserStatus.ONLINE
            ]

    def get_recent_messages(self, limit: int = 50) -> List[RoomMessage]:
        """Get recent messages.

        Args:
            limit: Maximum number of messages

        Returns:
            List of recent messages
        """
        with self._lock:
            return self.messages[-limit:] if self.messages else []

    def get_file_list(self) -> List[FileReference]:
        """Get list of files in room.

        Returns:
            List of file references
        """
        with self._lock:
            return list(self.files.values())

    def cleanup_inactive_users(self, timeout_minutes: int = 30) -> int:
        """Remove users inactive for too long.

        Args:
            timeout_minutes: Timeout in minutes

        Returns:
            Number of users removed
        """
        with self._lock:
            cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
            inactive_users = []

            for user_id, user in self.users.items():
                if user.last_seen < cutoff_time:
                    inactive_users.append(user_id)

            for user_id in inactive_users:
                self.remove_user(user_id)

            return len(inactive_users)

    def archive(self) -> None:
        """Archive the room."""
        with self._lock:
            self.status = RoomStatus.ARCHIVED

            # Remove all users
            for user_id in list(self.users.keys()):
                self.remove_user(user_id)

    def to_dict(self, include_messages: bool = False) -> Dict[str, Any]:
        """Convert room to dictionary.

        Args:
            include_messages: Include message history

        Returns:
            Room dictionary
        """
        with self._lock:
            result = {
                'id': self.id,
                'name': self.name,
                'created_by': self.created_by,
                'created_at': self.created_at.isoformat(),
                'status': self.status.value,
                'user_count': len(self.users),
                'online_users': len(self.get_online_users()),
                'file_count': len(self.files),
                'last_activity': self._last_activity.isoformat(),
                'settings': self.settings.copy()
            }

            if include_messages:
                result['messages'] = [
                    {
                        'id': msg.id,
                        'user_id': msg.user_id,
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat(),
                        'type': msg.message_type
                    }
                    for msg in self.messages
                ]

            return result

    def _add_system_message(self, content: str) -> None:
        """Add system message.

        Args:
            content: Message content
        """
        message = RoomMessage(
            id=str(uuid.uuid4()),
            user_id="system",
            content=content,
            timestamp=datetime.now(),
            message_type="system"
        )
        self.messages.append(message)

    def _release_user_locks(self, user_id: str) -> None:
        """Release all locks held by user.

        Args:
            user_id: User ID
        """
        for file_ref in self.files.values():
            if file_ref.locked_by == user_id:
                file_ref.locked_by = None
                file_ref.locked_at = None

    def _update_activity(self) -> None:
        """Update last activity timestamp."""
        self._last_activity = datetime.now()


class RoomManager:
    """Manage multiple collaboration rooms."""

    def __init__(self):
        """Initialize room manager."""
        self.rooms: Dict[str, CollaborationRoom] = {}
        self._lock = threading.RLock()

    def create_room(
        self,
        name: str,
        created_by: str,
        room_id: Optional[str] = None,
        **kwargs
    ) -> CollaborationRoom:
        """Create new collaboration room.

        Args:
            name: Room name
            created_by: Creator user ID
            room_id: Optional room ID (generated if None)
            **kwargs: Additional room parameters

        Returns:
            Created room
        """
        with self._lock:
            if room_id is None:
                room_id = str(uuid.uuid4())

            room = CollaborationRoom(
                room_id=room_id,
                name=name,
                created_by=created_by,
                **kwargs
            )

            self.rooms[room_id] = room
            return room

    def get_room(self, room_id: str) -> Optional[CollaborationRoom]:
        """Get room by ID.

        Args:
            room_id: Room ID

        Returns:
            Room or None if not found
        """
        with self._lock:
            return self.rooms.get(room_id)

    def delete_room(self, room_id: str) -> bool:
        """Delete room.

        Args:
            room_id: Room ID to delete

        Returns:
            True if deleted successfully
        """
        with self._lock:
            if room_id not in self.rooms:
                return False

            # Archive room first
            self.rooms[room_id].archive()

            # Remove from manager
            del self.rooms[room_id]
            return True

    def list_rooms(
        self,
        user_id: Optional[str] = None,
        status: Optional[RoomStatus] = None
    ) -> List[Dict[str, Any]]:
        """List rooms.

        Args:
            user_id: Filter by user membership
            status: Filter by room status

        Returns:
            List of room information
        """
        with self._lock:
            rooms = []

            for room in self.rooms.values():
                # Filter by status
                if status and room.status != status:
                    continue

                # Filter by user membership
                if user_id and user_id not in room.users:
                    continue

                rooms.append(room.to_dict())

            return rooms

    def cleanup_inactive_rooms(self, hours_inactive: int = 24) -> int:
        """Clean up inactive rooms.

        Args:
            hours_inactive: Hours of inactivity before cleanup

        Returns:
            Number of rooms cleaned up
        """
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours_inactive)
            inactive_rooms = []

            for room_id, room in self.rooms.items():
                if room._last_activity < cutoff_time and len(room.users) == 0:
                    inactive_rooms.append(room_id)

            for room_id in inactive_rooms:
                self.delete_room(room_id)

            return len(inactive_rooms)

    def get_user_rooms(self, user_id: str) -> List[str]:
        """Get rooms that user is member of.

        Args:
            user_id: User ID

        Returns:
            List of room IDs
        """
        with self._lock:
            user_rooms = []

            for room_id, room in self.rooms.items():
                if user_id in room.users:
                    user_rooms.append(room_id)

            return user_rooms

    def broadcast_to_room(
        self,
        room_id: str,
        event: str,
        data: Dict[str, Any],
        exclude_user: Optional[str] = None
    ) -> int:
        """Broadcast event to all users in room.

        Args:
            room_id: Room ID
            event: Event name
            data: Event data
            exclude_user: User ID to exclude from broadcast

        Returns:
            Number of users notified
        """
        room = self.get_room(room_id)
        if not room:
            return 0

        notified = 0
        for user in room.get_online_users():
            if exclude_user and user.id == exclude_user:
                continue

            # In real implementation, this would send via WebSocket
            # For now, just count notifications
            notified += 1

        return notified