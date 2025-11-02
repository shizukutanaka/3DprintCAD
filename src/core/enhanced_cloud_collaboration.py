#!/usr/bin/env python3
"""
強化されたクラウドコラボレーションシステム
Fusion 360スタイルのリアルタイム共同編集とプロジェクト管理機能
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum

from ..core.config import get_config
from ..core.logging import get_logger
from ..core.i18n_optimized import get_text as _

class CollaborationRole(Enum):
    """コラボレーション役割"""
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    COMMENTER = "commenter"

class ProjectStatus(Enum):
    """プロジェクトステータス"""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ARCHIVED = "archived"

class ActivityType(Enum):
    """アクティビティの種類"""
    CREATE = "create"
    MODIFY = "modify"
    COMMENT = "comment"
    APPROVE = "approve"
    SHARE = "share"
    EXPORT = "export"

@dataclass
class CollaborationUser:
    """コラボレーションユーザー"""
    user_id: str
    username: str
    email: str
    role: CollaborationRole
    joined_at: str
    last_active: str
    avatar_url: Optional[str] = None
    permissions: List[str] = field(default_factory=list)

@dataclass
class ProjectComment:
    """プロジェクトコメント"""
    comment_id: str
    user_id: str
    username: str
    content: str
    timestamp: str
    position: Optional[Dict[str, float]] = None  # 3D空間での位置
    element_id: Optional[str] = None  # 関連する要素ID

@dataclass
class CollaborationProject:
    """コラボレーションプロジェクト"""
    project_id: str
    name: str
    description: str
    owner_id: str
    status: ProjectStatus
    created_at: str
    updated_at: str
    collaborators: Dict[str, CollaborationUser] = field(default_factory=dict)
    files: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    comments: List[ProjectComment] = field(default_factory=list)
    activity_log: List[Dict[str, Any]] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['status'] = self.status.value
        return data

class EnhancedCloudCollaborationManager:
    """強化されたクラウドコラボレーション管理システム"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.projects: Dict[str, CollaborationProject] = {}
        self.active_sessions: Dict[str, Set[str]] = {}  # project_id -> set of session_ids
        self.websocket_connections: Dict[str, List[Any]] = {}  # session_id -> connections

    def create_project(self, name: str, description: str, owner_id: str, owner_username: str) -> Dict[str, Any]:
        """新しいプロジェクトを作成"""
        project_id = f"project_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        project = CollaborationProject(
            project_id=project_id,
            name=name,
            description=description,
            owner_id=owner_id,
            status=ProjectStatus.DRAFT,
            created_at=self._get_timestamp(),
            updated_at=self._get_timestamp(),
            collaborators={
                owner_id: CollaborationUser(
                    user_id=owner_id,
                    username=owner_username,
                    email=f"{owner_username}@example.com",  # 実際には適切なメールアドレスを使用
                    role=CollaborationRole.OWNER,
                    joined_at=self._get_timestamp(),
                    last_active=self._get_timestamp()
                )
            }
        )

        self.projects[project_id] = project
        self.active_sessions[project_id] = set()

        # アクティビティログを記録
        self._log_activity(project_id, owner_id, owner_username, ActivityType.CREATE, f"Created project '{name}'")

        self.logger.info(f"Created collaboration project {project_id} by {owner_username}")

        return {
            "project_id": project_id,
            "project": project.to_dict(),
            "message": _("プロジェクトが作成されました", "Project has been created")
        }

    def invite_collaborator(self, project_id: str, inviter_id: str, invitee_email: str, role: str) -> Dict[str, Any]:
        """プロジェクトにコラボレーターを招待"""
        if project_id not in self.projects:
            raise ValueError("Project not found")

        project = self.projects[project_id]
        inviter = project.collaborators.get(inviter_id)

        if not inviter or inviter.role != CollaborationRole.OWNER:
            raise ValueError("Only project owners can invite collaborators")

        # 実際の実装では、メール送信や通知システムと連携
        invitee_id = f"user_{uuid.uuid4().hex[:8]}"
        invitee_username = invitee_email.split('@')[0]

        collaborator = CollaborationUser(
            user_id=invitee_id,
            username=invitee_username,
            email=invitee_email,
            role=CollaborationRole(role),
            joined_at=self._get_timestamp(),
            last_active=self._get_timestamp()
        )

        project.collaborators[invitee_id] = collaborator
        project.updated_at = self._get_timestamp()

        # アクティビティログを記録
        self._log_activity(project_id, inviter_id, inviter.username, ActivityType.SHARE,
                          f"Invited {invitee_username} as {role}")

        return {
            "success": True,
            "invitee_id": invitee_id,
            "message": _("招待が送信されました", "Invitation has been sent")
        }

    def update_project_status(self, project_id: str, user_id: str, new_status: str) -> Dict[str, Any]:
        """プロジェクトステータスを更新"""
        if project_id not in self.projects:
            raise ValueError("Project not found")

        project = self.projects[project_id]
        user = project.collaborators.get(user_id)

        if not user or user.role not in [CollaborationRole.OWNER, CollaborationRole.EDITOR]:
            raise ValueError("Insufficient permissions")

        old_status = project.status
        project.status = ProjectStatus(new_status)
        project.updated_at = self._get_timestamp()

        # アクティビティログを記録
        self._log_activity(project_id, user_id, user.username, ActivityType.MODIFY,
                          f"Changed status from {old_status.value} to {new_status}")

        # 全コラボレーターに通知
        self._broadcast_to_project(project_id, {
            "type": "status_change",
            "project_id": project_id,
            "new_status": new_status,
            "updated_by": user.username,
            "timestamp": project.updated_at
        })

        return {
            "success": True,
            "new_status": new_status,
            "message": _("ステータスが更新されました", "Status has been updated")
        }

    def add_comment(self, project_id: str, user_id: str, content: str,
                   position: Optional[Dict[str, float]] = None,
                   element_id: Optional[str] = None) -> Dict[str, Any]:
        """プロジェクトにコメントを追加"""
        if project_id not in self.projects:
            raise ValueError("Project not found")

        project = self.projects[project_id]
        user = project.collaborators.get(user_id)

        if not user or user.role not in [CollaborationRole.OWNER, CollaborationRole.EDITOR, CollaborationRole.COMMENTER]:
            raise ValueError("Insufficient permissions")

        comment = ProjectComment(
            comment_id=f"comment_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            username=user.username,
            content=content,
            timestamp=self._get_timestamp(),
            position=position,
            element_id=element_id
        )

        project.comments.append(comment)
        project.updated_at = self._get_timestamp()

        # アクティビティログを記録
        self._log_activity(project_id, user_id, user.username, ActivityType.COMMENT,
                          f"Added comment: {content[:50]}...")

        # 全コラボレーターに通知
        self._broadcast_to_project(project_id, {
            "type": "new_comment",
            "comment": comment.__dict__,
            "project_id": project_id
        })

        return {
            "success": True,
            "comment_id": comment.comment_id,
            "message": _("コメントが追加されました", "Comment has been added")
        }

    def upload_file(self, project_id: str, user_id: str, file_name: str, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """プロジェクトにファイルをアップロード"""
        if project_id not in self.projects:
            raise ValueError("Project not found")

        project = self.projects[project_id]
        user = project.collaborators.get(user_id)

        if not user or user.role not in [CollaborationRole.OWNER, CollaborationRole.EDITOR]:
            raise ValueError("Insufficient permissions")

        file_id = f"file_{uuid.uuid4().hex[:8]}"

        file_info = {
            "file_id": file_id,
            "file_name": file_name,
            "uploaded_by": user_id,
            "uploaded_at": self._get_timestamp(),
            "file_size": len(json.dumps(file_data)),
            "file_type": file_data.get("type", "unknown"),
            "data": file_data  # 実際にはクラウドストレージに保存
        }

        project.files[file_id] = file_info
        project.updated_at = self._get_timestamp()

        # アクティビティログを記録
        self._log_activity(project_id, user_id, user.username, ActivityType.MODIFY,
                          f"Uploaded file: {file_name}")

        # 全コラボレーターに通知
        self._broadcast_to_project(project_id, {
            "type": "file_upload",
            "file_info": file_info,
            "project_id": project_id
        })

        return {
            "success": True,
            "file_id": file_id,
            "message": _("ファイルがアップロードされました", "File has been uploaded")
        }

    def join_collaboration_session(self, project_id: str, user_id: str) -> Dict[str, Any]:
        """コラボレーションセッションに参加"""
        if project_id not in self.projects:
            raise ValueError("Project not found")

        project = self.projects[project_id]
        user = project.collaborators.get(user_id)

        if not user:
            raise ValueError("User is not a collaborator on this project")

        session_id = f"session_{uuid.uuid4().hex[:8]}"

        if project_id not in self.active_sessions:
            self.active_sessions[project_id] = set()

        self.active_sessions[project_id].add(session_id)

        # ユーザーの最終アクティブ時間を更新
        user.last_active = self._get_timestamp()

        return {
            "session_id": session_id,
            "project": project.to_dict(),
            "active_collaborators": len(self.active_sessions[project_id]),
            "message": _("セッションに参加しました", "Joined collaboration session")
        }

    def leave_collaboration_session(self, session_id: str, project_id: str) -> Dict[str, Any]:
        """コラボレーションセッションから退出"""
        if project_id in self.active_sessions and session_id in self.active_sessions[project_id]:
            self.active_sessions[project_id].remove(session_id)

            if not self.active_sessions[project_id]:
                del self.active_sessions[project_id]

            return {
                "success": True,
                "message": _("セッションから退出しました", "Left collaboration session")
            }

        return {"error": "Session not found"}

    def broadcast_design_change(self, project_id: str, user_id: str, change_data: Dict[str, Any]) -> Dict[str, Any]:
        """デザイン変更をブロードキャスト"""
        if project_id not in self.projects:
            raise ValueError("Project not found")

        project = self.projects[project_id]
        user = project.collaborators.get(user_id)

        if not user or user.role not in [CollaborationRole.OWNER, CollaborationRole.EDITOR]:
            raise ValueError("Insufficient permissions")

        # アクティビティログを記録
        self._log_activity(project_id, user_id, user.username, ActivityType.MODIFY,
                          "Design change broadcast")

        # 全セッション参加者にブロードキャスト
        self._broadcast_to_project(project_id, {
            "type": "design_change",
            "user_id": user_id,
            "username": user.username,
            "change_data": change_data,
            "timestamp": self._get_timestamp()
        })

        return {
            "success": True,
            "broadcast_to": len(self.active_sessions.get(project_id, [])),
            "message": _("変更がブロードキャストされました", "Change has been broadcast")
        }

    def get_project_collaborators(self, project_id: str) -> Dict[str, Any]:
        """プロジェクトのコラボレーターを取得"""
        if project_id not in self.projects:
            raise ValueError("Project not found")

        project = self.projects[project_id]
        return {
            "collaborators": {k: v.__dict__ for k, v in project.collaborators.items()},
            "active_sessions": len(self.active_sessions.get(project_id, []))
        }

    def get_project_activity(self, project_id: str, limit: int = 50) -> Dict[str, Any]:
        """プロジェクトのアクティビティログを取得"""
        if project_id not in self.projects:
            raise ValueError("Project not found")

        project = self.projects[project_id]
        recent_activity = project.activity_log[-limit:] if project.activity_log else []

        return {
            "activity_log": recent_activity,
            "total_activities": len(project.activity_log)
        }

    def _log_activity(self, project_id: str, user_id: str, username: str, activity_type: ActivityType, description: str):
        """アクティビティをログに記録"""
        if project_id not in self.projects:
            return

        project = self.projects[project_id]

        activity = {
            "activity_id": f"activity_{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            "username": username,
            "type": activity_type.value,
            "description": description,
            "timestamp": self._get_timestamp()
        }

        project.activity_log.append(activity)

        # ログが大きくなりすぎないよう制限
        if len(project.activity_log) > 1000:
            project.activity_log = project.activity_log[-500:]

    def _broadcast_to_project(self, project_id: str, message: Dict[str, Any]):
        """プロジェクトの全参加者にメッセージをブロードキャスト"""
        if project_id in self.active_sessions:
            # 実際の実装ではWebSocketやリアルタイム通信システムと連携
            # ここではログに記録するだけ
            self.logger.info(f"Broadcasting to project {project_id}: {message}")

    def _get_timestamp(self) -> str:
        """タイムスタンプを取得"""
        return datetime.now(timezone.utc).isoformat()

# グローバルインスタンス
_collaboration_manager = None

def get_collaboration_manager() -> EnhancedCloudCollaborationManager:
    """クラウドコラボレーション管理システムのインスタンスを取得"""
    global _collaboration_manager
    if _collaboration_manager is None:
        _collaboration_manager = EnhancedCloudCollaborationManager()
    return _collaboration_manager
