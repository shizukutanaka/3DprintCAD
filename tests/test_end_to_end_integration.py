"""End-to-end integration tests for 3D Print CAD Assistant."""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import shutil
import time

from src.cli_main import CLIProcessor, main as cli_main
from src.core.config import get_config
from src.core.compliance_manager import ComplianceManager, ComplianceStandard
from src.core.memory_manager import get_memory_manager
from src.core.progress import get_progress_manager
from src.cloud.distributed_processor import get_distributed_manager


class TestEndToEndWorkflow:
    """Comprehensive end-to-end workflow tests."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def sample_stl_file(self, temp_dir):
        """Create a sample STL file for testing."""
        stl_content = """
solid test_cube
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex 1 0 0
      vertex 1 1 0
      vertex 0 1 0
    endloop
  endfacet
endsolid test_cube
        """.strip()

        stl_file = temp_dir / "test_cube.stl"
        stl_file.write_text(stl_content)
        return stl_file

    @pytest.fixture
    def sample_obj_file(self, temp_dir):
        """Create a sample OBJ file for testing."""
        obj_content = """
# Sample cube OBJ file
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0
v 1.0 1.0 0.0
f 1 2 3
f 2 4 3
        """.strip()

        obj_file = temp_dir / "test_cube.obj"
        obj_file.write_text(obj_content)
        return obj_file

    def test_complete_validation_workflow(self, temp_dir, sample_stl_file):
        """Test complete validation workflow from CLI to results."""
        output_file = temp_dir / "validation_result.json"

        # Run validation via CLI
        exit_code = cli_main([
            str(sample_stl_file),
            "--validate",
            "--output", str(output_file),
            "--verbose"
        ])

        assert exit_code == 0
        assert output_file.exists()

        # Verify results
        with open(output_file, 'r') as f:
            result = json.load(f)

        assert result["success"] is True
        assert "validation" in result
        assert "mesh_info" in result
        assert result["mesh_info"]["vertices"] > 0

    def test_batch_processing_workflow(self, temp_dir, sample_stl_file, sample_obj_file):
        """Test batch processing of multiple files."""
        output_file = temp_dir / "batch_result.json"

        # Run batch processing
        exit_code = cli_main([
            "--batch",
            str(sample_stl_file), str(sample_obj_file),
            "--parallel",
            "--max-workers", "2",
            "--output", str(output_file),
            "--summary"
        ])

        assert exit_code == 0
        assert output_file.exists()

        # Verify batch results
        with open(output_file, 'r') as f:
            result = json.load(f)

        assert "files" in result
        assert len(result["files"]) == 2

        # Both files should be processed successfully
        successful_files = [f for f in result["files"] if f["success"]]
        assert len(successful_files) == 2

    def test_repair_workflow(self, temp_dir):
        """Test mesh repair workflow."""
        # Create a file with repairable issues (simplified)
        stl_content = """
solid test_cube_with_hole
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
  # Missing some faces to simulate hole
endsolid test_cube_with_hole
        """.strip()

        input_file = temp_dir / "damaged_cube.stl"
        input_file.write_text(stl_content)

        repaired_file = temp_dir / "repaired_cube.stl"
        output_file = temp_dir / "repair_result.json"

        # Run repair workflow
        exit_code = cli_main([
            str(input_file),
            "--validate",
            "--repair",
            "--save-repaired", str(repaired_file),
            "--output", str(output_file)
        ])

        assert exit_code == 0
        assert output_file.exists()

        # Verify repair results
        with open(output_file, 'r') as f:
            result = json.load(f)

        assert result["success"] is True
        assert "repaired" in result or result.get("validation", {}).get("issues", [])

    def test_slicing_workflow(self, temp_dir, sample_stl_file):
        """Test slicing workflow."""
        output_file = temp_dir / "slice_result.json"

        # Run slicing
        exit_code = cli_main([
            str(sample_stl_file),
            "--slice",
            "--layer-height", "0.2",
            "--infill", "20",
            "--output", str(output_file)
        ])

        assert exit_code == 0
        assert output_file.exists()

        # Verify slicing results
        with open(output_file, 'r') as f:
            result = json.load(f)

        assert result["success"] is True
        assert "slicing" in result
        assert result["slicing"]["layers"] > 0

    def test_distributed_processing_workflow(self, temp_dir, sample_stl_file):
        """Test distributed processing capabilities."""
        # Initialize distributed processing
        from src.cloud.distributed_processor import init_distributed_processing, shutdown_distributed_processing

        try:
            init_distributed_processing(max_workers=2, enable_cloud_scaling=False)

            manager = get_distributed_manager()

            # Submit validation task
            task_id = manager.submit_task(
                operation="validate",
                input_data={"mesh_data": str(sample_stl_file)},
                priority=manager.task_queue._priority_queues.__class__.__bases__[0].HIGH
            )

            # Wait for completion
            max_wait = 30
            start_time = time.time()

            while time.time() - start_time < max_wait:
                task = manager.get_task_status(task_id)
                if task and task.status.value in ["completed", "failed"]:
                    break
                time.sleep(1)

            # Verify task completion
            final_task = manager.get_task_status(task_id)
            assert final_task is not None
            assert final_task.status.value == "completed"
            assert final_task.result is not None

        finally:
            shutdown_distributed_processing()

    def test_compliance_workflow(self, temp_dir):
        """Test compliance management workflow."""
        async def run_compliance_test():
            manager = ComplianceManager()

            # Perform GDPR compliance assessment
            assessment = await manager.assess_compliance(
                ComplianceStandard.GDPR,
                "Test Auditor"
            )

            assert assessment.overall_score >= 0
            assert assessment.requirements_met >= 0
            assert assessment.total_requirements > 0

            # Generate compliance report
            report = await manager.generate_compliance_report(ComplianceStandard.GDPR)
            assert "standard" in report
            assert "assessment" in report

            # Log audit event
            await manager.log_audit_event(
                action="test_compliance_check",
                user_id="test_user",
                resource="test_model.stl",
                details="Automated compliance test"
            )

            # Verify audit chain integrity
            chain_result = manager.verify_audit_chain()
            assert chain_result["valid"] is True

        # Run async test
        asyncio.run(run_compliance_test())

    def test_memory_management_workflow(self, temp_dir, sample_stl_file):
        """Test memory management during intensive operations."""
        # Initialize memory management
        get_memory_manager().start_monitoring()

        try:
            # Perform memory-intensive operations
            for i in range(5):
                # Simulate processing multiple files
                exit_code = cli_main([
                    str(sample_stl_file),
                    "--validate",
                    "--repair",
                    "--slice",
                    "--output", str(temp_dir / f"result_{i}.json")
                ])

                assert exit_code == 0

                # Check memory usage hasn't grown excessively
                stats = get_memory_manager().get_system_stats()
                # Memory usage should be reasonable (< 1GB for test)
                assert stats.process_mb < 1000

        finally:
            get_memory_manager().stop_monitoring()

    def test_progress_tracking_workflow(self, temp_dir, sample_stl_file):
        """Test progress tracking during long operations."""
        progress_manager = get_progress_manager()

        # Create a long-running task simulation
        task_id = progress_manager.create_task(
            "Test Long Operation",
            steps=["Initialize", "Process", "Validate", "Finalize"]
        )

        # Simulate progress updates
        progress_manager.update_progress(task_id, step_index=0, progress=50, message="Initializing...")
        time.sleep(0.1)

        progress_manager.update_progress(task_id, step_index=0, progress=100, message="Initialized")
        progress_manager.update_progress(task_id, step_index=1, progress=25, message="Processing...")

        # Get progress info
        progress_info = progress_manager.get_task_progress(task_id)
        assert progress_info is not None
        assert progress_info["progress"] > 0

        # Complete task
        progress_manager.complete_task(task_id, success=True)

        # Verify completion
        final_progress = progress_manager.get_task_progress(task_id)
        assert final_progress["state"] == "completed"

    def test_error_recovery_workflow(self, temp_dir):
        """Test error recovery mechanisms."""
        from src.core.error_handler import get_error_handler

        error_handler = get_error_handler()

        # Test error handling with invalid file
        invalid_file = temp_dir / "nonexistent.stl"

        try:
            cli_main([str(invalid_file), "--validate"])
            # Should fail gracefully
        except SystemExit as e:
            # Expected to exit with error code
            assert e.code != 0

        # Verify error was logged
        stats = error_handler.get_error_statistics()
        assert stats["total_errors"] > 0

    def test_configuration_management_workflow(self, temp_dir):
        """Test configuration management across operations."""
        from src.core.config import ConfigManager

        config_manager = ConfigManager(config_dir=temp_dir)

        # Test configuration loading and modification
        config = config_manager.load()
        assert config is not None

        # Modify validation settings
        config_manager.update_validation_config(
            min_wall_thickness_mm=1.0,
            min_feature_size_mm=0.5
        )

        # Reload and verify changes
        updated_config = config_manager.load()
        assert updated_config.validation.min_wall_thickness_mm == 1.0

    def test_api_compatibility_workflow(self, temp_dir, sample_stl_file):
        """Test API compatibility and response formats."""
        # Test that CLI produces consistent JSON output
        output_file = temp_dir / "api_test.json"

        exit_code = cli_main([
            str(sample_stl_file),
            "--validate",
            "--output", str(output_file),
            "--format", "json"
        ])

        assert exit_code == 0

        # Verify JSON structure matches API expectations
        with open(output_file, 'r') as f:
            result = json.load(f)

        # Should have standard API response structure
        assert "success" in result
        assert "validation" in result or result["success"] is False
        assert "mesh_info" in result

    def test_performance_under_load(self, temp_dir):
        """Test system performance under moderate load."""
        # Create multiple test files
        test_files = []
        for i in range(10):
            stl_file = temp_dir / f"test_model_{i}.stl"

            # Create slightly different content for each file
            stl_content = f"""
solid test_model_{i}
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex {i+1} 0 0
      vertex 0 1 0
    endloop
  endfacet
endsolid test_model_{i}
            """.strip()

            stl_file.write_text(stl_content)
            test_files.append(stl_file)

        start_time = time.time()

        # Process all files in batch
        output_file = temp_dir / "load_test_results.json"
        exit_code = cli_main([
            "--batch",
            "--parallel",
            "--max-workers", "4"
        ] + [str(f) for f in test_files] + [
            "--output", str(output_file)
        ])

        end_time = time.time()
        processing_time = end_time - start_time

        assert exit_code == 0
        assert processing_time < 60  # Should complete within 60 seconds

        # Verify all files were processed
        with open(output_file, 'r') as f:
            result = json.load(f)

        assert len(result["files"]) == 10

    def test_security_workflow(self, temp_dir, sample_stl_file):
        """Test security features and access controls."""
        # Test hash manifest enforcement
        manifest_file = temp_dir / "manifest.json"

        # Create hash manifest
        import hashlib
        with open(sample_stl_file, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        manifest_data = {
            "files": {
                str(sample_stl_file): file_hash
            }
        }

        with open(manifest_file, 'w') as f:
            json.dump(manifest_data, f)

        # Test processing with hash manifest
        output_file = temp_dir / "secure_result.json"
        exit_code = cli_main([
            str(sample_stl_file),
            "--hash-manifest", str(manifest_file),
            "--hash-policy", "strict",
            "--output", str(output_file)
        ])

        assert exit_code == 0

        # Verify audit logging for security events
        compliance_manager = ComplianceManager()
        asyncio.run(compliance_manager.log_audit_event(
            action="security_test",
            user_id="test_user",
            resource=str(sample_stl_file),
            details="Security workflow test"
        ))

    def test_internationalization_workflow(self, temp_dir, sample_stl_file):
        """Test internationalization and localization."""
        from src.core.i18n_optimized import set_language, t

        # Test Japanese localization
        set_language("ja")

        output_file = temp_dir / "i18n_result.json"
        exit_code = cli_main([
            str(sample_stl_file),
            "--language", "ja",
            "--validate",
            "--output", str(output_file)
        ])

        assert exit_code == 0

        # Test English
        set_language("en")
        output_file_en = temp_dir / "i18n_result_en.json"
        exit_code = cli_main([
            str(sample_stl_file),
            "--language", "en",
            "--validate",
            "--output", str(output_file_en)
        ])

        assert exit_code == 0

    def test_backup_and_recovery_workflow(self, temp_dir, sample_stl_file):
        """Test data backup and recovery capabilities."""
        # Create backup of original file
        backup_file = temp_dir / "backup.stl"
        shutil.copy2(sample_stl_file, backup_file)

        # Process and modify original
        output_file = temp_dir / "processed_result.json"
        exit_code = cli_main([
            str(sample_stl_file),
            "--repair",
            "--output", str(output_file)
        ])

        assert exit_code == 0

        # Simulate data loss and recovery
        sample_stl_file.unlink()  # Delete original
        shutil.copy2(backup_file, sample_stl_file)  # Restore from backup

        # Verify recovery
        recovery_output = temp_dir / "recovery_result.json"
        exit_code = cli_main([
            str(sample_stl_file),
            "--validate",
            "--output", str(recovery_output)
        ])

        assert exit_code == 0

    def test_cross_platform_compatibility(self, temp_dir, sample_stl_file):
        """Test cross-platform compatibility."""
        # Test different file path formats
        output_file = temp_dir / "cross_platform_result.json"

        # Use absolute path
        abs_path = sample_stl_file.resolve()
        exit_code = cli_main([
            str(abs_path),
            "--validate",
            "--output", str(output_file)
        ])

        assert exit_code == 0

        # Test with relative path
        rel_output = temp_dir / "relative_result.json"
        cwd = Path.cwd()
        try:
            import os
            os.chdir(temp_dir)
            exit_code = cli_main([
                sample_stl_file.name,
                "--validate",
                "--output", "relative_result.json"
            ])

            assert exit_code == 0
            assert (temp_dir / "relative_result.json").exists()

        finally:
            os.chdir(cwd)


class TestSystemIntegration:
    """System-wide integration tests."""

    def test_all_subsystems_integration(self, temp_dir):
        """Test that all subsystems work together correctly."""
        # This test ensures that memory management, progress tracking,
        # error handling, and compliance all work together

        sample_file = temp_dir / "integration_test.stl"
        sample_file.write_text("""
solid integration_test
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
endsolid integration_test
        """.strip())

        # Initialize all systems
        get_memory_manager().start_monitoring()
        progress_manager = get_progress_manager()

        try:
            # Create progress task
            task_id = progress_manager.create_task("Integration Test")

            # Run comprehensive workflow
            output_file = temp_dir / "integration_result.json"
            exit_code = cli_main([
                str(sample_file),
                "--validate",
                "--repair",
                "--slice",
                "--output", str(output_file),
                "--verbose"
            ])

            # Complete progress task
            progress_manager.complete_task(task_id, success=(exit_code == 0))

            assert exit_code == 0
            assert output_file.exists()

            # Verify all systems are still functional
            memory_stats = get_memory_manager().get_system_stats()
            assert memory_stats.process_mb > 0

            progress_info = progress_manager.get_task_progress(task_id)
            assert progress_info is not None

        finally:
            get_memory_manager().stop_monitoring()

    def test_scalability_under_concurrent_load(self, temp_dir):
        """Test system scalability with concurrent operations."""
        import concurrent.futures
        import threading

        # Create test files
        test_files = []
        for i in range(20):
            stl_file = temp_dir / f"concurrent_test_{i}.stl"
            stl_file.write_text(f"""
solid concurrent_test_{i}
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
endsolid concurrent_test_{i}
            """.strip())
            test_files.append(stl_file)

        results = []
        errors = []

        def process_file(file_path):
            try:
                output_file = temp_dir / f"result_{file_path.stem}.json"
                exit_code = cli_main([
                    str(file_path),
                    "--validate",
                    "--output", str(output_file)
                ])
                return exit_code == 0
            except Exception as e:
                errors.append(e)
                return False

        # Process files concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_file, f) for f in test_files[:10]]  # Test first 10
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Most operations should succeed
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.8  # At least 80% success rate
        assert len(errors) == 0

    def test_data_integrity_across_operations(self, temp_dir):
        """Test data integrity preservation across all operations."""
        # Create a test model with known characteristics
        stl_content = """
solid integrity_test
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 10 0 0
      vertex 0 10 0
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex 10 0 0
      vertex 10 10 0
      vertex 0 10 0
    endloop
  endfacet
endsolid integrity_test
        """.strip()

        original_file = temp_dir / "integrity_test.stl"
        original_file.write_text(stl_content)

        # Get original hash
        import hashlib
        with open(original_file, 'rb') as f:
            original_hash = hashlib.sha256(f.read()).hexdigest()

        # Process with repair and save
        repaired_file = temp_dir / "repaired_integrity.stl"
        output_file = temp_dir / "integrity_result.json"

        exit_code = cli_main([
            str(original_file),
            "--repair",
            "--save-repaired", str(repaired_file),
            "--output", str(output_file)
        ])

        assert exit_code == 0

        # Verify repaired file exists and has different content
        assert repaired_file.exists()

        with open(repaired_file, 'rb') as f:
            repaired_hash = hashlib.sha256(f.read()).hexdigest()

        # Hash should be different (repaired)
        assert repaired_hash != original_hash

        # Verify processing results
        with open(output_file, 'r') as f:
            result = json.load(f)

        assert result["success"] is True


class TestEnterpriseFeatures:
    """Test enterprise-grade features."""

    def test_audit_trail_completeness(self, temp_dir):
        """Test complete audit trail functionality."""
        async def run_audit_test():
            compliance_manager = ComplianceManager()

            # Perform multiple operations that should be audited
            await compliance_manager.log_audit_event(
                action="file_validation",
                user_id="enterprise_user",
                resource="enterprise_model.stl",
                details="Enterprise validation test"
            )

            await compliance_manager.log_audit_event(
                action="file_repair",
                user_id="enterprise_user",
                resource="enterprise_model.stl",
                details="Enterprise repair test"
            )

            # Verify audit chain integrity
            chain_result = compliance_manager.verify_audit_chain()
            assert chain_result["valid"] is True
            assert chain_result["entries_checked"] >= 2

        asyncio.run(run_audit_test())

    def test_encryption_key_rotation(self, temp_dir):
        """Test encryption key rotation for compliance."""
        async def run_encryption_test():
            compliance_manager = ComplianceManager()

            # Add some compliance evidence
            evidence_id = await compliance_manager.add_compliance_evidence(
                requirement_id="test_requirement",
                evidence_type="test_evidence",
                evidence_data="Test evidence data for encryption",
                assessor="Test Assessor"
            )

            assert evidence_id is not None

            # Rotate encryption key
            new_key = compliance_manager.rotate_encryption_key()

            # Verify the key was rotated
            assert new_key != compliance_manager.encryption_key

            # Verify evidence is still accessible
            evidence_list = await compliance_manager._get_requirement_evidence("test_requirement")
            assert len(evidence_list) > 0

        asyncio.run(run_encryption_test())

    def test_performance_monitoring_integration(self, temp_dir):
        """Test integration of performance monitoring across systems."""
        # Initialize all monitoring systems
        memory_manager = get_memory_manager()
        memory_manager.start_monitoring()

        progress_manager = get_progress_manager()

        try:
            # Create performance test file
            large_stl_file = temp_dir / "performance_test.stl"

            # Generate larger STL content
            stl_faces = []
            for i in range(1000):  # 1000 faces for performance testing
                stl_faces.append(f"""
  facet normal 0 0 1
    outer loop
      vertex {i % 100} {i // 100} 0
      vertex {(i + 1) % 100} {i // 100} 0
      vertex {i % 100} {(i // 100) + 1} 0
    endloop
  endfacet
                """.strip())

            stl_content = f"""
solid performance_test
{chr(10).join(stl_faces)}
endsolid performance_test
            """.strip()

            large_stl_file.write_text(stl_content)

            # Create progress task
            task_id = progress_manager.create_task("Performance Test")

            # Process large file
            output_file = temp_dir / "performance_result.json"
            start_time = time.time()

            exit_code = cli_main([
                str(large_stl_file),
                "--validate",
                "--repair",
                "--output", str(output_file)
            ])

            processing_time = time.time() - start_time

            # Complete progress task
            progress_manager.complete_task(task_id, success=(exit_code == 0))

            assert exit_code == 0
            assert processing_time < 30  # Should complete within 30 seconds

            # Verify memory usage stayed reasonable
            stats = memory_manager.get_system_stats()
            assert stats.process_mb < 500  # Should use less than 500MB

        finally:
            memory_manager.stop_monitoring()


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
