"""Cloud-specific features including storage and real-time collaboration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union, Callable
import os
import json
import time
import uuid
from pathlib import Path
from datetime import datetime, timedelta
import logging
import hashlib
import threading
import queue


class CloudStorageProvider(Enum):
    """Supported cloud storage providers."""
    AWS_S3 = "aws_s3"
    GOOGLE_CLOUD_STORAGE = "google_cloud_storage"
    AZURE_BLOB_STORAGE = "azure_blob_storage"
    DROPBOX = "dropbox"
    ONEDRIVE = "onedrive"
    LOCAL_SIMULATION = "local_simulation"  # For development/testing


class CollaborationMode(Enum):
    """Types of real-time collaboration modes."""
    VIEW_ONLY = "view_only"
    COMMENT_ONLY = "comment_only"
    EDIT_RESTRICTED = "edit_restricted"
    FULL_COLLABORATION = "full_collaboration"
    MASTER_SLAVE = "master_slave"


@dataclass
class CloudFile:
    """A file stored in the cloud."""

    id: str
    name: str
    path: str
    size: int
    mime_type: str
    hash: str
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    owner_id: str = ""
    permissions: Dict[str, str] = field(default_factory=dict)  # user_id -> permission
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollaborationSession:
    """A real-time collaboration session."""

    id: str
    file_id: str
    participants: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # user_id -> user_info
    mode: CollaborationMode = CollaborationMode.FULL_COLLABORATION
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    max_participants: int = 10
    is_active: bool = True


@dataclass
class CollaborationEvent:
    """An event in a collaboration session."""

    event_type: str  # "cursor_move", "selection_change", "edit", "comment", etc.
    user_id: str
    timestamp: datetime
    data: Dict[str, Any]
    session_id: str


@dataclass
class CloudProject:
    """A project stored in the cloud."""

    id: str
    name: str
    description: Optional[str] = None
    owner_id: str
    files: List[CloudFile] = field(default_factory=list)
    collaborators: Dict[str, str] = field(default_factory=dict)  # user_id -> role
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    settings: Dict[str, Any] = field(default_factory=dict)


class CloudStorageManager:
    """Manages cloud storage operations."""

    def __init__(self, provider: CloudStorageProvider = CloudStorageProvider.LOCAL_SIMULATION):
        self.provider = provider
        self.logger = logging.getLogger(__name__)
        self._setup_provider()

    def _setup_provider(self):
        """Setup the cloud storage provider."""

        if self.provider == CloudStorageProvider.AWS_S3:
            # Import boto3 and setup S3 client
            try:
                import boto3
                self.s3_client = boto3.client('s3')
                self.bucket_name = os.getenv('AWS_S3_BUCKET', '3dprint-cad-files')
            except ImportError:
                self.logger.warning("boto3 not available. Using local simulation.")
                self.provider = CloudStorageProvider.LOCAL_SIMULATION

        elif self.provider == CloudStorageProvider.GOOGLE_CLOUD_STORAGE:
            # Setup GCS client
            try:
                from google.cloud import storage
                self.gcs_client = storage.Client()
                self.bucket_name = os.getenv('GCS_BUCKET', '3dprint-cad-files')
            except ImportError:
                self.logger.warning("google-cloud-storage not available. Using local simulation.")
                self.provider = CloudStorageProvider.LOCAL_SIMULATION

        elif self.provider == CloudStorageProvider.AZURE_BLOB_STORAGE:
            # Setup Azure client
            try:
                from azure.storage.blob import BlobServiceClient
                connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
                self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                self.container_name = os.getenv('AZURE_CONTAINER', '3dprint-cad-files')
            except ImportError:
                self.logger.warning("azure-storage-blob not available. Using local simulation.")
                self.provider = CloudStorageProvider.LOCAL_SIMULATION

        # For local simulation, create a local directory
        if self.provider == CloudStorageProvider.LOCAL_SIMULATION:
            self.local_storage_path = Path("./cloud_storage_simulation")
            self.local_storage_path.mkdir(exist_ok=True)
            self.logger.info("Using local storage simulation")

    def upload_file(self, local_path: str, cloud_path: str,
                   metadata: Optional[Dict[str, Any]] = None) -> Optional[CloudFile]:
        """Upload a file to cloud storage."""

        try:
            file_path = Path(local_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Local file not found: {local_path}")

            # Calculate file hash
            with open(file_path, 'rb') as f:
                file_content = f.read()
                file_hash = hashlib.sha256(file_content).hexdigest()

            file_size = len(file_content)
            file_id = str(uuid.uuid4())

            if self.provider == CloudStorageProvider.LOCAL_SIMULATION:
                # Simulate upload to local storage
                cloud_file_path = self.local_storage_path / cloud_path
                cloud_file_path.parent.mkdir(parents=True, exist_ok=True)

                with open(cloud_file_path, 'wb') as f:
                    f.write(file_content)

            else:
                # Real cloud upload would go here
                self.logger.info(f"Simulating upload of {file_path.name} to {self.provider.value}")

            # Create CloudFile object
            cloud_file = CloudFile(
                id=file_id,
                name=file_path.name,
                path=cloud_path,
                size=file_size,
                mime_type=self._get_mime_type(file_path),
                hash=file_hash,
                metadata=metadata or {}
            )

            return cloud_file

        except Exception as e:
            self.logger.error(f"Error uploading file: {e}")
            return None

    def download_file(self, cloud_file: CloudFile, local_path: str) -> bool:
        """Download a file from cloud storage."""

        try:
            if self.provider == CloudStorageProvider.LOCAL_SIMULATION:
                cloud_file_path = self.local_storage_path / cloud_file.path

                with open(cloud_file_path, 'rb') as src:
                    with open(local_path, 'wb') as dst:
                        dst.write(src.read())

            else:
                # Real cloud download would go here
                self.logger.info(f"Simulating download of {cloud_file.name}")

            return True

        except Exception as e:
            self.logger.error(f"Error downloading file: {e}")
            return False

    def delete_file(self, cloud_file: CloudFile) -> bool:
        """Delete a file from cloud storage."""

        try:
            if self.provider == CloudStorageProvider.LOCAL_SIMULATION:
                cloud_file_path = self.local_storage_path / cloud_file.path
                if cloud_file_path.exists():
                    cloud_file_path.unlink()

            return True

        except Exception as e:
            self.logger.error(f"Error deleting file: {e}")
            return False

    def list_files(self, prefix: str = "") -> List[CloudFile]:
        """List files in cloud storage with optional prefix."""

        try:
            files = []

            if self.provider == CloudStorageProvider.LOCAL_SIMULATION:
                # List local files
                for file_path in self.local_storage_path.rglob("*"):
                    if file_path.is_file() and str(file_path).startswith(str(self.local_storage_path / prefix)):
                        relative_path = file_path.relative_to(self.local_storage_path)

                        # Create CloudFile object (simplified)
                        cloud_file = CloudFile(
                            id=str(uuid.uuid4()),
                            name=file_path.name,
                            path=str(relative_path),
                            size=file_path.stat().st_size,
                            mime_type=self._get_mime_type(file_path),
                            hash=""  # Would calculate in real implementation
                        )
                        files.append(cloud_file)

            return files

        except Exception as e:
            self.logger.error(f"Error listing files: {e}")
            return []

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type for a file."""

        extension = file_path.suffix.lower()

        mime_types = {
            '.stl': 'application/sla',
            '.obj': 'application/object',
            '.ply': 'application/ply',
            '.3mf': 'application/3mf',
            '.amf': 'application/amf',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.gif': 'image/gif'
        }

        return mime_types.get(extension, 'application/octet-stream')


class RealTimeCollaborationManager:
    """Manages real-time collaboration sessions."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sessions: Dict[str, CollaborationSession] = {}
        self.event_queues: Dict[str, queue.Queue] = {}
        self.participant_cursors: Dict[str, Dict[str, Any]] = {}  # session_id -> {user_id: cursor_info}
        self._cleanup_thread = None
        self._start_cleanup_thread()

    def create_session(self, file_id: str, owner_id: str,
                      mode: CollaborationMode = CollaborationMode.FULL_COLLABORATION) -> CollaborationSession:
        """Create a new collaboration session."""

        session_id = str(uuid.uuid4())

        session = CollaborationSession(
            id=session_id,
            file_id=file_id,
            mode=mode
        )

        # Add owner as participant
        session.participants[owner_id] = {
            "role": "owner",
            "joined_at": datetime.now(),
            "status": "active"
        }

        self.sessions[session_id] = session
        self.event_queues[session_id] = queue.Queue()
        self.participant_cursors[session_id] = {}

        self.logger.info(f"Created collaboration session {session_id} for file {file_id}")
        return session

    def join_session(self, session_id: str, user_id: str, user_info: Dict[str, Any]) -> bool:
        """Join an existing collaboration session."""

        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        if len(session.participants) >= session.max_participants:
            return False

        session.participants[user_id] = {
            "role": user_info.get("role", "participant"),
            "joined_at": datetime.now(),
            "status": "active",
            **user_info
        }

        session.last_activity = datetime.now()

        # Broadcast join event
        self._broadcast_event(session_id, CollaborationEvent(
            event_type="user_joined",
            user_id=user_id,
            timestamp=datetime.now(),
            data={"user_info": user_info},
            session_id=session_id
        ))

        self.logger.info(f"User {user_id} joined session {session_id}")
        return True

    def leave_session(self, session_id: str, user_id: str) -> bool:
        """Leave a collaboration session."""

        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        if user_id in session.participants:
            del session.participants[user_id]

            # Clean up empty sessions
            if not session.participants:
                session.is_active = False

            # Broadcast leave event
            self._broadcast_event(session_id, CollaborationEvent(
                event_type="user_left",
                user_id=user_id,
                timestamp=datetime.now(),
                data={},
                session_id=session_id
            ))

            self.logger.info(f"User {user_id} left session {session_id}")
            return True

        return False

    def send_event(self, session_id: str, event: CollaborationEvent) -> bool:
        """Send a collaboration event to all participants."""

        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        session.last_activity = datetime.now()

        self._broadcast_event(session_id, event)
        return True

    def update_cursor_position(self, session_id: str, user_id: str,
                             cursor_data: Dict[str, Any]) -> bool:
        """Update a participant's cursor position."""

        if session_id not in self.participant_cursors:
            self.participant_cursors[session_id] = {}

        self.participant_cursors[session_id][user_id] = {
            **cursor_data,
            "timestamp": datetime.now()
        }

        # Broadcast cursor update
        cursor_event = CollaborationEvent(
            event_type="cursor_update",
            user_id=user_id,
            timestamp=datetime.now(),
            data=cursor_data,
            session_id=session_id
        )

        self._broadcast_event(session_id, cursor_event)
        return True

    def get_session_participants(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all participants in a session."""

        if session_id not in self.sessions:
            return {}

        session = self.sessions[session_id]
        return dict(session.participants)

    def get_cursor_positions(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        """Get cursor positions for all participants in a session."""

        return self.participant_cursors.get(session_id, {})

    def _broadcast_event(self, session_id: str, event: CollaborationEvent):
        """Broadcast an event to all participants in a session."""

        if session_id in self.event_queues:
            try:
                self.event_queues[session_id].put(event, timeout=1)
            except queue.Full:
                self.logger.warning(f"Event queue full for session {session_id}")

    def get_pending_events(self, session_id: str, user_id: str) -> List[CollaborationEvent]:
        """Get pending events for a specific user."""

        if session_id not in self.event_queues:
            return []

        events = []
        event_queue = self.event_queues[session_id]

        # Get events, but don't block
        while not event_queue.empty():
            try:
                event = event_queue.get_nowait()
                # Filter events (users don't need their own events)
                if event.user_id != user_id:
                    events.append(event)
            except queue.Empty:
                break

        return events

    def _start_cleanup_thread(self):
        """Start background thread to clean up inactive sessions."""

        def cleanup_worker():
            while True:
                try:
                    time.sleep(300)  # Check every 5 minutes

                    current_time = datetime.now()
                    inactive_sessions = []

                    for session_id, session in self.sessions.items():
                        # Mark sessions inactive after 1 hour of no activity
                        if (current_time - session.last_activity) > timedelta(hours=1):
                            session.is_active = False
                            inactive_sessions.append(session_id)

                        # Remove sessions with no participants after 10 minutes
                        elif not session.participants and (current_time - session.created_at) > timedelta(minutes=10):
                            inactive_sessions.append(session_id)

                    # Clean up inactive sessions
                    for session_id in inactive_sessions:
                        self._cleanup_session(session_id)

                except Exception as e:
                    self.logger.error(f"Error in cleanup thread: {e}")

        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()

    def _cleanup_session(self, session_id: str):
        """Clean up a session and its resources."""

        if session_id in self.sessions:
            del self.sessions[session_id]

        if session_id in self.event_queues:
            del self.event_queues[session_id]

        if session_id in self.participant_cursors:
            del self.participant_cursors[session_id]

        self.logger.info(f"Cleaned up session {session_id}")


class CloudProjectManager:
    """Manages cloud-based projects and collaboration."""

    def __init__(self, storage_manager: CloudStorageManager,
                 collaboration_manager: RealTimeCollaborationManager):
        self.storage = storage_manager
        self.collaboration = collaboration_manager
        self.logger = logging.getLogger(__name__)
        self.projects: Dict[str, CloudProject] = {}
        self.project_sessions: Dict[str, str] = {}  # project_id -> session_id

    def create_project(self, name: str, owner_id: str,
                      description: Optional[str] = None) -> CloudProject:
        """Create a new cloud project."""

        project_id = str(uuid.uuid4())

        project = CloudProject(
            id=project_id,
            name=name,
            description=description,
            owner_id=owner_id
        )

        # Add owner as collaborator
        project.collaborators[owner_id] = "owner"

        self.projects[project_id] = project
        self.logger.info(f"Created project {project_id}: {name}")

        return project

    def add_file_to_project(self, project_id: str, local_path: str,
                           cloud_path: str, user_id: str) -> Optional[CloudFile]:
        """Add a file to a cloud project."""

        if project_id not in self.projects:
            return None

        project = self.projects[project_id]

        # Check permissions
        if user_id not in project.collaborators:
            return None

        # Upload file
        cloud_file = self.storage.upload_file(local_path, cloud_path, {
            "project_id": project_id,
            "uploaded_by": user_id
        })

        if cloud_file:
            project.files.append(cloud_file)
            project.modified_at = datetime.now()

        return cloud_file

    def start_collaboration_session(self, project_id: str, file_id: str,
                                  user_id: str) -> Optional[CollaborationSession]:
        """Start a collaboration session for a project file."""

        if project_id not in self.projects:
            return None

        project = self.projects[project_id]

        # Check if user has access
        if user_id not in project.collaborators:
            return None

        # Find the file
        target_file = None
        for file in project.files:
            if file.id == file_id:
                target_file = file
                break

        if not target_file:
            return None

        # Create or reuse collaboration session
        if project_id in self.project_sessions:
            session_id = self.project_sessions[project_id]
            if session_id in self.collaboration.sessions:
                session = self.collaboration.sessions[session_id]
                if session.is_active:
                    return session

        # Create new session
        session = self.collaboration.create_session(file_id, user_id)
        self.project_sessions[project_id] = session.id

        return session

    def invite_collaborator(self, project_id: str, owner_id: str,
                          collaborator_id: str, role: str = "editor") -> bool:
        """Invite a collaborator to a project."""

        if project_id not in self.projects:
            return False

        project = self.projects[project_id]

        # Only owner can invite collaborators
        if project.owner_id != owner_id:
            return False

        project.collaborators[collaborator_id] = role
        self.logger.info(f"Added collaborator {collaborator_id} to project {project_id}")

        return True

    def get_project_files(self, project_id: str, user_id: str) -> List[CloudFile]:
        """Get files in a project that a user has access to."""

        if project_id not in self.projects:
            return []

        project = self.projects[project_id]

        # Check access
        if user_id not in project.collaborators:
            return []

        return project.files

    def export_project_manifest(self, project_id: str, file_path: str) -> bool:
        """Export project manifest as JSON."""

        if project_id not in self.projects:
            return False

        project = self.projects[project_id]

        manifest = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "owner_id": project.owner_id,
            "created_at": project.created_at.isoformat(),
            "modified_at": project.modified_at.isoformat(),
            "collaborators": project.collaborators,
            "settings": project.settings,
            "files": [
                {
                    "id": f.id,
                    "name": f.name,
                    "path": f.path,
                    "size": f.size,
                    "mime_type": f.mime_type,
                    "hash": f.hash,
                    "version": f.version,
                    "created_at": f.created_at.isoformat(),
                    "modified_at": f.modified_at.isoformat(),
                    "owner_id": f.owner_id
                }
                for f in project.files
            ]
        }

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"Error exporting project manifest: {e}")
            return False


# Global instances
cloud_storage = CloudStorageManager()
collaboration_manager = RealTimeCollaborationManager()
cloud_project_manager = CloudProjectManager(cloud_storage, collaboration_manager)


def create_cloud_project(name: str, owner_id: str, description: Optional[str] = None) -> CloudProject:
    """Convenience function to create a cloud project."""
    return cloud_project_manager.create_project(name, owner_id, description)


def upload_to_cloud(local_path: str, cloud_path: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[CloudFile]:
    """Convenience function to upload a file to cloud storage."""
    return cloud_storage.upload_file(local_path, cloud_path, metadata)


def start_collaboration_session(project_id: str, file_id: str, user_id: str) -> Optional[CollaborationSession]:
    """Convenience function to start a collaboration session."""
    return cloud_project_manager.start_collaboration_session(project_id, file_id, user_id)
