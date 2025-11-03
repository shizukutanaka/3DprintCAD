"""
Enterprise Compliance Manager for 3D Print CAD Assistant
Provides comprehensive compliance management for government and enterprise deployments
Supports SOC 2, ISO 27001, NIST, GDPR, and other standards
"""

import asyncio
import json
import hashlib
import os
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from pathlib import Path
import sqlite3
from cryptography.fernet import Fernet
import uuid

logger = logging.getLogger(__name__)

class ComplianceStandard(Enum):
    """Supported compliance standards with comprehensive coverage"""
    SOC2_TYPE2 = "SOC 2 Type II"
    ISO27001 = "ISO 27001"
    NIST_CSF = "NIST Cybersecurity Framework"
    NIST_SP800_53 = "NIST Special Publication 800-53"
    NIST_SP800_171 = "NIST Special Publication 800-171"
    GDPR = "General Data Protection Regulation"
    CCPA = "California Consumer Privacy Act"
    HIPAA = "Health Insurance Portability and Accountability Act"
    FedRAMP = "Federal Risk and Authorization Management Program"
    FISMA = "Federal Information Security Management Act"
    PCI_DSS = "Payment Card Industry Data Security Standard"
    SOX = "Sarbanes-Oxley Act"
    GLBA = "Gramm-Leach-Bliley Act"
    FERPA = "Family Educational Rights and Privacy Act"
    COPPA = "Children's Online Privacy Protection Act"
    HITRUST = "HITRUST Common Security Framework"
    CSA_STAR = "Cloud Security Alliance Security, Trust & Assurance Registry"
    ISO22301 = "ISO 22301 Business Continuity Management"
    ISO27018 = "ISO 27018 Cloud Privacy Protection"
    ISO27701 = "ISO 27701 Privacy Information Management"

@dataclass
class ComplianceRequirement:
    """Individual compliance requirement"""
    id: str
    standard: ComplianceStandard
    category: str
    description: str
    implementation_guide: str
    priority: int  # 1-5, 1 being highest
    status: str  # implemented, partial, not_implemented
    evidence_required: List[str]
    last_assessed: Optional[datetime] = None
    next_assessment: Optional[datetime] = None

@dataclass
class ComplianceEvidence:
    """Evidence for compliance requirement"""
    requirement_id: str
    evidence_type: str  # document, configuration, audit_log, screenshot
    evidence_data: str
    timestamp: datetime
    assessor: str
    validity_period: timedelta

@dataclass
class ComplianceAssessment:
    """Compliance assessment result"""
    assessment_id: str
    standard: ComplianceStandard
    timestamp: datetime
    assessor: str
    overall_score: float  # 0-100
    requirements_met: int
    total_requirements: int
    findings: List[str]
    recommendations: List[str]
    next_assessment_due: datetime

class ComplianceManager:
    """Enterprise compliance management system"""

    def __init__(self, data_dir: str = "compliance_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Initialize encryption for sensitive data
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)

        # Initialize database
        self.db_path = self.data_dir / "compliance.db"
        self._init_database()

        # Load compliance requirements
        self.requirements = self._load_compliance_requirements()

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for sensitive data.

        Security: Keys are loaded from PRINTCAD_ENCRYPTION_KEY environment variable
        in production. File-based keys are used only in development.
        """
        # First, check environment variable (production/hardened deployments)
        env_key = os.environ.get('PRINTCAD_ENCRYPTION_KEY')
        if env_key:
            try:
                # Validate it's a valid Fernet key
                key = env_key.encode() if isinstance(env_key, str) else env_key
                Fernet(key)  # Verify key validity
                logger.info("Using encryption key from PRINTCAD_ENCRYPTION_KEY environment variable")
                return key
            except Exception as exc:
                logger.error("Invalid encryption key in PRINTCAD_ENCRYPTION_KEY: %s", exc)
                raise ValueError("Invalid PRINTCAD_ENCRYPTION_KEY environment variable") from exc

        # Fallback to file-based key for development (with warnings)
        key_file = self.data_dir / "compliance.key"

        if key_file.exists():
            with open(key_file, 'rb') as f:
                key = f.read()
            self._harden_key_file(key_file)
            logger.warning("Using file-based encryption key. Set PRINTCAD_ENCRYPTION_KEY for production.")
            return key

        key = Fernet.generate_key()
        self._write_encryption_key(key, key_file)
        logger.warning("Generated new encryption key. Set PRINTCAD_ENCRYPTION_KEY for production deployments.")
        return key

    def _write_encryption_key(self, key: bytes, key_file: Optional[Path] = None) -> None:
        """Persist encryption key with restrictive permissions."""

        target = key_file or (self.data_dir / "compliance.key")
        with open(target, 'wb') as f:
            f.write(key)
        self._harden_key_file(target)

    def _harden_key_file(self, key_file: Path) -> None:
        """Ensure key material is not world-readable on POSIX systems."""

        if os.name == "nt":
            return

        try:
            key_file.chmod(0o600)
        except OSError as exc:
            logger.warning("Unable to adjust key permissions for %s: %s", key_file, exc)

    def _init_database(self):
        """Initialize compliance database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS requirements (
                    id TEXT PRIMARY KEY,
                    standard TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    implementation_guide TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'not_implemented',
                    evidence_required TEXT NOT NULL,
                    last_assessed TIMESTAMP,
                    next_assessment TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS evidence (
                    id TEXT PRIMARY KEY,
                    requirement_id TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    evidence_data BLOB NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    assessor TEXT NOT NULL,
                    validity_period INTEGER NOT NULL,
                    FOREIGN KEY (requirement_id) REFERENCES requirements (id)
                );

                CREATE TABLE IF NOT EXISTS assessments (
                    id TEXT PRIMARY KEY,
                    standard TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    assessor TEXT NOT NULL,
                    overall_score REAL NOT NULL,
                    requirements_met INTEGER NOT NULL,
                    total_requirements INTEGER NOT NULL,
                    findings TEXT NOT NULL,
                    recommendations TEXT NOT NULL,
                    next_assessment_due TIMESTAMP NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_trail (
                    id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    details TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_requirements_standard ON requirements(standard);
                CREATE INDEX IF NOT EXISTS idx_evidence_requirement ON evidence(requirement_id);
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_trail(timestamp);
            """)

            self._ensure_additional_columns(conn)

    def _ensure_additional_columns(self, conn: sqlite3.Connection) -> None:
        """Add integrity metadata columns if the schema predates them."""

        try:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(audit_trail)")}
            if "integrity_hash" not in columns:
                conn.execute("ALTER TABLE audit_trail ADD COLUMN integrity_hash TEXT")
        except sqlite3.DatabaseError as exc:
            logger.warning("Failed to ensure audit trail integrity column: %s", exc)

    def _load_compliance_requirements(self) -> Dict[ComplianceStandard, List[ComplianceRequirement]]:
        """Load compliance requirements for all standards"""
        requirements = {}

        # SOC 2 Type II Requirements
        requirements[ComplianceStandard.SOC2_TYPE2] = [
            ComplianceRequirement(
                id="SOC2-CC1.1",
                standard=ComplianceStandard.SOC2_TYPE2,
                category="Control Environment",
                description="Management establishes structures, reporting lines, and appropriate authorities and responsibilities",
                implementation_guide="Document organizational structure, roles, and responsibilities for security",
                priority=1,
                status="not_implemented",
                evidence_required=["organization_chart", "role_definitions", "responsibility_matrix"]
            ),
            ComplianceRequirement(
                id="SOC2-CC2.1",
                standard=ComplianceStandard.SOC2_TYPE2,
                category="Communication and Information",
                description="Management obtains or generates relevant, quality information",
                implementation_guide="Implement comprehensive logging and monitoring systems",
                priority=1,
                status="implemented",
                evidence_required=["audit_logs", "monitoring_dashboard", "reporting_system"]
            ),
            ComplianceRequirement(
                id="SOC2-CC3.1",
                standard=ComplianceStandard.SOC2_TYPE2,
                category="Risk Assessment",
                description="Management specifies objectives clearly and identifies and analyzes risks",
                implementation_guide="Conduct regular risk assessments and maintain risk register",
                priority=1,
                status="partial",
                evidence_required=["risk_assessment", "risk_register", "mitigation_plans"]
            )
        ]

        # ISO 27001 Requirements
        requirements[ComplianceStandard.ISO27001] = [
            ComplianceRequirement(
                id="ISO27001-A.5.1.1",
                standard=ComplianceStandard.ISO27001,
                category="Information Security Policies",
                description="Information security policy shall be defined, approved by management",
                implementation_guide="Create and maintain information security policy document",
                priority=1,
                status="implemented",
                evidence_required=["security_policy", "management_approval", "policy_distribution"]
            ),
            ComplianceRequirement(
                id="ISO27001-A.9.1.1",
                standard=ComplianceStandard.ISO27001,
                category="Access Control",
                description="Access control policy shall be established, documented and reviewed",
                implementation_guide="Implement role-based access control system",
                priority=1,
                status="implemented",
                evidence_required=["access_control_policy", "rbac_implementation", "access_reviews"]
            ),
            ComplianceRequirement(
                id="ISO27001-A.12.6.1",
                standard=ComplianceStandard.ISO27001,
                category="Operations Security",
                description="Management of technical vulnerabilities shall be implemented",
                implementation_guide="Establish vulnerability management process",
                priority=2,
                status="implemented",
                evidence_required=["vulnerability_scans", "patch_management", "security_updates"]
            )
        ]

        # NIST Cybersecurity Framework Requirements
        requirements[ComplianceStandard.NIST_CSF] = [
            ComplianceRequirement(
                id="NIST-ID.AM-1",
                standard=ComplianceStandard.NIST_CSF,
                category="Identify - Asset Management",
                description="Physical devices and systems within the organization are inventoried",
                implementation_guide="Maintain comprehensive asset inventory",
                priority=2,
                status="partial",
                evidence_required=["asset_inventory", "network_discovery", "device_management"]
            ),
            ComplianceRequirement(
                id="NIST-PR.AC-1",
                standard=ComplianceStandard.NIST_CSF,
                category="Protect - Access Control",
                description="Identities and credentials are issued, managed, verified, revoked",
                implementation_guide="Implement identity and access management system",
                priority=1,
                status="implemented",
                evidence_required=["iam_system", "credential_management", "access_provisioning"]
            ),
            ComplianceRequirement(
                id="NIST-DE.CM-1",
                standard=ComplianceStandard.NIST_CSF,
                category="Detect - Continuous Monitoring",
                description="The network is monitored to detect potential cybersecurity events",
                implementation_guide="Deploy network monitoring and SIEM solution",
                priority=1,
                status="implemented",
                evidence_required=["network_monitoring", "siem_logs", "incident_detection"]
            )
        ]

        # GDPR Requirements
        requirements[ComplianceStandard.GDPR] = [
            ComplianceRequirement(
                id="GDPR-Art25",
                standard=ComplianceStandard.GDPR,
                category="Data Protection by Design",
                description="Data protection shall be integrated into processing activities by design and by default",
                implementation_guide="Implement privacy by design principles",
                priority=1,
                status="implemented",
                evidence_required=["privacy_impact_assessment", "data_minimization", "consent_management"]
            ),
            ComplianceRequirement(
                id="GDPR-Art32",
                standard=ComplianceStandard.GDPR,
                category="Security of Processing",
                description="Implement appropriate technical and organizational security measures",
                implementation_guide="Deploy encryption, access controls, and security monitoring",
                priority=1,
                status="implemented",
                evidence_required=["encryption_implementation", "access_controls", "security_monitoring"]
            )
        ]

        return requirements

    async def assess_compliance(self, standard: ComplianceStandard, assessor: str) -> ComplianceAssessment:
        """Perform comprehensive compliance assessment"""
        assessment_id = str(uuid.uuid4())
        timestamp = datetime.now()

        if standard not in self.requirements:
            raise ValueError(f"Unsupported compliance standard: {standard}")

        requirements = self.requirements[standard]
        requirements_met = 0
        total_requirements = len(requirements)
        findings = []
        recommendations = []

        # Assess each requirement
        for req in requirements:
            if await self._assess_requirement(req):
                requirements_met += 1
            else:
                findings.append(f"Requirement {req.id} not fully implemented: {req.description}")
                recommendations.append(f"Implement {req.id}: {req.implementation_guide}")

        # Calculate overall score
        overall_score = (requirements_met / total_requirements) * 100 if total_requirements > 0 else 0

        # Next assessment due date
        next_assessment_due = timestamp + timedelta(days=365)  # Annual assessment

        assessment = ComplianceAssessment(
            assessment_id=assessment_id,
            standard=standard,
            timestamp=timestamp,
            assessor=assessor,
            overall_score=overall_score,
            requirements_met=requirements_met,
            total_requirements=total_requirements,
            findings=findings,
            recommendations=recommendations,
            next_assessment_due=next_assessment_due
        )

        # Store assessment
        await self._store_assessment(assessment)

        return assessment

    async def _assess_requirement(self, requirement: ComplianceRequirement) -> bool:
        """Assess individual compliance requirement"""
        # Check if requirement has valid evidence
        evidence = await self._get_requirement_evidence(requirement.id)

        if not evidence:
            return False

        # Check if evidence is still valid
        current_time = datetime.now()
        for ev in evidence:
            if current_time - ev.timestamp > ev.validity_period:
                return False

        # Check if all required evidence types are present
        evidence_types = {ev.evidence_type for ev in evidence}
        required_types = set(requirement.evidence_required)

        return required_types.issubset(evidence_types)

    async def add_compliance_evidence(self, requirement_id: str, evidence_type: str,
                                    evidence_data: str, assessor: str,
                                    validity_days: int = 365) -> str:
        """Add evidence for compliance requirement"""
        evidence_id = str(uuid.uuid4())
        timestamp = datetime.now()
        validity_period = timedelta(days=validity_days)

        # Encrypt sensitive evidence data
        encrypted_data = self.cipher.encrypt(evidence_data.encode())

        evidence = ComplianceEvidence(
            requirement_id=requirement_id,
            evidence_type=evidence_type,
            evidence_data=evidence_data,
            timestamp=timestamp,
            assessor=assessor,
            validity_period=validity_period
        )

        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO evidence (id, requirement_id, evidence_type, evidence_data,
                                    timestamp, assessor, validity_period)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                evidence_id,
                requirement_id,
                evidence_type,
                encrypted_data,
                timestamp,
                assessor,
                validity_period.total_seconds()
            ))

        logger.info(f"Added evidence {evidence_id} for requirement {requirement_id}")
        return evidence_id

    async def _get_requirement_evidence(self, requirement_id: str) -> List[ComplianceEvidence]:
        """Get all evidence for a requirement"""
        evidence_list = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, evidence_type, evidence_data, timestamp, assessor, validity_period
                FROM evidence
                WHERE requirement_id = ?
                ORDER BY timestamp DESC
            """, (requirement_id,))

            for row in cursor.fetchall():
                evidence_id, evidence_type, encrypted_data, timestamp, assessor, validity_seconds = row

                # Decrypt evidence data
                evidence_data = self.cipher.decrypt(encrypted_data).decode()

                evidence = ComplianceEvidence(
                    requirement_id=requirement_id,
                    evidence_type=evidence_type,
                    evidence_data=evidence_data,
                    timestamp=datetime.fromisoformat(timestamp),
                    assessor=assessor,
                    validity_period=timedelta(seconds=validity_seconds)
                )
                evidence_list.append(evidence)

        return evidence_list

    async def _store_assessment(self, assessment: ComplianceAssessment):
        """Store compliance assessment in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO assessments (id, standard, timestamp, assessor, overall_score,
                                       requirements_met, total_requirements, findings,
                                       recommendations, next_assessment_due)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assessment.assessment_id,
                assessment.standard.value,
                assessment.timestamp,
                assessment.assessor,
                assessment.overall_score,
                assessment.requirements_met,
                assessment.total_requirements,
                json.dumps(assessment.findings),
                json.dumps(assessment.recommendations),
                assessment.next_assessment_due
            ))

    async def generate_compliance_report(self, standard: ComplianceStandard) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        latest_assessment = await self._get_latest_assessment(standard)

        if not latest_assessment:
            return {
                "error": f"No assessment found for {standard.value}",
                "standard": standard.value
            }

        requirements = self.requirements.get(standard, [])
        implemented_reqs = [req for req in requirements if req.status == "implemented"]
        partial_reqs = [req for req in requirements if req.status == "partial"]
        not_implemented_reqs = [req for req in requirements if req.status == "not_implemented"]

        report = {
            "standard": standard.value,
            "assessment": {
                "id": latest_assessment.assessment_id,
                "date": latest_assessment.timestamp.isoformat(),
                "assessor": latest_assessment.assessor,
                "overall_score": latest_assessment.overall_score,
                "requirements_met": latest_assessment.requirements_met,
                "total_requirements": latest_assessment.total_requirements,
                "compliance_percentage": round((latest_assessment.requirements_met / latest_assessment.total_requirements) * 100, 2)
            },
            "requirement_breakdown": {
                "implemented": len(implemented_reqs),
                "partial": len(partial_reqs),
                "not_implemented": len(not_implemented_reqs)
            },
            "findings": latest_assessment.findings,
            "recommendations": latest_assessment.recommendations,
            "next_assessment_due": latest_assessment.next_assessment_due.isoformat(),
            "certification_status": self._get_certification_status(latest_assessment.overall_score)
        }

        return report

    async def _get_latest_assessment(self, standard: ComplianceStandard) -> Optional[ComplianceAssessment]:
        """Get latest assessment for a standard"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, timestamp, assessor, overall_score, requirements_met,
                       total_requirements, findings, recommendations, next_assessment_due
                FROM assessments
                WHERE standard = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (standard.value,))

            row = cursor.fetchone()
            if not row:
                return None

            assessment_id, timestamp, assessor, overall_score, requirements_met, \
            total_requirements, findings, recommendations, next_assessment_due = row

            return ComplianceAssessment(
                assessment_id=assessment_id,
                standard=standard,
                timestamp=datetime.fromisoformat(timestamp),
                assessor=assessor,
                overall_score=overall_score,
                requirements_met=requirements_met,
                total_requirements=total_requirements,
                findings=json.loads(findings),
                recommendations=json.loads(recommendations),
                next_assessment_due=datetime.fromisoformat(next_assessment_due)
            )

    def _get_certification_status(self, score: float) -> str:
        """Determine certification status based on score"""
        if score >= 95:
            return "Fully Compliant"
        elif score >= 85:
            return "Substantially Compliant"
        elif score >= 70:
            return "Partially Compliant"
        else:
            return "Non-Compliant"

    async def log_audit_event(self, action: str, user_id: str, resource: str,
                            details: str, ip_address: str = None,
                            user_agent: str = None):
        """Log audit event for compliance"""
        event_id = str(uuid.uuid4())
        timestamp = datetime.now()
        timestamp_iso = timestamp.isoformat()
        payload = {
            "action": action,
            "user_id": user_id,
            "resource": resource,
            "timestamp": timestamp_iso,
            "details": details,
            "ip_address": ip_address or "",
            "user_agent": user_agent or "",
        }

        with sqlite3.connect(self.db_path) as conn:
            self._ensure_additional_columns(conn)
            previous_hash = self._get_latest_audit_hash(conn)
            integrity_hash = self._calculate_audit_hash(previous_hash, payload)
            conn.execute(
                """
                INSERT INTO audit_trail (id, action, user_id, resource, timestamp,
                                       details, ip_address, user_agent, integrity_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, action, user_id, resource, timestamp_iso, details, ip_address, user_agent, integrity_hash),
            )

        logger.info(
            "Audit event logged: %s by %s on %s (hash=%s)",
            action,
            user_id,
            resource,
            integrity_hash,
        )

    def _get_latest_audit_hash(self, conn: sqlite3.Connection) -> Optional[str]:
        """Return the most recent audit trail hash for chaining."""

        try:
            row = conn.execute(
                "SELECT integrity_hash FROM audit_trail ORDER BY timestamp DESC, rowid DESC LIMIT 1"
            ).fetchone()
            if row:
                return row[0]
        except sqlite3.DatabaseError as exc:
            logger.warning("Unable to read latest audit hash: %s", exc)
        return None

    def _calculate_audit_hash(self, previous_hash: Optional[str], payload: Dict[str, Any]) -> str:
        """Calculate deterministic hash for an audit event."""

        hasher = hashlib.sha256()
        if previous_hash:
            hasher.update(previous_hash.encode('utf-8'))

        for key in sorted(payload.keys()):
            value = payload[key] if payload[key] is not None else ""
            hasher.update(str(value).encode('utf-8'))

        return hasher.hexdigest()

    def verify_audit_chain(self) -> Dict[str, Any]:
        """Verify integrity hashes for the entire audit trail."""

        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT id, action, user_id, resource, timestamp, details, ip_address, user_agent, integrity_hash "
                    "FROM audit_trail ORDER BY timestamp ASC, rowid ASC"
                ).fetchall()
        except sqlite3.DatabaseError as exc:
            return {"valid": False, "error": str(exc), "entries_checked": 0, "failures": []}

        previous_hash = None
        failures: List[Dict[str, Any]] = []

        for row in rows:
            payload = {
                "action": row[1],
                "user_id": row[2],
                "resource": row[3],
                "timestamp": row[4],
                "details": row[5],
                "ip_address": row[6] or "",
                "user_agent": row[7] or "",
            }
            expected_hash = self._calculate_audit_hash(previous_hash, payload)
            stored_hash = row[8]
            if expected_hash != stored_hash:
                failures.append({
                    "id": row[0],
                    "expected": expected_hash,
                    "stored": stored_hash,
                })
            previous_hash = stored_hash

        return {
            "valid": not failures,
            "entries_checked": len(rows),
            "failures": failures,
        }

    def rotate_encryption_key(self, new_key: Optional[bytes] = None) -> bytes:
        """Rotate the evidence encryption key and re-encrypt stored artifacts."""

        new_key = new_key or Fernet.generate_key()
        new_cipher = Fernet(new_key)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT id, evidence_data FROM evidence").fetchall()
                for row in rows:
                    decrypted = self.cipher.decrypt(row["evidence_data"])
                    re_encrypted = new_cipher.encrypt(decrypted)
                    conn.execute(
                        "UPDATE evidence SET evidence_data = ? WHERE id = ?",
                        (re_encrypted, row["id"]),
                    )
        except (sqlite3.DatabaseError, Exception) as exc:
            logger.error("Failed to rotate encryption key: %s", exc)
            raise

        self._write_encryption_key(new_key)
        self.encryption_key = new_key
        self.cipher = new_cipher
        logger.info("Rotated compliance evidence encryption key across %d record(s)", len(rows))
        return new_key

    async def get_compliance_dashboard(self) -> Dict[str, Any]:
        """Get compliance dashboard data"""
        dashboard = {
            "overall_status": {},
            "recent_assessments": [],
            "upcoming_assessments": [],
            "compliance_trends": {}
        }

        # Get status for each standard
        for standard in ComplianceStandard:
            latest_assessment = await self._get_latest_assessment(standard)
            if latest_assessment:
                dashboard["overall_status"][standard.value] = {
                    "score": latest_assessment.overall_score,
                    "status": self._get_certification_status(latest_assessment.overall_score),
                    "last_assessed": latest_assessment.timestamp.isoformat(),
                    "next_due": latest_assessment.next_assessment_due.isoformat()
                }

        return dashboard

async def main():
    """Main compliance manager entry point"""
    manager = ComplianceManager()

    # Perform sample assessment
    assessment = await manager.assess_compliance(ComplianceStandard.SOC2_TYPE2, "Security Auditor")
    print(f"SOC 2 Assessment Score: {assessment.overall_score}/100")

    # Generate report
    report = await manager.generate_compliance_report(ComplianceStandard.SOC2_TYPE2)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    asyncio.run(main())