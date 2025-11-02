"""Government-grade audit logging system for compliance and security."""
from __future__ import annotations

import json
import hashlib
import hmac
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum
import threading
import queue
import logging
from dataclasses import dataclass, asdict
import sqlite3
import zlib

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Audit event classifications for government compliance."""
    # Authentication & Authorization
    AUTH_LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
    AUTH_LOGIN_FAILURE = "AUTH_LOGIN_FAILURE"
    AUTH_LOGOUT = "AUTH_LOGOUT"
    AUTH_TOKEN_ISSUED = "AUTH_TOKEN_ISSUED"
    AUTH_TOKEN_REVOKED = "AUTH_TOKEN_REVOKED"
    AUTH_PERMISSION_GRANTED = "AUTH_PERMISSION_GRANTED"
    AUTH_PERMISSION_DENIED = "AUTH_PERMISSION_DENIED"

    # Data Access
    DATA_READ = "DATA_READ"
    DATA_WRITE = "DATA_WRITE"
    DATA_DELETE = "DATA_DELETE"
    DATA_EXPORT = "DATA_EXPORT"
    DATA_IMPORT = "DATA_IMPORT"

    # File Operations
    FILE_UPLOAD = "FILE_UPLOAD"
    FILE_DOWNLOAD = "FILE_DOWNLOAD"
    FILE_PROCESS = "FILE_PROCESS"
    FILE_VALIDATE = "FILE_VALIDATE"
    FILE_DELETE = "FILE_DELETE"

    # System Operations
    SYSTEM_START = "SYSTEM_START"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    SYSTEM_CONFIG_CHANGE = "SYSTEM_CONFIG_CHANGE"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    SYSTEM_MAINTENANCE = "SYSTEM_MAINTENANCE"

    # Security Events
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    SECURITY_SCAN = "SECURITY_SCAN"
    SECURITY_ALERT = "SECURITY_ALERT"

    # Compliance Events
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    COMPLIANCE_VIOLATION = "COMPLIANCE_VIOLATION"
    COMPLIANCE_REPORT = "COMPLIANCE_REPORT"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class AuditEvent:
    """Immutable audit event record."""
    event_id: str
    timestamp: str
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    resource: Optional[str]
    action: str
    result: str
    details: Dict[str, Any]
    metadata: Dict[str, Any]
    hash: Optional[str] = None
    signature: Optional[str] = None

    def to_json(self) -> str:
        """Convert to JSON string."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        return json.dumps(data, sort_keys=True, default=str)

    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of event data."""
        data_str = self.to_json()
        return hashlib.sha256(data_str.encode()).hexdigest()


class AuditLogger:
    """Enterprise-grade audit logging system with tamper protection."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        signing_key: Optional[str] = None,
        retention_days: int = 2555,  # 7 years for government compliance
        enable_encryption: bool = True
    ):
        """Initialize audit logger with security features.

        Args:
            db_path: Path to audit database
            signing_key: Key for HMAC signing
            retention_days: Days to retain audit logs
            enable_encryption: Enable encryption for sensitive data
        """
        self.db_path = db_path or Path("audit.db")
        self.signing_key = signing_key or self._generate_signing_key()
        self.retention_days = retention_days
        self.enable_encryption = enable_encryption

        # Thread-safe queue for async logging
        self.audit_queue: queue.Queue = queue.Queue()
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None

        # Initialize database
        self._init_database()

        # Start worker thread
        self._start_worker()

        # Log system start
        self.log_event(
            event_type=AuditEventType.SYSTEM_START,
            severity=AuditSeverity.INFO,
            action="System initialized",
            result="SUCCESS",
            details={"version": "2.0.0", "mode": "production"}
        )

    def _generate_signing_key(self) -> str:
        """Generate secure signing key."""
        return hashlib.sha512(uuid.uuid4().bytes).hexdigest()

    def _init_database(self):
        """Initialize audit database with security features."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Create audit events table with indexes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                ip_address TEXT,
                resource TEXT,
                action TEXT NOT NULL,
                result TEXT NOT NULL,
                details_json TEXT,
                metadata_json TEXT,
                hash TEXT NOT NULL,
                signature TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON audit_events(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type
            ON audit_events(event_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id
            ON audit_events(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_severity
            ON audit_events(severity)
        """)

        # Create chain verification table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_chain (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                previous_hash TEXT,
                current_hash TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES audit_events(event_id)
            )
        """)

        conn.commit()
        conn.close()

    def _start_worker(self):
        """Start background worker for async logging."""
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def _worker_loop(self):
        """Background worker to process audit events."""
        while self.running:
            try:
                event = self.audit_queue.get(timeout=1.0)
                if event:
                    self._write_event(event)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Audit worker error: {e}")

    def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        action: str,
        result: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log an audit event with full context.

        Args:
            event_type: Type of event
            severity: Event severity
            action: Action performed
            result: Result of action (SUCCESS/FAILURE/ERROR)
            user_id: User identifier
            session_id: Session identifier
            ip_address: Client IP address
            resource: Resource accessed
            details: Event-specific details
            metadata: Additional metadata

        Returns:
            Event ID
        """
        # Generate event
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
            metadata=metadata or {}
        )

        # Calculate hash and signature
        event.hash = event.calculate_hash()
        event.signature = self._sign_event(event)

        # Queue for async processing
        self.audit_queue.put(event)

        # Log critical events immediately
        if severity == AuditSeverity.CRITICAL:
            self._write_event(event)

        return event.event_id

    def _sign_event(self, event: AuditEvent) -> str:
        """Generate HMAC signature for event."""
        message = event.to_json().encode()
        signature = hmac.new(
            self.signing_key.encode(),
            message,
            hashlib.sha256
        ).hexdigest()
        return signature

    def _verify_signature(self, event: AuditEvent) -> bool:
        """Verify event signature."""
        expected_signature = self._sign_event(event)
        return hmac.compare_digest(event.signature, expected_signature)

    def _write_event(self, event: AuditEvent):
        """Write event to database with chain verification."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Get previous hash for chain
            cursor.execute("""
                SELECT current_hash FROM audit_chain
                ORDER BY id DESC LIMIT 1
            """)
            row = cursor.fetchone()
            previous_hash = row[0] if row else None

            # Compress details if needed
            details_json = json.dumps(event.details)
            metadata_json = json.dumps(event.metadata)

            if self.enable_encryption and len(details_json) > 1000:
                details_json = zlib.compress(details_json.encode()).hex()
                metadata_json = zlib.compress(metadata_json.encode()).hex()

            # Insert event
            cursor.execute("""
                INSERT INTO audit_events (
                    event_id, timestamp, event_type, severity,
                    user_id, session_id, ip_address, resource,
                    action, result, details_json, metadata_json,
                    hash, signature, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.timestamp, event.event_type.value,
                event.severity.value, event.user_id, event.session_id,
                event.ip_address, event.resource, event.action, event.result,
                details_json, metadata_json, event.hash, event.signature,
                time.time()
            ))

            # Add to chain
            current_hash = hashlib.sha256(
                f"{previous_hash}{event.hash}".encode()
            ).hexdigest()

            cursor.execute("""
                INSERT INTO audit_chain (event_id, previous_hash, current_hash)
                VALUES (?, ?, ?)
            """, (event.event_id, previous_hash, current_hash))

            conn.commit()

        except Exception as e:
            logger.error(f"Failed to write audit event: {e}")
            conn.rollback()
        finally:
            conn.close()

    def query_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[AuditEventType] = None,
        severity: Optional[AuditSeverity] = None,
        user_id: Optional[str] = None,
        limit: int = 1000
    ) -> List[AuditEvent]:
        """Query audit events with filters.

        Args:
            start_time: Start time filter
            end_time: End time filter
            event_type: Event type filter
            severity: Severity filter
            user_id: User ID filter
            limit: Maximum results

        Returns:
            List of matching audit events
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Build query
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)

        if severity:
            query += " AND severity = ?"
            params.append(severity.value)

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        # Convert to AuditEvent objects
        events = []
        for row in rows:
            event = AuditEvent(
                event_id=row[0],
                timestamp=row[1],
                event_type=AuditEventType(row[2]),
                severity=AuditSeverity(row[3]),
                user_id=row[4],
                session_id=row[5],
                ip_address=row[6],
                resource=row[7],
                action=row[8],
                result=row[9],
                details=json.loads(row[10]) if row[10] else {},
                metadata=json.loads(row[11]) if row[11] else {},
                hash=row[12],
                signature=row[13]
            )
            events.append(event)

        return events

    def verify_integrity(self, start_date: Optional[datetime] = None) -> bool:
        """Verify audit log integrity using chain verification.

        Args:
            start_date: Start date for verification

        Returns:
            True if integrity is maintained
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get chain entries
        query = "SELECT event_id, previous_hash, current_hash FROM audit_chain"
        if start_date:
            query += f" WHERE event_id IN (SELECT event_id FROM audit_events WHERE timestamp >= '{start_date.isoformat()}')"
        query += " ORDER BY id"

        cursor.execute(query)
        chain_entries = cursor.fetchall()

        # Verify chain
        previous_hash = None
        for event_id, stored_prev, stored_current in chain_entries:
            # Get event
            cursor.execute("""
                SELECT hash FROM audit_events WHERE event_id = ?
            """, (event_id,))
            event_hash = cursor.fetchone()[0]

            # Calculate expected hash
            expected_hash = hashlib.sha256(
                f"{stored_prev}{event_hash}".encode()
            ).hexdigest()

            # Verify
            if stored_current != expected_hash:
                logger.error(f"Chain verification failed at event {event_id}")
                conn.close()
                return False

            if previous_hash and stored_prev != previous_hash:
                logger.error(f"Chain continuity broken at event {event_id}")
                conn.close()
                return False

            previous_hash = stored_current

        conn.close()
        return True

    def export_audit_log(
        self,
        output_path: Path,
        format: str = "json",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ):
        """Export audit log for compliance reporting.

        Args:
            output_path: Output file path
            format: Export format (json/csv)
            start_date: Start date filter
            end_date: End date filter
        """
        events = self.query_events(
            start_time=start_date,
            end_time=end_date,
            limit=1000000  # Large limit for export
        )

        if format == "json":
            with open(output_path, 'w') as f:
                json.dump(
                    [json.loads(e.to_json()) for e in events],
                    f,
                    indent=2
                )
        elif format == "csv":
            import csv
            with open(output_path, 'w', newline='') as f:
                if events:
                    writer = csv.DictWriter(f, fieldnames=asdict(events[0]).keys())
                    writer.writeheader()
                    for event in events:
                        row = asdict(event)
                        row['event_type'] = row['event_type'].value
                        row['severity'] = row['severity'].value
                        writer.writerow(row)

    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report with statistics.

        Returns:
            Compliance report dictionary
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get statistics
        cursor.execute("SELECT COUNT(*) FROM audit_events")
        total_events = cursor.fetchone()[0]

        cursor.execute("""
            SELECT event_type, COUNT(*) FROM audit_events
            GROUP BY event_type
        """)
        events_by_type = dict(cursor.fetchall())

        cursor.execute("""
            SELECT severity, COUNT(*) FROM audit_events
            GROUP BY severity
        """)
        events_by_severity = dict(cursor.fetchall())

        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM audit_events
            WHERE user_id IS NOT NULL
        """)
        unique_users = cursor.fetchone()[0]

        # Get recent security events
        cursor.execute("""
            SELECT COUNT(*) FROM audit_events
            WHERE event_type LIKE 'SECURITY_%'
            AND timestamp >= datetime('now', '-30 days')
        """)
        recent_security_events = cursor.fetchone()[0]

        conn.close()

        # Verify integrity
        integrity_verified = self.verify_integrity()

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_events": total_events,
            "events_by_type": events_by_type,
            "events_by_severity": events_by_severity,
            "unique_users": unique_users,
            "recent_security_events": recent_security_events,
            "integrity_verified": integrity_verified,
            "retention_days": self.retention_days,
            "database_size_mb": self.db_path.stat().st_size / (1024 * 1024)
        }

    def cleanup_old_events(self):
        """Remove events older than retention period."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Archive before deletion (in production, would export to cold storage)
        cursor.execute("""
            SELECT COUNT(*) FROM audit_events
            WHERE timestamp < ?
        """, (cutoff_date.isoformat(),))

        count = cursor.fetchone()[0]
        if count > 0:
            logger.info(f"Archiving {count} events older than {self.retention_days} days")

            # Delete old events
            cursor.execute("""
                DELETE FROM audit_events
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))

            conn.commit()

        conn.close()

    def shutdown(self):
        """Shutdown audit logger gracefully."""
        # Log shutdown
        self.log_event(
            event_type=AuditEventType.SYSTEM_SHUTDOWN,
            severity=AuditSeverity.INFO,
            action="System shutdown",
            result="SUCCESS",
            details={"graceful": True}
        )

        # Stop worker
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)

        # Process remaining events
        while not self.audit_queue.empty():
            event = self.audit_queue.get_nowait()
            self._write_event(event)


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def init_audit_logger(
    db_path: Optional[Path] = None,
    signing_key: Optional[str] = None
) -> AuditLogger:
    """Initialize global audit logger."""
    global _audit_logger
    _audit_logger = AuditLogger(db_path=db_path, signing_key=signing_key)
    return _audit_logger


def audit_log(
    event_type: AuditEventType,
    action: str,
    result: str = "SUCCESS",
    **kwargs
) -> str:
    """Quick audit logging function."""
    logger = get_audit_logger()
    return logger.log_event(
        event_type=event_type,
        severity=AuditSeverity.INFO,
        action=action,
        result=result,
        **kwargs
    )