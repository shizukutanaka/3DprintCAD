"""
Disaster Recovery and Business Continuity Manager for 3D Print CAD Assistant
Provides comprehensive backup, recovery, and business continuity capabilities
Suitable for mission-critical government and enterprise deployments
"""

import asyncio
import os
import shutil
import gzip
import tarfile
import json
import boto3
import psutil
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from pathlib import Path
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import hashlib
import sqlite3

logger = logging.getLogger(__name__)

class BackupType(Enum):
    """Types of backups"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"

class RecoveryTier(Enum):
    """Recovery time objectives"""
    CRITICAL = "critical"      # RTO: < 1 hour, RPO: < 15 minutes
    HIGH = "high"             # RTO: < 4 hours, RPO: < 1 hour
    MEDIUM = "medium"         # RTO: < 24 hours, RPO: < 4 hours
    LOW = "low"              # RTO: < 72 hours, RPO: < 24 hours

@dataclass
class BackupJob:
    """Backup job configuration"""
    id: str
    name: str
    backup_type: BackupType
    source_paths: List[str]
    destination: str
    schedule: str  # cron format
    retention_days: int
    compression: bool
    encryption: bool
    recovery_tier: RecoveryTier
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

@dataclass
class BackupRecord:
    """Record of completed backup"""
    id: str
    job_id: str
    backup_type: BackupType
    timestamp: datetime
    size_bytes: int
    checksum: str
    location: str
    status: str  # success, failed, partial
    duration_seconds: float
    files_count: int
    error_message: Optional[str] = None

@dataclass
class RecoveryPoint:
    """Point-in-time recovery point"""
    timestamp: datetime
    backup_records: List[BackupRecord]
    description: str
    verified: bool
    recovery_tier: RecoveryTier

class DisasterRecoveryManager:
    """Comprehensive disaster recovery and backup management"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.backup_root = Path(self.config["backup_root"])
        self.backup_root.mkdir(parents=True, exist_ok=True)

        # Initialize cloud storage if configured
        self.s3_client = None
        if self.config.get("aws_s3_enabled"):
            self.s3_client = boto3.client('s3')

        # Initialize database for tracking
        self.db_path = self.backup_root / "backup_tracking.db"
        self._init_database()

        # Background services
        self.scheduler_running = False
        self.scheduler_thread = None
        self.executor = ThreadPoolExecutor(max_workers=4)

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load disaster recovery configuration"""
        default_config = {
            "backup_root": "/var/backups/3dcad",
            "max_parallel_jobs": 2,
            "verification_interval_hours": 24,
            "cleanup_interval_hours": 168,  # Weekly
            "aws_s3_enabled": False,
            "aws_s3_bucket": None,
            "encryption_enabled": True,
            "compression_enabled": True,
            "notification_webhook": None,
            "monitoring_enabled": True
        }

        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Could not load config from {config_path}: {e}")

        return default_config

    def _init_database(self):
        """Initialize backup tracking database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS backup_jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    backup_type TEXT NOT NULL,
                    source_paths TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    retention_days INTEGER NOT NULL,
                    compression BOOLEAN NOT NULL,
                    encryption BOOLEAN NOT NULL,
                    recovery_tier TEXT NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT 1,
                    last_run TIMESTAMP,
                    next_run TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS backup_records (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    backup_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    checksum TEXT NOT NULL,
                    location TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    files_count INTEGER NOT NULL,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES backup_jobs (id)
                );

                CREATE TABLE IF NOT EXISTS recovery_points (
                    id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    description TEXT NOT NULL,
                    verified BOOLEAN NOT NULL DEFAULT 0,
                    recovery_tier TEXT NOT NULL,
                    backup_records TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS recovery_tests (
                    id TEXT PRIMARY KEY,
                    recovery_point_id TEXT NOT NULL,
                    test_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    status TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (recovery_point_id) REFERENCES recovery_points (id)
                );

                CREATE INDEX IF NOT EXISTS idx_backup_records_timestamp ON backup_records(timestamp);
                CREATE INDEX IF NOT EXISTS idx_recovery_points_timestamp ON recovery_points(timestamp);
            """)

    async def create_backup_job(self, job: BackupJob) -> str:
        """Create new backup job"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO backup_jobs
                (id, name, backup_type, source_paths, destination, schedule,
                 retention_days, compression, encryption, recovery_tier, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id, job.name, job.backup_type.value,
                json.dumps(job.source_paths), job.destination, job.schedule,
                job.retention_days, job.compression, job.encryption,
                job.recovery_tier.value, job.enabled
            ))

        logger.info(f"Created backup job: {job.name} ({job.id})")
        return job.id

    async def execute_backup(self, job_id: str) -> BackupRecord:
        """Execute backup job"""
        job = await self._get_backup_job(job_id)
        if not job:
            raise ValueError(f"Backup job {job_id} not found")

        if not job.enabled:
            raise ValueError(f"Backup job {job_id} is disabled")

        logger.info(f"Starting backup job: {job.name}")
        start_time = time.time()

        try:
            # Create backup directory
            timestamp = datetime.now()
            backup_dir = self.backup_root / job.id / timestamp.strftime("%Y%m%d_%H%M%S")
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Determine backup files
            files_to_backup = []
            for source_path in job.source_paths:
                source = Path(source_path)
                if source.exists():
                    if source.is_file():
                        files_to_backup.append(source)
                    elif source.is_dir():
                        files_to_backup.extend(source.rglob("*"))

            # Filter files based on backup type
            if job.backup_type == BackupType.INCREMENTAL:
                files_to_backup = await self._filter_incremental_files(job_id, files_to_backup)
            elif job.backup_type == BackupType.DIFFERENTIAL:
                files_to_backup = await self._filter_differential_files(job_id, files_to_backup)

            # Create backup archive
            archive_path = backup_dir / f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.tar"
            if job.compression:
                archive_path = archive_path.with_suffix('.tar.gz')

            total_size = 0
            files_count = 0

            if job.compression:
                with tarfile.open(archive_path, 'w:gz') as tar:
                    for file_path in files_to_backup:
                        if file_path.is_file():
                            tar.add(file_path, arcname=file_path.relative_to(Path.cwd()))
                            total_size += file_path.stat().st_size
                            files_count += 1
            else:
                with tarfile.open(archive_path, 'w') as tar:
                    for file_path in files_to_backup:
                        if file_path.is_file():
                            tar.add(file_path, arcname=file_path.relative_to(Path.cwd()))
                            total_size += file_path.stat().st_size
                            files_count += 1

            # Encrypt if required
            final_path = archive_path
            if job.encryption:
                final_path = await self._encrypt_backup(archive_path)
                archive_path.unlink()  # Remove unencrypted version

            # Calculate checksum
            checksum = await self._calculate_checksum(final_path)

            # Upload to cloud if configured
            cloud_location = None
            if self.s3_client and self.config.get("aws_s3_bucket"):
                cloud_location = await self._upload_to_s3(final_path, job.id, timestamp)

            # Create backup record
            duration = time.time() - start_time
            backup_record = BackupRecord(
                id=f"{job_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}",
                job_id=job_id,
                backup_type=job.backup_type,
                timestamp=timestamp,
                size_bytes=final_path.stat().st_size,
                checksum=checksum,
                location=str(final_path),
                status="success",
                duration_seconds=duration,
                files_count=files_count
            )

            # Store record
            await self._store_backup_record(backup_record)

            # Update job last run time
            await self._update_job_last_run(job_id, timestamp)

            logger.info(f"Backup completed: {job.name} ({files_count} files, {total_size / 1024 / 1024:.2f}MB)")
            return backup_record

        except Exception as e:
            duration = time.time() - start_time
            error_record = BackupRecord(
                id=f"{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_failed",
                job_id=job_id,
                backup_type=job.backup_type,
                timestamp=datetime.now(),
                size_bytes=0,
                checksum="",
                location="",
                status="failed",
                duration_seconds=duration,
                files_count=0,
                error_message=str(e)
            )
            await self._store_backup_record(error_record)
            logger.error(f"Backup failed: {job.name} - {e}")
            raise

    async def restore_from_backup(self, backup_record_id: str,
                                restore_path: str,
                                verify: bool = True) -> bool:
        """Restore from backup"""
        backup_record = await self._get_backup_record(backup_record_id)
        if not backup_record:
            raise ValueError(f"Backup record {backup_record_id} not found")

        logger.info(f"Starting restore from backup: {backup_record_id}")

        try:
            restore_destination = Path(restore_path)
            restore_destination.mkdir(parents=True, exist_ok=True)

            backup_file = Path(backup_record.location)
            if not backup_file.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_file}")

            # Verify checksum if requested
            if verify:
                current_checksum = await self._calculate_checksum(backup_file)
                if current_checksum != backup_record.checksum:
                    raise ValueError("Backup file checksum mismatch - file may be corrupted")

            # Decrypt if needed (detect by file extension or metadata)
            working_file = backup_file
            if backup_file.suffix == '.enc':
                working_file = await self._decrypt_backup(backup_file)

            # Extract archive
            if working_file.suffix in ['.gz', '.tgz']:
                with tarfile.open(working_file, 'r:gz') as tar:
                    tar.extractall(restore_destination)
            else:
                with tarfile.open(working_file, 'r') as tar:
                    tar.extractall(restore_destination)

            # Clean up temporary decrypted file
            if working_file != backup_file:
                working_file.unlink()

            logger.info(f"Restore completed to: {restore_destination}")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    async def create_recovery_point(self, description: str,
                                  recovery_tier: RecoveryTier) -> str:
        """Create point-in-time recovery point"""
        timestamp = datetime.now()

        # Get all recent successful backups
        recent_backups = await self._get_recent_backups(hours=24)

        recovery_point = RecoveryPoint(
            timestamp=timestamp,
            backup_records=recent_backups,
            description=description,
            verified=False,
            recovery_tier=recovery_tier
        )

        # Store recovery point
        recovery_point_id = f"rp_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO recovery_points
                (id, timestamp, description, verified, recovery_tier, backup_records)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                recovery_point_id,
                timestamp,
                description,
                False,
                recovery_tier.value,
                json.dumps([r.id for r in recent_backups])
            ))

        logger.info(f"Created recovery point: {recovery_point_id}")
        return recovery_point_id

    async def test_recovery(self, recovery_point_id: str,
                          test_type: str = "basic") -> bool:
        """Test recovery point viability"""
        logger.info(f"Testing recovery point: {recovery_point_id}")

        start_time = time.time()
        test_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            # Create temporary test environment
            test_dir = self.backup_root / "recovery_tests" / test_id
            test_dir.mkdir(parents=True, exist_ok=True)

            # Get recovery point
            recovery_point = await self._get_recovery_point(recovery_point_id)
            if not recovery_point:
                raise ValueError(f"Recovery point {recovery_point_id} not found")

            # Test restore of each backup in recovery point
            for backup_record in recovery_point.backup_records:
                test_restore_path = test_dir / f"restore_{backup_record.id}"
                success = await self.restore_from_backup(
                    backup_record.id,
                    str(test_restore_path),
                    verify=True
                )
                if not success:
                    raise Exception(f"Failed to restore backup {backup_record.id}")

            # Additional integrity checks based on test type
            if test_type == "comprehensive":
                await self._comprehensive_recovery_test(test_dir)

            duration = time.time() - start_time

            # Record test result
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO recovery_tests
                    (id, recovery_point_id, test_type, timestamp, status, duration_seconds, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    test_id, recovery_point_id, test_type, datetime.now(),
                    "success", duration, "Recovery test completed successfully"
                ))

            # Mark recovery point as verified
            await self._mark_recovery_point_verified(recovery_point_id)

            logger.info(f"Recovery test successful: {recovery_point_id}")
            return True

        except Exception as e:
            duration = time.time() - start_time

            # Record test failure
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO recovery_tests
                    (id, recovery_point_id, test_type, timestamp, status, duration_seconds, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    test_id, recovery_point_id, test_type, datetime.now(),
                    "failed", duration, str(e)
                ))

            logger.error(f"Recovery test failed: {recovery_point_id} - {e}")
            return False

        finally:
            # Cleanup test directory
            if test_dir.exists():
                shutil.rmtree(test_dir, ignore_errors=True)

    async def start_scheduler(self):
        """Start backup scheduler"""
        self.scheduler_running = True

        def scheduler_loop():
            while self.scheduler_running:
                try:
                    # Check for jobs that need to run
                    jobs = asyncio.run(self._get_scheduled_jobs())

                    for job in jobs:
                        if self._should_run_job(job):
                            logger.info(f"Triggering scheduled backup: {job.name}")
                            asyncio.run(self.execute_backup(job.id))

                    # Sleep for 1 minute before checking again
                    time.sleep(60)

                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                    time.sleep(60)

        self.scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info("Backup scheduler started")

    def stop_scheduler(self):
        """Stop backup scheduler"""
        self.scheduler_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Backup scheduler stopped")

    async def get_disaster_recovery_report(self) -> Dict[str, Any]:
        """Generate comprehensive disaster recovery report"""
        # Get backup statistics
        backup_stats = await self._get_backup_statistics()

        # Get recovery point status
        recovery_points = await self._get_recovery_points_summary()

        # Get recent test results
        recent_tests = await self._get_recent_test_results()

        # Calculate RTO/RPO metrics
        rto_rpo_metrics = await self._calculate_rto_rpo_metrics()

        report = {
            "timestamp": datetime.now().isoformat(),
            "backup_health": {
                "total_jobs": backup_stats["total_jobs"],
                "active_jobs": backup_stats["active_jobs"],
                "successful_backups_24h": backup_stats["successful_24h"],
                "failed_backups_24h": backup_stats["failed_24h"],
                "total_backup_size": backup_stats["total_size"],
                "average_backup_duration": backup_stats["avg_duration"]
            },
            "recovery_readiness": {
                "total_recovery_points": len(recovery_points),
                "verified_recovery_points": sum(1 for rp in recovery_points if rp["verified"]),
                "latest_recovery_point": recovery_points[0]["timestamp"] if recovery_points else None,
                "recovery_test_success_rate": recent_tests["success_rate"]
            },
            "rto_rpo_compliance": rto_rpo_metrics,
            "recommendations": await self._generate_dr_recommendations()
        }

        return report

    # Helper methods

    async def _get_backup_job(self, job_id: str) -> Optional[BackupJob]:
        """Get backup job by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, name, backup_type, source_paths, destination, schedule,
                       retention_days, compression, encryption, recovery_tier, enabled,
                       last_run, next_run
                FROM backup_jobs WHERE id = ?
            """, (job_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return BackupJob(
                id=row[0],
                name=row[1],
                backup_type=BackupType(row[2]),
                source_paths=json.loads(row[3]),
                destination=row[4],
                schedule=row[5],
                retention_days=row[6],
                compression=bool(row[7]),
                encryption=bool(row[8]),
                recovery_tier=RecoveryTier(row[9]),
                enabled=bool(row[10]),
                last_run=datetime.fromisoformat(row[11]) if row[11] else None,
                next_run=datetime.fromisoformat(row[12]) if row[12] else None
            )

    async def _store_backup_record(self, record: BackupRecord):
        """Store backup record in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO backup_records
                (id, job_id, backup_type, timestamp, size_bytes, checksum,
                 location, status, duration_seconds, files_count, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id, record.job_id, record.backup_type.value,
                record.timestamp, record.size_bytes, record.checksum,
                record.location, record.status, record.duration_seconds,
                record.files_count, record.error_message
            ))

    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    async def _encrypt_backup(self, file_path: Path) -> Path:
        """Encrypt backup file"""
        # Simplified encryption - in production, use proper key management
        encrypted_path = file_path.with_suffix(file_path.suffix + '.enc')

        # Use GPG or similar encryption in production
        # For demo, just rename (implement proper encryption)
        shutil.move(file_path, encrypted_path)

        return encrypted_path

    async def _decrypt_backup(self, encrypted_path: Path) -> Path:
        """Decrypt backup file"""
        # Simplified decryption - implement proper decryption
        decrypted_path = encrypted_path.with_suffix('')
        shutil.copy(encrypted_path, decrypted_path)
        return decrypted_path

    async def _upload_to_s3(self, file_path: Path, job_id: str, timestamp: datetime) -> str:
        """Upload backup to S3"""
        if not self.s3_client:
            return ""

        bucket = self.config["aws_s3_bucket"]
        key = f"backups/{job_id}/{timestamp.strftime('%Y/%m/%d')}/{file_path.name}"

        try:
            self.s3_client.upload_file(str(file_path), bucket, key)
            return f"s3://{bucket}/{key}"
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return ""

    async def _filter_incremental_files(self, job_id: str, files: List[Path]) -> List[Path]:
        """Filter files for incremental backup"""
        # Get last backup timestamp
        last_backup = await self._get_last_successful_backup(job_id)
        if not last_backup:
            return files  # First backup, include all files

        # Filter files modified since last backup
        filtered_files = []
        for file_path in files:
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime > last_backup.timestamp:
                    filtered_files.append(file_path)

        return filtered_files

    async def _filter_differential_files(self, job_id: str, files: List[Path]) -> List[Path]:
        """Filter files for differential backup"""
        # Get last full backup timestamp
        last_full_backup = await self._get_last_full_backup(job_id)
        if not last_full_backup:
            return files  # No full backup, include all files

        # Filter files modified since last full backup
        filtered_files = []
        for file_path in files:
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime > last_full_backup.timestamp:
                    filtered_files.append(file_path)

        return filtered_files

    async def _get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Total jobs
            total_jobs = conn.execute("SELECT COUNT(*) FROM backup_jobs").fetchone()[0]
            active_jobs = conn.execute("SELECT COUNT(*) FROM backup_jobs WHERE enabled = 1").fetchone()[0]

            # 24h statistics
            cutoff_24h = datetime.now() - timedelta(hours=24)
            successful_24h = conn.execute("""
                SELECT COUNT(*) FROM backup_records
                WHERE timestamp > ? AND status = 'success'
            """, (cutoff_24h,)).fetchone()[0]

            failed_24h = conn.execute("""
                SELECT COUNT(*) FROM backup_records
                WHERE timestamp > ? AND status = 'failed'
            """, (cutoff_24h,)).fetchone()[0]

            # Size and duration
            total_size = conn.execute("""
                SELECT COALESCE(SUM(size_bytes), 0) FROM backup_records
                WHERE status = 'success'
            """).fetchone()[0]

            avg_duration = conn.execute("""
                SELECT COALESCE(AVG(duration_seconds), 0) FROM backup_records
                WHERE status = 'success' AND timestamp > ?
            """, (cutoff_24h,)).fetchone()[0]

        return {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "successful_24h": successful_24h,
            "failed_24h": failed_24h,
            "total_size": total_size,
            "avg_duration": avg_duration
        }

    async def _generate_dr_recommendations(self) -> List[str]:
        """Generate disaster recovery recommendations"""
        recommendations = []

        # Check backup frequency
        stats = await self._get_backup_statistics()
        if stats["failed_24h"] > 0:
            recommendations.append("Address recent backup failures to ensure data protection")

        # Check recovery testing
        recent_tests = await self._get_recent_test_results()
        if recent_tests["last_test_days"] > 30:
            recommendations.append("Perform recovery testing - last test was over 30 days ago")

        # Check retention compliance
        recommendations.append("Review backup retention policies for compliance requirements")

        # Check offsite backups
        if not self.config.get("aws_s3_enabled"):
            recommendations.append("Consider enabling offsite backup storage for better disaster resilience")

        return recommendations

async def main():
    """Main disaster recovery entry point"""
    dr_manager = DisasterRecoveryManager()

    # Example usage
    report = await dr_manager.get_disaster_recovery_report()
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    asyncio.run(main())