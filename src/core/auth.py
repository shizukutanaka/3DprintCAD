"""Authentication and authorization module for 3D Print CAD Assistant."""
from __future__ import annotations

import os
import jwt
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps
from flask import request, jsonify, current_app, g
import logging

from .security import constant_time_compare, generate_secure_token, validate_api_key_format

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Authentication/authorization error."""
    pass


class User:
    """User model for authentication."""

    def __init__(self, user_id: str, username: str, roles: List[str] = None,
                 is_active: bool = True, metadata: Dict[str, Any] = None):
        self.user_id = user_id
        self.username = username
        self.roles = roles or ['user']
        self.is_active = is_active
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.last_active = datetime.utcnow()

    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission based on roles."""
        role_permissions = {
            'admin': ['read', 'write', 'delete', 'manage_users', 'view_analytics'],
            'editor': ['read', 'write', 'delete'],
            'user': ['read', 'write'],
            'viewer': ['read']
        }

        for role in self.roles:
            if permission in role_permissions.get(role, []):
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for serialization."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'roles': self.roles,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_active': self.last_active.isoformat()
        }


class AuthManager:
    """Manages authentication and authorization."""

    def __init__(self, secret_key: str, token_expiry_hours: int = 24):
        self.secret_key = secret_key
        self.token_expiry_hours = token_expiry_hours
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, str] = {}  # api_key -> user_id
        self.revoked_tokens: set = set()

        # Load default admin user from environment
        self._load_default_users()

    def _load_default_users(self):
        """Load default users from environment variables."""
        admin_username = os.environ.get('DEFAULT_ADMIN_USER', 'admin')
        admin_password = os.environ.get('DEFAULT_ADMIN_PASSWORD')

        if admin_password:
            admin_user = User(
                user_id='admin-001',
                username=admin_username,
                roles=['admin'],
                metadata={'source': 'environment'}
            )
            self.users[admin_user.user_id] = admin_user
            logger.info(f"Default admin user '{admin_username}' loaded")

    def create_user(self, username: str, roles: List[str] = None,
                   metadata: Dict[str, Any] = None) -> User:
        """Create a new user."""
        if not username or len(username) < 3:
            raise AuthError("Username must be at least 3 characters")

        # Check if username already exists
        for user in self.users.values():
            if user.username == username:
                raise AuthError(f"Username '{username}' already exists")

        user_id = f"user-{int(time.time())}-{len(self.users)}"
        user = User(
            user_id=user_id,
            username=username,
            roles=roles or ['user'],
            metadata=metadata or {}
        )

        self.users[user_id] = user
        logger.info(f"Created user: {username} with roles: {user.roles}")
        return user

    def authenticate_password(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        # This is a simplified implementation
        # In production, use proper password hashing with bcrypt/argon2

        # Check against default admin
        admin_password = os.environ.get('DEFAULT_ADMIN_PASSWORD')
        if (username == os.environ.get('DEFAULT_ADMIN_USER', 'admin') and
            admin_password and constant_time_compare(password, admin_password)):

            for user in self.users.values():
                if user.username == username and user.has_role('admin'):
                    user.last_active = datetime.utcnow()
                    return user

        # In production, implement proper password verification
        logger.warning(f"Authentication failed for user: {username}")
        return None

    def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """Authenticate using API key."""
        if not validate_api_key_format(api_key):
            return None

        user_id = self.api_keys.get(api_key)
        if user_id and user_id in self.users:
            user = self.users[user_id]
            if user.is_active:
                user.last_active = datetime.utcnow()
                return user

        return None

    def generate_api_key(self, user_id: str) -> str:
        """Generate API key for user."""
        if user_id not in self.users:
            raise AuthError("User not found")

        api_key = generate_secure_token(32)
        self.api_keys[api_key] = user_id

        logger.info(f"Generated API key for user: {user_id}")
        return api_key

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        if api_key in self.api_keys:
            del self.api_keys[api_key]
            logger.info(f"Revoked API key: {api_key[:8]}...")
            return True
        return False

    def generate_jwt_token(self, user: User) -> str:
        """Generate JWT token for user."""
        payload = {
            'user_id': user.user_id,
            'username': user.username,
            'roles': user.roles,
            'exp': datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            'iat': datetime.utcnow(),
            'jti': generate_secure_token(16)  # JWT ID for tracking
        }

        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def verify_jwt_token(self, token: str) -> Optional[User]:
        """Verify JWT token and return user."""
        try:
            if token in self.revoked_tokens:
                return None

            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')

            if user_id in self.users:
                user = self.users[user_id]
                if user.is_active:
                    user.last_active = datetime.utcnow()
                    return user

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")

        return None

    def revoke_jwt_token(self, token: str) -> bool:
        """Revoke a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            jti = payload.get('jti')
            if jti:
                self.revoked_tokens.add(jti)
                return True
        except jwt.InvalidTokenError:
            pass

        return False

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)

    def update_user_roles(self, user_id: str, roles: List[str]) -> bool:
        """Update user roles."""
        if user_id in self.users:
            self.users[user_id].roles = roles
            logger.info(f"Updated roles for user {user_id}: {roles}")
            return True
        return False

    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account."""
        if user_id in self.users:
            self.users[user_id].is_active = False
            logger.info(f"Deactivated user: {user_id}")
            return True
        return False


# Global auth manager instance
auth_manager: Optional[AuthManager] = None


def init_auth(secret_key: str, token_expiry_hours: int = 24) -> AuthManager:
    """Initialize authentication manager."""
    global auth_manager
    auth_manager = AuthManager(secret_key, token_expiry_hours)
    return auth_manager


def get_auth_manager() -> AuthManager:
    """Get the global auth manager instance."""
    if auth_manager is None:
        raise AuthError("Authentication not initialized")
    return auth_manager


def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth = get_auth_manager()
            user = None

            # Check for JWT token in Authorization header
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]  # Remove 'Bearer ' prefix
                user = auth.verify_jwt_token(token)

            # Check for API key in header
            elif request.headers.get('X-API-Key'):
                api_key = request.headers.get('X-API-Key')
                user = auth.authenticate_api_key(api_key)

            if not user:
                return jsonify({'error': 'Authentication required'}), 401

            # Store user in Flask's g object for use in view functions
            g.current_user = user
            return f(*args, **kwargs)

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({'error': 'Authentication failed'}), 401

    return decorated_function


def require_role(required_role: str):
    """Decorator to require specific role."""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user = g.current_user
            if not user.has_role(required_role):
                return jsonify({'error': f'Role {required_role} required'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_permission(required_permission: str):
    """Decorator to require specific permission."""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user = g.current_user
            if not user.has_permission(required_permission):
                return jsonify({'error': f'Permission {required_permission} required'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator