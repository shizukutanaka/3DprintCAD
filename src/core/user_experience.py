"""User experience enhancement features for 3D Print CAD Assistant."""

import time
import threading
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class UXTheme(Enum):
    """UI theme options."""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class NotificationLevel(Enum):
    """Notification importance levels."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Notification:
    """User notification."""
    id: str
    level: NotificationLevel
    title: str
    message: str
    timestamp: float
    actions: List[Dict[str, str]] = field(default_factory=list)
    read: bool = False
    persistent: bool = False


@dataclass
class UserPreferences:
    """User interface preferences."""
    theme: UXTheme = UXTheme.AUTO
    language: str = "ja"
    notifications_enabled: bool = True
    auto_save: bool = True
    confirm_actions: bool = True
    show_tooltips: bool = True
    animations_enabled: bool = True


class NotificationManager:
    """Manages user notifications and alerts."""

    def __init__(self, max_notifications: int = 1000):
        """Initialize notification manager.

        Args:
            max_notifications: Maximum number of notifications to keep
        """
        self.logger = logging.getLogger(__name__)
        self.notifications: List[Notification] = []
        self.max_notifications = max_notifications
        self.handlers: List[Callable] = []
        self._lock = threading.RLock()

    def add_notification(self,
                        level: NotificationLevel,
                        title: str,
                        message: str,
                        actions: Optional[List[Dict[str, str]]] = None,
                        persistent: bool = False) -> str:
        """Add a notification.

        Args:
            level: Notification level
            title: Notification title
            message: Notification message
            actions: Optional action buttons
            persistent: Whether notification should persist until dismissed

        Returns:
            Notification ID
        """
        notification = Notification(
            id=f"notif_{int(time.time() * 1000)}",
            level=level,
            title=title,
            message=message,
            timestamp=time.time(),
            actions=actions or [],
            persistent=persistent
        )

        with self._lock:
            self.notifications.append(notification)

            # Remove old notifications if limit exceeded
            if len(self.notifications) > self.max_notifications:
                # Keep persistent notifications and remove oldest non-persistent ones
                persistent = [n for n in self.notifications if n.persistent]
                non_persistent = [n for n in self.notifications if not n.persistent]

                # Remove oldest non-persistent notifications
                to_remove = len(non_persistent) - (self.max_notifications - len(persistent))
                if to_remove > 0:
                    non_persistent = non_persistent[to_remove:]

                self.notifications = persistent + non_persistent

        # Notify handlers
        for handler in self.handlers:
            try:
                handler(notification)
            except Exception as e:
                self.logger.error(f"Notification handler failed: {e}")

        self.logger.info(f"Added {level.value} notification: {title}")
        return notification.id

    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read.

        Args:
            notification_id: Notification ID

        Returns:
            True if notification was found and marked as read
        """
        with self._lock:
            for notification in self.notifications:
                if notification.id == notification_id:
                    notification.read = True
                    return True
            return False

    def dismiss_notification(self, notification_id: str) -> bool:
        """Dismiss a notification.

        Args:
            notification_id: Notification ID

        Returns:
            True if notification was found and dismissed
        """
        with self._lock:
            for i, notification in enumerate(self.notifications):
                if notification.id == notification_id:
                    # Don't remove persistent notifications, just mark as read
                    if notification.persistent:
                        notification.read = True
                    else:
                        self.notifications.pop(i)
                    return True
            return False

    def get_notifications(self,
                         limit: int = 50,
                         unread_only: bool = False,
                         level: Optional[NotificationLevel] = None) -> List[Notification]:
        """Get notifications.

        Args:
            limit: Maximum number of notifications to return
            unread_only: Return only unread notifications
            level: Filter by notification level

        Returns:
            List of notifications
        """
        with self._lock:
            filtered = self.notifications

            if unread_only:
                filtered = [n for n in filtered if not n.read]

            if level:
                filtered = [n for n in filtered if n.level == level]

            return filtered[-limit:]

    def register_handler(self, handler: Callable):
        """Register a notification handler.

        Args:
            handler: Function to call when notifications are added
        """
        self.handlers.append(handler)

    def clear_all(self):
        """Clear all notifications."""
        with self._lock:
            self.notifications.clear()


class ProgressTracker:
    """Tracks progress of long-running operations."""

    def __init__(self):
        """Initialize progress tracker."""
        self.logger = logging.getLogger(__name__)
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        self.completed_operations: List[Dict[str, Any]] = []
        self.max_completed = 100
        self._lock = threading.RLock()

    def start_operation(self,
                       operation_id: str,
                       operation_name: str,
                       total_steps: int = 0,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start tracking an operation.

        Args:
            operation_id: Unique operation identifier
            operation_name: Human-readable operation name
            total_steps: Total number of steps (0 for unknown)
            metadata: Additional operation metadata

        Returns:
            Operation ID
        """
        with self._lock:
            self.active_operations[operation_id] = {
                'id': operation_id,
                'name': operation_name,
                'start_time': time.time(),
                'current_step': 0,
                'total_steps': total_steps,
                'status': 'running',
                'metadata': metadata or {},
                'progress_percent': 0.0,
                'last_update': time.time()
            }

        self.logger.info(f"Started operation: {operation_name} ({operation_id})")
        return operation_id

    def update_progress(self,
                       operation_id: str,
                       current_step: int,
                       status: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None):
        """Update operation progress.

        Args:
            operation_id: Operation identifier
            current_step: Current step number
            status: Operation status
            metadata: Updated metadata
        """
        with self._lock:
            if operation_id not in self.active_operations:
                self.logger.warning(f"Operation {operation_id} not found")
                return

            operation = self.active_operations[operation_id]
            operation['current_step'] = current_step
            operation['last_update'] = time.time()

            if operation['total_steps'] > 0:
                operation['progress_percent'] = (current_step / operation['total_steps']) * 100

            if status:
                operation['status'] = status

            if metadata:
                operation['metadata'].update(metadata)

    def complete_operation(self, operation_id: str, success: bool = True):
        """Mark an operation as completed.

        Args:
            operation_id: Operation identifier
            success: Whether operation completed successfully
        """
        with self._lock:
            if operation_id not in self.active_operations:
                return

            operation = self.active_operations.pop(operation_id)
            operation['end_time'] = time.time()
            operation['duration'] = operation['end_time'] - operation['start_time']
            operation['status'] = 'completed' if success else 'failed'
            operation['success'] = success

            # Move to completed list
            self.completed_operations.append(operation)

            if len(self.completed_operations) > self.max_completed:
                self.completed_operations = self.completed_operations[-self.max_completed:]

        status = "successfully" if success else "with errors"
        self.logger.info(f"Completed operation: {operation['name']} ({status})")

    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an operation.

        Args:
            operation_id: Operation identifier

        Returns:
            Operation status or None if not found
        """
        with self._lock:
            return self.active_operations.get(operation_id) or \
                   next((op for op in self.completed_operations if op['id'] == operation_id), None)

    def get_active_operations(self) -> List[Dict[str, Any]]:
        """Get all active operations.

        Returns:
            List of active operation statuses
        """
        with self._lock:
            return list(self.active_operations.values())

    def get_recent_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent completed operations.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of recent operations
        """
        with self._lock:
            return self.completed_operations[-limit:]


class UserFeedbackCollector:
    """Collects user feedback and usage analytics."""

    def __init__(self, feedback_file: Optional[Union[str, Path]] = None):
        """Initialize feedback collector.

        Args:
            feedback_file: File to store feedback data
        """
        self.logger = logging.getLogger(__name__)
        self.feedback_file = Path(feedback_file) if feedback_file else None
        self.feedback_data: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

        if self.feedback_file:
            self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
            self._load_feedback()

    def record_action(self, action: str, category: str, metadata: Optional[Dict[str, Any]] = None):
        """Record a user action.

        Args:
            action: Action performed
            category: Action category
            metadata: Additional metadata
        """
        feedback = {
            'type': 'action',
            'action': action,
            'category': category,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }

        with self._lock:
            self.feedback_data.append(feedback)

        self._save_feedback()

    def record_feedback(self,
                       feedback_type: str,
                       rating: int,
                       comment: str,
                       category: str = "general"):
        """Record user feedback.

        Args:
            feedback_type: Type of feedback (e.g., "usability", "performance")
            rating: Rating (1-5 scale)
            comment: User comment
            category: Feedback category
        """
        feedback = {
            'type': 'feedback',
            'feedback_type': feedback_type,
            'rating': rating,
            'comment': comment,
            'category': category,
            'timestamp': time.time()
        }

        with self._lock:
            self.feedback_data.append(feedback)

        self._save_feedback()
        self.logger.info(f"Recorded {feedback_type} feedback: {rating}/5")

    def record_error(self, error: str, context: str, metadata: Optional[Dict[str, Any]] = None):
        """Record an error or issue.

        Args:
            error: Error description
            context: Context where error occurred
            metadata: Additional error metadata
        """
        feedback = {
            'type': 'error',
            'error': error,
            'context': context,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }

        with self._lock:
            self.feedback_data.append(feedback)

        self._save_feedback()

    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics.

        Returns:
            Dictionary with feedback statistics
        """
        with self._lock:
            feedback_items = [item for item in self.feedback_data if item['type'] == 'feedback']
            action_items = [item for item in self.feedback_data if item['type'] == 'action']
            error_items = [item for item in self.feedback_data if item['type'] == 'error']

            # Calculate feedback ratings
            if feedback_items:
                avg_rating = sum(item['rating'] for item in feedback_items) / len(feedback_items)
            else:
                avg_rating = 0

            return {
                'total_feedback': len(feedback_items),
                'total_actions': len(action_items),
                'total_errors': len(error_items),
                'average_rating': avg_rating,
                'most_common_actions': self._get_most_common(action_items, 'action'),
                'most_common_errors': self._get_most_common(error_items, 'error')
            }

    def _get_most_common(self, items: List[Dict[str, Any]], field: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most common values for a field."""
        from collections import Counter

        if not items:
            return []

        counts = Counter(item[field] for item in items)
        return [{'value': value, 'count': count} for value, count in counts.most_common(limit)]

    def _load_feedback(self):
        """Load feedback data from file."""
        if not self.feedback_file or not self.feedback_file.exists():
            return

        try:
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                self.feedback_data = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load feedback data: {e}")

    def _save_feedback(self):
        """Save feedback data to file."""
        if not self.feedback_file:
            return

        try:
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(self.feedback_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save feedback data: {e}")


class AccessibilityManager:
    """Manages accessibility features."""

    def __init__(self):
        """Initialize accessibility manager."""
        self.logger = logging.getLogger(__name__)
        self.features = {
            'high_contrast': False,
            'large_text': False,
            'screen_reader': False,
            'keyboard_navigation': True,
            'voice_commands': False
        }

    def enable_feature(self, feature: str, enabled: bool = True):
        """Enable or disable an accessibility feature.

        Args:
            feature: Feature name
            enabled: Whether to enable the feature
        """
        if feature in self.features:
            self.features[feature] = enabled
            self.logger.info(f"{'Enabled' if enabled else 'Disabled'} accessibility feature: {feature}")
        else:
            self.logger.warning(f"Unknown accessibility feature: {feature}")

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if an accessibility feature is enabled.

        Args:
            feature: Feature name

        Returns:
            True if feature is enabled
        """
        return self.features.get(feature, False)

    def get_accessibility_settings(self) -> Dict[str, bool]:
        """Get all accessibility settings.

        Returns:
            Dictionary of accessibility features and their states
        """
        return self.features.copy()


class UserExperienceManager:
    """Main manager for user experience features."""

    def __init__(self):
        """Initialize user experience manager."""
        self.logger = logging.getLogger(__name__)
        self.preferences = UserPreferences()
        self.notifications = NotificationManager()
        self.progress = ProgressTracker()
        self.feedback = UserFeedbackCollector()
        self.accessibility = AccessibilityManager()

    def load_user_preferences(self, preferences_file: Optional[Union[str, Path]] = None):
        """Load user preferences from file.

        Args:
            preferences_file: Path to preferences file
        """
        if not preferences_file:
            preferences_file = Path.home() / '.3d_print_cad' / 'preferences.json'

        preferences_path = Path(preferences_file)

        if preferences_path.exists():
            try:
                with open(preferences_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Update preferences
                for key, value in data.items():
                    if hasattr(self.preferences, key):
                        setattr(self.preferences, key, value)

                self.logger.info(f"Loaded user preferences from {preferences_path}")

            except Exception as e:
                self.logger.error(f"Failed to load user preferences: {e}")

    def save_user_preferences(self, preferences_file: Optional[Union[str, Path]] = None):
        """Save user preferences to file.

        Args:
            preferences_file: Path to save preferences file
        """
        if not preferences_file:
            preferences_file = Path.home() / '.3d_print_cad' / 'preferences.json'

        preferences_path = Path(preferences_file)
        preferences_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            data = {
                'theme': self.preferences.theme.value,
                'language': self.preferences.language,
                'notifications_enabled': self.preferences.notifications_enabled,
                'auto_save': self.preferences.auto_save,
                'confirm_actions': self.preferences.confirm_actions,
                'show_tooltips': self.preferences.show_tooltips,
                'animations_enabled': self.preferences.animations_enabled
            }

            with open(preferences_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Saved user preferences to {preferences_path}")

        except Exception as e:
            self.logger.error(f"Failed to save user preferences: {e}")

    def show_notification(self,
                         level: NotificationLevel,
                         title: str,
                         message: str,
                         actions: Optional[List[Dict[str, str]]] = None):
        """Show a notification to the user.

        Args:
            level: Notification level
            title: Notification title
            message: Notification message
            actions: Optional action buttons
        """
        return self.notifications.add_notification(level, title, message, actions)

    def start_progress_operation(self, operation_name: str, total_steps: int = 0) -> str:
        """Start tracking a progress operation.

        Args:
            operation_name: Name of the operation
            total_steps: Total number of steps

        Returns:
            Operation ID
        """
        import uuid
        operation_id = str(uuid.uuid4())
        return self.progress.start_operation(operation_id, operation_name, total_steps)

    def update_progress(self, operation_id: str, current_step: int, status: Optional[str] = None):
        """Update progress of an operation.

        Args:
            operation_id: Operation ID
            current_step: Current step
            status: Operation status
        """
        self.progress.update_progress(operation_id, current_step, status)

    def complete_progress_operation(self, operation_id: str, success: bool = True):
        """Complete a progress operation.

        Args:
            operation_id: Operation ID
            success: Whether operation completed successfully
        """
        self.progress.complete_operation(operation_id, success)

    def record_user_action(self, action: str, category: str = "general"):
        """Record a user action for analytics.

        Args:
            action: Action performed
            category: Action category
        """
        self.feedback.record_action(action, category)

    def submit_feedback(self, feedback_type: str, rating: int, comment: str):
        """Submit user feedback.

        Args:
            feedback_type: Type of feedback
            rating: Rating (1-5)
            comment: User comment
        """
        self.feedback.record_feedback(feedback_type, rating, comment)

    def get_ux_stats(self) -> Dict[str, Any]:
        """Get user experience statistics.

        Returns:
            Dictionary with UX statistics
        """
        return {
            'preferences': {
                'theme': self.preferences.theme.value,
                'language': self.preferences.language,
                'notifications_enabled': self.preferences.notifications_enabled
            },
            'notifications': {
                'total': len(self.notifications.notifications),
                'unread': len([n for n in self.notifications.notifications if not n.read])
            },
            'progress': {
                'active_operations': len(self.progress.active_operations),
                'recent_operations': len(self.progress.get_recent_operations(10))
            },
            'feedback': self.feedback.get_feedback_stats(),
            'accessibility': self.accessibility.get_accessibility_settings()
        }


# Global user experience manager
ux_manager = UserExperienceManager()


# Convenience functions
def show_notification(level: NotificationLevel, title: str, message: str, **kwargs):
    """Show a notification."""
    return ux_manager.show_notification(level, title, message, **kwargs)


def start_progress(operation_name: str, total_steps: int = 0) -> str:
    """Start progress tracking."""
    return ux_manager.start_progress_operation(operation_name, total_steps)


def update_progress(operation_id: str, current_step: int, **kwargs):
    """Update progress."""
    ux_manager.update_progress(operation_id, current_step, **kwargs)


def complete_progress(operation_id: str, success: bool = True):
    """Complete progress tracking."""
    ux_manager.complete_progress_operation(operation_id, success)


def record_action(action: str, category: str = "general"):
    """Record user action."""
    ux_manager.record_user_action(action, category)
