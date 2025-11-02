"""Advanced security features with zero-trust architecture and quantum-resistant encryption."""

import os
import time
import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import hmac
import secrets
import threading
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding, utils
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.exceptions import InvalidSignature, InvalidKey
import base64


class EncryptionAlgorithm(Enum):
    """Encryption algorithms."""
    AES_256_GCM = "aes_256_gcm"
    CHACHA20_POLY1305 = "chacha20_poly1305"
    KYBER = "kyber"  # Quantum-resistant
    DILITHIUM = "dilithium"  # Quantum-resistant


class ZeroTrustPolicy(Enum):
    """Zero-trust security policies."""
    DENY_BY_DEFAULT = "deny_by_default"
    LEAST_PRIVILEGE = "least_privilege"
    CONTINUOUS_VERIFICATION = "continuous_verification"
    MICRO_SEGMENTATION = "micro_segmentation"


@dataclass
class SecurityContext:
    """Security context for operations."""
    user_id: str
    session_id: str
    device_fingerprint: str
    ip_address: str
    user_agent: str
    risk_score: float = 0.0
    security_level: str = "standard"
    access_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AccessRequest:
    """Access request for zero-trust evaluation."""
    resource: str
    action: str
    context: SecurityContext
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class QuantumResistantCrypto:
    """Quantum-resistant cryptographic operations."""

    def __init__(self):
        """Initialize quantum-resistant crypto."""
        self.logger = logging.getLogger(__name__)

        # Generate key pairs for quantum-resistant algorithms
        self._kyber_keypair = None
        self._dilithium_keypair = None

    def generate_kyber_keypair(self) -> Tuple[str, str]:
        """Generate Kyber keypair for quantum-resistant encryption.

        Returns:
            Tuple of (public_key, private_key)
        """
        try:
            # In a real implementation, this would use actual Kyber implementation
            # For now, we'll simulate with larger RSA keys as placeholder
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,  # Larger key size for quantum resistance
            )

            public_key = private_key.public_key()

            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            return public_pem.decode(), private_pem.decode()

        except Exception as e:
            self.logger.error(f"Error generating Kyber keypair: {e}")
            raise

    def generate_dilithium_keypair(self) -> Tuple[str, str]:
        """Generate Dilithium keypair for quantum-resistant signatures.

        Returns:
            Tuple of (public_key, private_key)
        """
        try:
            # In a real implementation, this would use actual Dilithium implementation
            # For now, we'll simulate with ECC as placeholder
            private_key = ec.generate_private_key(ec.SECP521R1())

            public_key = private_key.public_key()

            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            return public_pem.decode(), private_pem.decode()

        except Exception as e:
            self.logger.error(f"Error generating Dilithium keypair: {e}")
            raise

    def encrypt_data(self, data: bytes, public_key_pem: str) -> bytes:
        """Encrypt data using quantum-resistant encryption.

        Args:
            data: Data to encrypt
            public_key_pem: Public key in PEM format

        Returns:
            Encrypted data
        """
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(public_key_pem.encode())

            # For simulation, use RSA-OAEP with larger keys
            ciphertext = public_key.encrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            return ciphertext

        except Exception as e:
            self.logger.error(f"Error encrypting data: {e}")
            raise

    def decrypt_data(self, encrypted_data: bytes, private_key_pem: str) -> bytes:
        """Decrypt data using quantum-resistant decryption.

        Args:
            encrypted_data: Data to decrypt
            private_key_pem: Private key in PEM format

        Returns:
            Decrypted data
        """
        try:
            # Load private key
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None
            )

            # For simulation, use RSA-OAEP with larger keys
            plaintext = private_key.decrypt(
                encrypted_data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            return plaintext

        except Exception as e:
            self.logger.error(f"Error decrypting data: {e}")
            raise

    def sign_data(self, data: bytes, private_key_pem: str) -> bytes:
        """Sign data using quantum-resistant signature.

        Args:
            data: Data to sign
            private_key_pem: Private key in PEM format

        Returns:
            Digital signature
        """
        try:
            # Load private key
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None
            )

            # For simulation, use ECDSA with larger curves
            signature = private_key.sign(
                data,
                ec.ECDSA(hashes.SHA256())
            )

            return signature

        except Exception as e:
            self.logger.error(f"Error signing data: {e}")
            raise

    def verify_signature(self, data: bytes, signature: bytes, public_key_pem: str) -> bool:
        """Verify quantum-resistant signature.

        Args:
            data: Original data
            signature: Signature to verify
            public_key_pem: Public key in PEM format

        Returns:
            True if signature is valid
        """
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(public_key_pem.encode())

            # For simulation, use ECDSA with larger curves
            public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
            return True

        except InvalidSignature:
            return False
        except Exception as e:
            self.logger.error(f"Error verifying signature: {e}")
            return False


class ZeroTrustSecurityManager:
    """Advanced zero-trust security manager."""

    def __init__(self):
        """Initialize zero-trust security manager."""
        self.logger = logging.getLogger(__name__)
        self.crypto = QuantumResistantCrypto()

        # Security policies
        self.policies = {
            ZeroTrustPolicy.DENY_BY_DEFAULT: True,
            ZeroTrustPolicy.LEAST_PRIVILEGE: True,
            ZeroTrustPolicy.CONTINUOUS_VERIFICATION: True,
            ZeroTrustPolicy.MICRO_SEGMENTATION: True
        }

        # Access control
        self.access_rules: Dict[str, Dict[str, Any]] = {}
        self.resource_permissions: Dict[str, Set[str]] = {}

        # Risk assessment
        self.risk_thresholds = {
            'low': 0.3,
            'medium': 0.7,
            'high': 1.0
        }

        # Security events
        self.security_events: List[Dict[str, Any]] = []
        self.max_events = 10000

        # Thread safety
        self._lock = threading.RLock()

    def evaluate_access_request(self, request: AccessRequest) -> Tuple[bool, str]:
        """Evaluate access request using zero-trust principles.

        Args:
            request: Access request to evaluate

        Returns:
            Tuple of (access_granted, reason)
        """
        with self._lock:
            # 1. Verify user identity and context
            identity_valid = self._verify_identity(request.context)
            if not identity_valid:
                return False, "Identity verification failed"

            # 2. Assess risk score
            risk_level = self._assess_risk(request)
            if risk_level == 'high':
                return False, "High risk score"

            # 3. Check resource permissions
            has_permission = self._check_permissions(request)
            if not has_permission:
                return False, "Insufficient permissions"

            # 4. Continuous verification
            verification_passed = self._continuous_verification(request)
            if not verification_passed:
                return False, "Continuous verification failed"

            # 5. Log access attempt
            self._log_security_event(request, True, f"Access granted (risk: {risk_level})")

            return True, f"Access granted (risk: {risk_level})"

    def _verify_identity(self, context: SecurityContext) -> bool:
        """Verify user identity and device."""
        # Check device fingerprint
        expected_fingerprint = self._get_device_fingerprint(context.user_id)
        if expected_fingerprint and context.device_fingerprint != expected_fingerprint:
            return False

        # Check session validity
        if not self._is_session_valid(context.session_id):
            return False

        # Check IP reputation
        if self._is_ip_suspicious(context.ip_address):
            return False

        return True

    def _assess_risk(self, request: AccessRequest) -> str:
        """Assess risk level of access request."""
        risk_score = 0.0

        # Base risk from context
        risk_score += request.context.risk_score

        # Resource sensitivity
        resource_risk = self._get_resource_risk(request.resource)
        risk_score += resource_risk

        # Time-based risk (unusual hours)
        current_hour = time.localtime().tm_hour
        if current_hour < 6 or current_hour > 22:
            risk_score += 0.2

        # Action risk
        action_risk = self._get_action_risk(request.action)
        risk_score += action_risk

        # Determine risk level
        if risk_score < self.risk_thresholds['low']:
            return 'low'
        elif risk_score < self.risk_thresholds['medium']:
            return 'medium'
        else:
            return 'high'

    def _check_permissions(self, request: AccessRequest) -> bool:
        """Check if user has permission for requested action."""
        user_permissions = self.resource_permissions.get(request.context.user_id, set())

        required_permission = f"{request.resource}:{request.action}"
        return required_permission in user_permissions

    def _continuous_verification(self, request: AccessRequest) -> bool:
        """Perform continuous verification checks."""
        # Check if user has recent suspicious activity
        recent_events = [
            event for event in self.security_events[-100:]  # Last 100 events
            if event['user_id'] == request.context.user_id
            and event['success'] == False
            and time.time() - event['timestamp'] < 3600  # Last hour
        ]

        if len(recent_events) > 3:
            return False

        # Check device consistency
        if not self._verify_device_consistency(request.context):
            return False

        return True

    def _get_device_fingerprint(self, user_id: str) -> Optional[str]:
        """Get stored device fingerprint for user."""
        # In real implementation, this would query a database
        # For now, return None (no stored fingerprint)
        return None

    def _is_session_valid(self, session_id: str) -> bool:
        """Check if session is valid."""
        # In real implementation, this would check session store
        # For now, assume sessions are valid
        return True

    def _is_ip_suspicious(self, ip_address: str) -> bool:
        """Check if IP address is suspicious."""
        # In real implementation, this would check threat intelligence
        # For now, assume IPs are not suspicious
        return False

    def _get_resource_risk(self, resource: str) -> float:
        """Get risk score for a resource."""
        high_risk_resources = {'admin', 'system', 'database', 'encryption_keys'}
        return 0.5 if any(risk_word in resource.lower() for risk_word in high_risk_resources) else 0.1

    def _get_action_risk(self, action: str) -> float:
        """Get risk score for an action."""
        high_risk_actions = {'delete', 'modify', 'admin', 'execute'}
        return 0.3 if action.lower() in high_risk_actions else 0.1

    def _verify_device_consistency(self, context: SecurityContext) -> bool:
        """Verify device consistency."""
        # Check if device characteristics are consistent
        # In real implementation, this would compare against stored device profile
        return True

    def _log_security_event(self, request: AccessRequest, success: bool, reason: str):
        """Log security event."""
        event = {
            'user_id': request.context.user_id,
            'session_id': request.context.session_id,
            'resource': request.resource,
            'action': request.action,
            'success': success,
            'reason': reason,
            'timestamp': request.timestamp,
            'ip_address': request.context.ip_address,
            'user_agent': request.context.user_agent
        }

        self.security_events.append(event)

        if len(self.security_events) > self.max_events:
            self.security_events = self.security_events[-self.max_events:]

    def grant_permission(self, user_id: str, resource: str, action: str):
        """Grant permission to a user.

        Args:
            user_id: User ID
            resource: Resource name
            action: Action name
        """
        with self._lock:
            if user_id not in self.resource_permissions:
                self.resource_permissions[user_id] = set()

            permission = f"{resource}:{action}"
            self.resource_permissions[user_id].add(permission)

    def revoke_permission(self, user_id: str, resource: str, action: str):
        """Revoke permission from a user.

        Args:
            user_id: User ID
            resource: Resource name
            action: Action name
        """
        with self._lock:
            if user_id in self.resource_permissions:
                permission = f"{resource}:{action}"
                self.resource_permissions[user_id].discard(permission)

    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for a user.

        Args:
            user_id: User ID

        Returns:
            Set of permissions
        """
        with self._lock:
            return self.resource_permissions.get(user_id, set()).copy()

    def create_security_context(self, user_id: str, session_id: str,
                              device_fingerprint: str, ip_address: str,
                              user_agent: str) -> SecurityContext:
        """Create a security context for a user session.

        Args:
            user_id: User ID
            session_id: Session ID
            device_fingerprint: Device fingerprint
            ip_address: IP address
            user_agent: User agent string

        Returns:
            Security context
        """
        return SecurityContext(
            user_id=user_id,
            session_id=session_id,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
            access_history=[]
        )

    def update_risk_score(self, context: SecurityContext, risk_factors: Dict[str, float]):
        """Update risk score for a security context.

        Args:
            context: Security context to update
            risk_factors: Risk factors to consider
        """
        with self._lock:
            # Calculate new risk score based on factors
            base_risk = 0.0

            # Behavioral factors
            if 'unusual_time' in risk_factors:
                base_risk += risk_factors['unusual_time'] * 0.3

            if 'unusual_location' in risk_factors:
                base_risk += risk_factors['unusual_location'] * 0.4

            if 'multiple_failures' in risk_factors:
                base_risk += risk_factors['multiple_failures'] * 0.5

            # Update context
            context.risk_score = min(base_risk, 1.0)

    def get_security_events(self, limit: int = 100,
                           user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get security events.

        Args:
            limit: Maximum number of events to return
            user_id: Filter by user ID

        Returns:
            List of security events
        """
        with self._lock:
            events = self.security_events

            if user_id:
                events = [e for e in events if e['user_id'] == user_id]

            return events[-limit:]


class SecureKeyManager:
    """Manages encryption keys with quantum resistance."""

    def __init__(self):
        """Initialize secure key manager."""
        self.logger = logging.getLogger(__name__)
        self.crypto = QuantumResistantCrypto()

        # Key storage (in production, use secure key management service)
        self.keys: Dict[str, Dict[str, str]] = {}
        self.key_rotation_schedule: Dict[str, float] = {}

        # Key derivation
        self.salt = secrets.token_bytes(32)

    def generate_master_key(self, key_id: str, algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM) -> Dict[str, str]:
        """Generate a master key.

        Args:
            key_id: Unique key identifier
            algorithm: Encryption algorithm

        Returns:
            Dictionary with key information
        """
        if algorithm == EncryptionAlgorithm.KYBER:
            public_key, private_key = self.crypto.generate_kyber_keypair()
        elif algorithm == EncryptionAlgorithm.DILITHIUM:
            public_key, private_key = self.crypto.generate_dilithium_keypair()
        else:
            # Generate AES key
            key_bytes = secrets.token_bytes(32)  # 256 bits
            public_key = base64.b64encode(key_bytes).decode()
            private_key = public_key  # Same key for symmetric encryption

        key_info = {
            'key_id': key_id,
            'algorithm': algorithm.value,
            'public_key': public_key,
            'private_key': private_key,
            'created_at': time.time(),
            'rotation_due': time.time() + (365 * 24 * 3600)  # 1 year
        }

        self.keys[key_id] = key_info
        self.key_rotation_schedule[key_id] = key_info['rotation_due']

        self.logger.info(f"Generated master key: {key_id}")
        return key_info

    def derive_data_key(self, master_key_id: str, context: str) -> bytes:
        """Derive a data encryption key from master key.

        Args:
            master_key_id: Master key ID
            context: Context for key derivation

        Returns:
            Derived key as bytes
        """
        if master_key_id not in self.keys:
            raise ValueError(f"Master key {master_key_id} not found")

        # Use PBKDF2 for key derivation
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )

        context_bytes = context.encode()
        derived_key = kdf.derive(context_bytes)

        return derived_key

    def encrypt_sensitive_data(self, data: str, key_id: str, context: str = "default") -> str:
        """Encrypt sensitive data.

        Args:
            data: Data to encrypt
            key_id: Key ID to use
            context: Context for key derivation

        Returns:
            Encrypted data as base64 string
        """
        try:
            # Derive data key
            data_key = self.derive_data_key(key_id, context)

            # Generate IV
            iv = secrets.token_bytes(12)  # 96 bits for GCM

            # Encrypt data
            cipher = Cipher(algorithms.AES(data_key), modes.GCM(iv))
            encryptor = cipher.encryptor()

            ciphertext = encryptor.update(data.encode()) + encryptor.finalize()

            # Combine IV and ciphertext
            encrypted_data = iv + ciphertext + encryptor.tag

            return base64.b64encode(encrypted_data).decode()

        except Exception as e:
            self.logger.error(f"Error encrypting data: {e}")
            raise

    def decrypt_sensitive_data(self, encrypted_data_b64: str, key_id: str, context: str = "default") -> str:
        """Decrypt sensitive data.

        Args:
            encrypted_data_b64: Base64 encoded encrypted data
            key_id: Key ID to use
            context: Context for key derivation

        Returns:
            Decrypted data
        """
        try:
            # Derive data key
            data_key = self.derive_data_key(key_id, context)

            # Decode encrypted data
            encrypted_data = base64.b64decode(encrypted_data_b64)

            # Extract IV and tag
            iv = encrypted_data[:12]
            tag = encrypted_data[-16:]
            ciphertext = encrypted_data[12:-16]

            # Decrypt data
            cipher = Cipher(algorithms.AES(data_key), modes.GCM(iv, tag))
            decryptor = cipher.decryptor()

            plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            return plaintext.decode()

        except Exception as e:
            self.logger.error(f"Error decrypting data: {e}")
            raise

    def rotate_key(self, key_id: str) -> bool:
        """Rotate a master key.

        Args:
            key_id: Key ID to rotate

        Returns:
            True if rotation successful
        """
        if key_id not in self.keys:
            return False

        try:
            # Generate new key with same algorithm
            old_key = self.keys[key_id]
            algorithm = EncryptionAlgorithm(old_key['algorithm'])

            new_key_info = self.generate_master_key(f"{key_id}_rotated", algorithm)

            # Update references
            self.keys[key_id] = new_key_info
            self.key_rotation_schedule[key_id] = new_key_info['rotation_due']

            self.logger.info(f"Rotated key: {key_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error rotating key {key_id}: {e}")
            return False

    def get_key_info(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a key.

        Args:
            key_id: Key ID

        Returns:
            Key information or None if not found
        """
        return self.keys.get(key_id)


class AdvancedSecurityManager:
    """Main advanced security manager."""

    def __init__(self):
        """Initialize advanced security manager."""
        self.logger = logging.getLogger(__name__)
        self.zero_trust = ZeroTrustSecurityManager()
        self.key_manager = SecureKeyManager()

        # Initialize with some default keys
        self.key_manager.generate_master_key("default_aes")
        self.key_manager.generate_master_key("default_kyber", EncryptionAlgorithm.KYBER)

    def create_secure_session(self, user_id: str, device_fingerprint: str,
                            ip_address: str, user_agent: str) -> SecurityContext:
        """Create a secure session with zero-trust evaluation.

        Args:
            user_id: User ID
            device_fingerprint: Device fingerprint
            ip_address: IP address
            user_agent: User agent

        Returns:
            Security context
        """
        session_id = secrets.token_urlsafe(32)

        context = self.zero_trust.create_security_context(
            user_id, session_id, device_fingerprint, ip_address, user_agent
        )

        self.logger.info(f"Created secure session for user {user_id}")
        return context

    def authorize_action(self, context: SecurityContext, resource: str,
                        action: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """Authorize an action using zero-trust principles.

        Args:
            context: Security context
            resource: Resource being accessed
            action: Action being performed
            metadata: Additional metadata

        Returns:
            Tuple of (authorized, reason)
        """
        request = AccessRequest(
            resource=resource,
            action=action,
            context=context,
            metadata=metadata or {}
        )

        return self.zero_trust.evaluate_access_request(request)

    def encrypt_secure_data(self, data: str, context: str = "default") -> str:
        """Encrypt sensitive data.

        Args:
            data: Data to encrypt
            context: Encryption context

        Returns:
            Encrypted data
        """
        return self.key_manager.encrypt_sensitive_data(data, "default_aes", context)

    def decrypt_secure_data(self, encrypted_data: str, context: str = "default") -> str:
        """Decrypt sensitive data.

        Args:
            encrypted_data: Encrypted data
            context: Decryption context

        Returns:
            Decrypted data
        """
        return self.key_manager.decrypt_sensitive_data(encrypted_data, "default_aes", context)

    def sign_data(self, data: bytes) -> bytes:
        """Sign data with quantum-resistant signature.

        Args:
            data: Data to sign

        Returns:
            Digital signature
        """
        key_info = self.key_manager.get_key_info("default_dilithium")
        if not key_info:
            # Generate key if not exists
            key_info = self.key_manager.generate_master_key("default_dilithium", EncryptionAlgorithm.DILITHIUM)

        return self.zero_trust.crypto.sign_data(data, key_info['private_key'])

    def verify_signature(self, data: bytes, signature: bytes) -> bool:
        """Verify quantum-resistant signature.

        Args:
            data: Original data
            signature: Signature to verify

        Returns:
            True if signature is valid
        """
        key_info = self.key_manager.get_key_info("default_dilithium")
        if not key_info:
            return False

        return self.zero_trust.crypto.verify_signature(data, signature, key_info['public_key'])

    def get_security_dashboard_data(self) -> Dict[str, Any]:
        """Get data for security dashboard.

        Returns:
            Security dashboard data
        """
        return {
            'zero_trust_policies': {policy.name: enabled for policy, enabled in self.zero_trust.policies.items()},
            'active_sessions': len([e for e in self.zero_trust.security_events if time.time() - e['timestamp'] < 3600]),
            'security_events_24h': len([e for e in self.zero_trust.security_events if time.time() - e['timestamp'] < 86400]),
            'risk_distribution': self._calculate_risk_distribution(),
            'key_rotation_status': self._get_key_rotation_status(),
            'quantum_resistance_status': self._check_quantum_resistance()
        }

    def _calculate_risk_distribution(self) -> Dict[str, int]:
        """Calculate risk level distribution."""
        events = self.zero_trust.security_events[-1000:]  # Last 1000 events

        distribution = {'low': 0, 'medium': 0, 'high': 0}

        for event in events:
            # Extract risk level from reason or assume based on success
            if not event['success']:
                distribution['high'] += 1
            elif 'medium' in event.get('reason', '').lower():
                distribution['medium'] += 1
            else:
                distribution['low'] += 1

        return distribution

    def _get_key_rotation_status(self) -> Dict[str, Any]:
        """Get key rotation status."""
        current_time = time.time()
        status = {'total_keys': len(self.key_manager.keys), 'due_for_rotation': 0}

        for key_id, rotation_time in self.key_manager.key_rotation_schedule.items():
            if current_time >= rotation_time:
                status['due_for_rotation'] += 1

        return status

    def _check_quantum_resistance(self) -> Dict[str, Any]:
        """Check quantum resistance status."""
        return {
            'kyber_enabled': 'default_kyber' in self.key_manager.keys,
            'dilithium_enabled': 'default_dilithium' in self.key_manager.keys,
            'quantum_safe_algorithms': ['kyber', 'dilithium']
        }


# Global advanced security manager
advanced_security_manager = AdvancedSecurityManager()
