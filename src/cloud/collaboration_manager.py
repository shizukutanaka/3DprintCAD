"""Cloud integration and collaboration management for 3D printing."""

import asyncio
import json
import hashlib
import base64
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import uuid
import aiohttp
import websockets
from pathlib import Path
import threading
import queue
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

class ShareLevel(Enum):
    """Sharing permission levels."""
    PRIVATE = "private"
    VIEW_ONLY = "view_only"
    COLLABORATE = "collaborate"
    PUBLIC = "public"

class SyncStatus(Enum):
    """Synchronization status."""
    SYNCED = "synced"
    PENDING = "pending"
    SYNCING = "syncing"
    CONFLICT = "conflict"
    ERROR = "error"

class ActivityType(Enum):
    """Types of collaboration activities."""
    FILE_UPLOAD = "file_upload"
    FILE_EDIT = "file_edit"
    COMMENT_ADDED = "comment_added"
    SETTINGS_CHANGED = "settings_changed"
    PRINT_STARTED = "print_started"
    PRINT_COMPLETED = "print_completed"
    SHARE_CREATED = "share_created"

@dataclass
class CloudProject:
    """Cloud-synchronized project."""
    id: str
    name: str
    description: str
    owner_id: str
    share_level: ShareLevel
    collaborators: List[str]
    files: List[str]
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    sync_status: SyncStatus = SyncStatus.SYNCED
    local_path: Optional[str] = None
    cloud_version: int = 1
    local_version: int = 1

@dataclass
class CloudFile:
    """Cloud-synchronized file."""
    id: str
    project_id: str
    name: str
    path: str
    size: int
    checksum: str
    file_type: str
    version: int
    created_at: datetime
    updated_at: datetime
    uploaded_by: str
    sync_status: SyncStatus = SyncStatus.SYNCED
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class Comment:
    """Collaboration comment."""
    id: str
    project_id: str
    file_id: Optional[str]
    author_id: str
    author_name: str
    content: str
    position: Optional[Dict[str, float]]  # 3D position for model comments
    created_at: datetime
    updated_at: datetime
    replies: List['Comment'] = None
    resolved: bool = False

    def __post_init__(self):
        if self.replies is None:
            self.replies = []

@dataclass
class Activity:
    """Project activity log entry."""
    id: str
    project_id: str
    user_id: str
    user_name: str
    type: ActivityType
    description: str
    details: Dict[str, Any]
    timestamp: datetime

@dataclass
class PrintJob:
    """Shared print job information."""
    id: str
    project_id: str
    file_id: str
    printer_id: str
    owner_id: str
    status: str
    settings: Dict[str, Any]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    progress: float
    estimated_time: float
    actual_time: Optional[float]
    shared_with: List[str] = None

    def __post_init__(self):
        if self.shared_with is None:
            self.shared_with = []

class CloudAPI:
    """Cloud service API client."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def create_project(self, project: CloudProject) -> Dict:
        """Create new cloud project."""
        async with self.session.post(
            f"{self.base_url}/projects",
            json=asdict(project)
        ) as response:
            return await response.json()

    async def update_project(self, project: CloudProject) -> Dict:
        """Update cloud project."""
        async with self.session.put(
            f"{self.base_url}/projects/{project.id}",
            json=asdict(project)
        ) as response:
            return await response.json()

    async def get_project(self, project_id: str) -> Dict:
        """Get project from cloud."""
        async with self.session.get(
            f"{self.base_url}/projects/{project_id}"
        ) as response:
            return await response.json()

    async def list_projects(self, user_id: str) -> List[Dict]:
        """List user's projects."""
        async with self.session.get(
            f"{self.base_url}/users/{user_id}/projects"
        ) as response:
            return await response.json()

    async def upload_file(self, file_path: str, project_id: str) -> Dict:
        """Upload file to cloud."""
        with open(file_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=Path(file_path).name)
            data.add_field('project_id', project_id)

            async with self.session.post(
                f"{self.base_url}/files",
                data=data
            ) as response:
                return await response.json()

    async def download_file(self, file_id: str, local_path: str) -> bool:
        """Download file from cloud."""
        async with self.session.get(
            f"{self.base_url}/files/{file_id}/download"
        ) as response:
            if response.status == 200:
                with open(local_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                return True
            return False

    async def add_comment(self, comment: Comment) -> Dict:
        """Add comment to project."""
        async with self.session.post(
            f"{self.base_url}/comments",
            json=asdict(comment)
        ) as response:
            return await response.json()

    async def get_comments(self, project_id: str) -> List[Dict]:
        """Get project comments."""
        async with self.session.get(
            f"{self.base_url}/projects/{project_id}/comments"
        ) as response:
            return await response.json()

    async def share_project(self, project_id: str, user_email: str, level: ShareLevel) -> Dict:
        """Share project with user."""
        async with self.session.post(
            f"{self.base_url}/projects/{project_id}/share",
            json={"email": user_email, "level": level.value}
        ) as response:
            return await response.json()

class CollaborationManager:
    """Manage cloud collaboration and synchronization."""

    def __init__(self, api_key: str, base_url: Optional[str] = None, websocket_url: Optional[str] = None):
        self.api_key = api_key
        base_url_candidate = base_url or os.environ.get("PRINTCAD_COLLAB_BASE_URL")
        if not base_url_candidate:
            raise ValueError(
                "Collaboration base URL must be provided via argument or "
                "PRINTCAD_COLLAB_BASE_URL environment variable."
            )

        # Validate and sanitize base URL
        parsed = urlparse(base_url_candidate)
        if parsed.scheme != "https":
            raise ValueError("Collaboration base URL must use HTTPS scheme.")
        if not parsed.netloc:
            raise ValueError("Collaboration base URL must have a valid hostname.")
        if parsed.netloc.startswith('.') or '..' in parsed.netloc:
            raise ValueError("Invalid hostname in collaboration base URL.")

        # Reconstruct URL to remove any path/query/fragment for security
        self.base_url = f"https://{parsed.netloc}"

        websocket_candidate = websocket_url or os.environ.get("PRINTCAD_COLLAB_WS_URL")
        if websocket_candidate:
            parsed_ws = urlparse(websocket_candidate)
            if parsed_ws.scheme != "wss":
                raise ValueError("Collaboration WebSocket URL must use WSS scheme.")
            if not parsed_ws.netloc:
                raise ValueError("Collaboration WebSocket URL must have a valid hostname.")
            if parsed_ws.netloc.startswith('.') or '..' in parsed_ws.netloc:
                raise ValueError("Invalid hostname in WebSocket URL.")
            # Reconstruct to ensure clean URL
            self.websocket_endpoint = f"wss://{parsed_ws.netloc}/collaborate"
        else:
            # Derive default WSS endpoint from base API host
            self.websocket_endpoint = f"wss://{parsed.netloc}/collaborate"

        self.projects = {}
        self.files = {}
        self.comments = {}
        self.activities = {}
        self.print_jobs = {}
        self.websocket = None
        self.sync_queue = queue.Queue()
        self.sync_thread = None
        self.running = False

        self.user_id = None
        self.user_name = None

    async def initialize(self, user_id: str, user_name: str):
        """Initialize collaboration manager."""
        self.user_id = user_id
        self.user_name = user_name

        # Load local projects and sync with cloud
        await self.sync_projects()

        # Start real-time collaboration
        await self.start_realtime_sync()

        # Start sync thread
        self.running = True
        self.sync_thread = threading.Thread(target=self._sync_worker)
        self.sync_thread.start()

    async def create_project(self, name: str, description: str,
                           share_level: ShareLevel = ShareLevel.PRIVATE) -> str:
        """Create new collaborative project."""

        project_id = str(uuid.uuid4())
        project = CloudProject(
            id=project_id,
            name=name,
            description=description,
            owner_id=self.user_id,
            share_level=share_level,
            collaborators=[],
            files=[],
            settings={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Create locally
        self.projects[project_id] = project

        # Queue for cloud sync
        self.sync_queue.put(("create_project", project))

        # Log activity
        await self.add_activity(project_id, ActivityType.SHARE_CREATED,
                              f"Project '{name}' created")

        return project_id

    async def upload_file(self, project_id: str, file_path: str,
                         file_type: str = "model") -> str:
        """Upload file to project."""

        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")

        # Calculate checksum
        checksum = self._calculate_checksum(file_path)

        file_id = str(uuid.uuid4())
        cloud_file = CloudFile(
            id=file_id,
            project_id=project_id,
            name=Path(file_path).name,
            path=file_path,
            size=Path(file_path).stat().st_size,
            checksum=checksum,
            file_type=file_type,
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            uploaded_by=self.user_id,
            sync_status=SyncStatus.PENDING
        )

        # Add to project
        self.files[file_id] = cloud_file
        self.projects[project_id].files.append(file_id)

        # Queue for upload
        self.sync_queue.put(("upload_file", cloud_file))

        # Log activity
        await self.add_activity(project_id, ActivityType.FILE_UPLOAD,
                              f"File '{Path(file_path).name}' uploaded")

        return file_id

    async def add_comment(self, project_id: str, content: str,
                         file_id: Optional[str] = None,
                         position: Optional[Dict[str, float]] = None) -> str:
        """Add comment to project or file."""

        comment_id = str(uuid.uuid4())
        comment = Comment(
            id=comment_id,
            project_id=project_id,
            file_id=file_id,
            author_id=self.user_id,
            author_name=self.user_name,
            content=content,
            position=position,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Add locally
        if project_id not in self.comments:
            self.comments[project_id] = []
        self.comments[project_id].append(comment)

        # Queue for cloud sync
        self.sync_queue.put(("add_comment", comment))

        # Log activity
        await self.add_activity(project_id, ActivityType.COMMENT_ADDED,
                              f"Comment added: {content[:50]}...")

        # Notify collaborators
        await self.notify_collaborators(project_id, "comment_added", {
            "comment_id": comment_id,
            "author": self.user_name,
            "content": content
        })

        return comment_id

    async def share_project(self, project_id: str, user_email: str,
                          level: ShareLevel) -> bool:
        """Share project with another user."""

        project = self.projects.get(project_id)
        if not project:
            return False

        if self.user_id != project.owner_id:
            return False  # Only owner can share

        # Queue for cloud sync
        self.sync_queue.put(("share_project", {
            "project_id": project_id,
            "user_email": user_email,
            "level": level
        }))

        # Log activity
        await self.add_activity(project_id, ActivityType.SHARE_CREATED,
                              f"Project shared with {user_email} ({level.value})")

        return True

    async def start_print_job(self, project_id: str, file_id: str,
                            printer_id: str, settings: Dict) -> str:
        """Start collaborative print job."""

        job_id = str(uuid.uuid4())
        print_job = PrintJob(
            id=job_id,
            project_id=project_id,
            file_id=file_id,
            printer_id=printer_id,
            owner_id=self.user_id,
            status="starting",
            settings=settings,
            start_time=datetime.now(),
            progress=0.0,
            estimated_time=settings.get("estimated_time", 0.0)
        )

        self.print_jobs[job_id] = print_job

        # Share with project collaborators
        project = self.projects.get(project_id)
        if project:
            print_job.shared_with = project.collaborators.copy()

        # Queue for cloud sync
        self.sync_queue.put(("start_print_job", print_job))

        # Log activity
        await self.add_activity(project_id, ActivityType.PRINT_STARTED,
                              f"Print job started on {printer_id}")

        # Notify collaborators
        await self.notify_collaborators(project_id, "print_started", {
            "job_id": job_id,
            "printer_id": printer_id,
            "file_name": self.files[file_id].name if file_id in self.files else "Unknown"
        })

        return job_id

    async def update_print_progress(self, job_id: str, progress: float,
                                  status: str = None):
        """Update print job progress."""

        print_job = self.print_jobs.get(job_id)
        if not print_job:
            return

        print_job.progress = progress
        if status:
            print_job.status = status

        if status == "completed":
            print_job.end_time = datetime.now()
            print_job.actual_time = (print_job.end_time - print_job.start_time).total_seconds() / 60

            # Log activity
            await self.add_activity(print_job.project_id, ActivityType.PRINT_COMPLETED,
                                  f"Print job completed in {print_job.actual_time:.1f} minutes")

        # Queue for cloud sync
        self.sync_queue.put(("update_print_job", print_job))

        # Notify collaborators
        await self.notify_collaborators(print_job.project_id, "print_progress", {
            "job_id": job_id,
            "progress": progress,
            "status": status
        })

    async def get_project_activities(self, project_id: str) -> List[Activity]:
        """Get project activity log."""

        return self.activities.get(project_id, [])

    async def get_project_comments(self, project_id: str) -> List[Comment]:
        """Get project comments."""

        return self.comments.get(project_id, [])

    async def sync_projects(self):
        """Synchronize projects with cloud."""

        async with CloudAPI(self.base_url, self.api_key) as api:
            try:
                # Get cloud projects
                cloud_projects = await api.list_projects(self.user_id)

                for project_data in cloud_projects:
                    project = CloudProject(**project_data)
                    self.projects[project.id] = project

                    # Sync project files and comments
                    await self._sync_project_data(api, project.id)

            except Exception as e:
                print(f"Sync error: {e}")

    async def start_realtime_sync(self):
        """Start real-time collaboration WebSocket."""

        try:
            parsed = urlparse(self.websocket_endpoint)
            query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))
            query_items["token"] = self.api_key
            ws_url = urlunparse(parsed._replace(query=urlencode(query_items)))

            self.websocket = await websockets.connect(
                ws_url,
                ping_interval=30,
                ping_timeout=20,
                max_queue=32,
            )

            # Start message handler
            asyncio.create_task(self._handle_realtime_messages())

        except Exception as e:
            print(f"WebSocket connection error: {e}")

    async def notify_collaborators(self, project_id: str, event_type: str, data: Dict):
        """Send real-time notification to collaborators."""

        if not self.websocket:
            return

        message = {
            "type": "notification",
            "project_id": project_id,
            "event_type": event_type,
            "data": data,
            "sender_id": self.user_id,
            "timestamp": datetime.now().isoformat()
        }

        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            print(f"Notification error: {e}")

    async def add_activity(self, project_id: str, activity_type: ActivityType,
                         description: str, details: Dict = None):
        """Add activity to project log."""

        activity = Activity(
            id=str(uuid.uuid4()),
            project_id=project_id,
            user_id=self.user_id,
            user_name=self.user_name,
            type=activity_type,
            description=description,
            details=details or {},
            timestamp=datetime.now()
        )

        if project_id not in self.activities:
            self.activities[project_id] = []

        self.activities[project_id].append(activity)

        # Keep only last 100 activities
        self.activities[project_id] = self.activities[project_id][-100:]

        # Queue for cloud sync
        self.sync_queue.put(("add_activity", activity))

    async def _sync_project_data(self, api: CloudAPI, project_id: str):
        """Sync project files and comments."""

        try:
            # Get project comments
            comments_data = await api.get_comments(project_id)
            self.comments[project_id] = [Comment(**c) for c in comments_data]

        except Exception as e:
            print(f"Project data sync error: {e}")

    async def _handle_realtime_messages(self):
        """Handle incoming real-time collaboration messages."""

        if not self.websocket:
            return

        try:
            async for message in self.websocket:
                data = json.loads(message)

                if data["type"] == "notification":
                    await self._handle_collaboration_notification(data)
                elif data["type"] == "sync_update":
                    await self._handle_sync_update(data)

        except Exception as e:
            print(f"WebSocket message error: {e}")

    async def _handle_collaboration_notification(self, data: Dict):
        """Handle collaboration notification."""

        event_type = data["event_type"]
        project_id = data["project_id"]

        if event_type == "comment_added":
            # Refresh comments for project
            await self._refresh_project_comments(project_id)
        elif event_type == "print_progress":
            # Update print job status
            job_data = data["data"]
            job_id = job_data["job_id"]
            if job_id in self.print_jobs:
                self.print_jobs[job_id].progress = job_data["progress"]
                if "status" in job_data:
                    self.print_jobs[job_id].status = job_data["status"]

    async def _handle_sync_update(self, data: Dict):
        """Handle sync update notification."""

        update_type = data["update_type"]
        project_id = data["project_id"]

        if update_type == "project_updated":
            # Refresh project data
            await self._refresh_project(project_id)
        elif update_type == "file_uploaded":
            # Refresh project files
            await self._refresh_project_files(project_id)

    async def _refresh_project_comments(self, project_id: str):
        """Refresh project comments from cloud."""

        async with CloudAPI(self.base_url, self.api_key) as api:
            try:
                comments_data = await api.get_comments(project_id)
                self.comments[project_id] = [Comment(**c) for c in comments_data]
            except Exception as e:
                print(f"Comment refresh error: {e}")

    async def _refresh_project(self, project_id: str):
        """Refresh project from cloud."""

        async with CloudAPI(self.base_url, self.api_key) as api:
            try:
                project_data = await api.get_project(project_id)
                self.projects[project_id] = CloudProject(**project_data)
            except Exception as e:
                print(f"Project refresh error: {e}")

    async def _refresh_project_files(self, project_id: str):
        """Refresh project files from cloud."""

        # Implementation would fetch updated file list
        pass

    def _sync_worker(self):
        """Background worker for cloud synchronization."""

        while self.running:
            try:
                # Get sync task (timeout to check running flag)
                operation, data = self.sync_queue.get(timeout=1.0)

                # Execute sync operation
                asyncio.run(self._execute_sync_operation(operation, data))

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Sync worker error: {e}")

    async def _execute_sync_operation(self, operation: str, data: Any):
        """Execute cloud sync operation."""

        async with CloudAPI(self.base_url, self.api_key) as api:
            try:
                if operation == "create_project":
                    await api.create_project(data)
                elif operation == "upload_file":
                    await api.upload_file(data.path, data.project_id)
                    data.sync_status = SyncStatus.SYNCED
                elif operation == "add_comment":
                    await api.add_comment(data)
                elif operation == "share_project":
                    await api.share_project(
                        data["project_id"],
                        data["user_email"],
                        data["level"]
                    )
                # Add more operations as needed

            except Exception as e:
                print(f"Sync operation '{operation}' failed: {e}")

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate file checksum."""

        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def shutdown(self):
        """Shutdown collaboration manager."""

        self.running = False

        if self.sync_thread:
            self.sync_thread.join(timeout=5.0)

        if self.websocket:
            asyncio.run(self.websocket.close())