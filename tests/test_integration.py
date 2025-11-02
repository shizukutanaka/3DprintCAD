"""Integration tests for the 3D Print CAD Assistant."""
import pytest
import tempfile
import json
from pathlib import Path
import numpy as np
import trimesh

from src.adapters import load_mesh
from src.core.analysis import mesh_validator
from src.core.analysis.mesh_repair import repair_mesh
from src.core.recommendation import RecommendationEngine
from src.core.cache import MemoryCache, FileCache
from src.core.validators import PathValidator, NumericValidator, PrintSettingsValidator
from src.core.progress import ProgressTracker, track_progress
from src.cli_optimized import CLIProcessor


class TestMeshProcessingPipeline:
    """Test complete mesh processing pipeline."""

    @pytest.fixture
    def sample_mesh(self):
        """Create a sample mesh for testing."""
        vertices = np.array([
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1]
        ])
        faces = np.array([
            [0, 1, 2], [0, 2, 3],  # Bottom
            [4, 7, 6], [4, 6, 5],  # Top
            [0, 4, 5], [0, 5, 1],  # Front
            [2, 6, 7], [2, 7, 3],  # Back
            [0, 3, 7], [0, 7, 4],  # Left
            [1, 5, 6], [1, 6, 2]   # Right
        ])
        return trimesh.Trimesh(vertices=vertices, faces=faces)

    @pytest.fixture
    def temp_stl_file(self, sample_mesh):
        """Create a temporary STL file."""
        with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as f:
            sample_mesh.export(f.name)
            yield Path(f.name)
        Path(f.name).unlink(missing_ok=True)

    def test_full_pipeline(self, temp_stl_file):
        """Test complete processing pipeline."""
        # Load mesh
        mesh = load_mesh(temp_stl_file)
        assert mesh is not None
        assert mesh.vertices.shape[0] > 0

        # Validate mesh
        settings = mesh_validator.MeshValidationSettings()
        validation = mesh_validator.validate_mesh(mesh, settings=settings)
        assert validation.mesh_stats.vertex_count > 0
        assert validation.mesh_stats.face_count > 0

        # Generate recommendations
        recommender = RecommendationEngine()
        recommendations = recommender.generate_recommendations(validation)
        assert recommendations is not None

        # Repair if needed
        if validation.has_issues:
            repaired = repair_mesh(mesh, aggressive=False)
            if repaired:
                # Re-validate
                validation2 = mesh_validator.validate_mesh(repaired, settings=settings)
                assert validation2 is not None

    def test_batch_processing(self, temp_stl_file):
        """Test batch processing functionality."""
        import argparse

        args = argparse.Namespace(
            validate=True,
            repair=False,
            slice=False,
            gcode=False,
            output=None,
            quiet=True,
            verbose=False,
            no_progress=True,
            parallel=False,
            workers=1,
            min_wall=0.8,
            min_feature=0.4,
            overhang=60
        )

        processor = CLIProcessor()
        files = [temp_stl_file]
        results = processor.process_batch(files, args)

        assert len(results) == 1
        assert results[0]['success']
        assert 'validation' in results[0]

    def test_parallel_batch(self, temp_stl_file):
        """Test parallel batch processing."""
        import argparse

        args = argparse.Namespace(
            validate=True,
            repair=False,
            slice=False,
            gcode=False,
            output=None,
            quiet=True,
            verbose=False,
            no_progress=True,
            parallel=True,
            workers=2,
            min_wall=0.8,
            min_feature=0.4,
            overhang=60
        )

        processor = CLIProcessor()
        # Process same file multiple times to test parallelism
        files = [temp_stl_file, temp_stl_file]
        results = processor.process_batch(files, args)

        assert len(results) == 2
        assert all(r['success'] for r in results)


class TestValidators:
    """Test input validators."""

    def test_path_validator(self):
        """Test path validation."""
        # Valid paths
        path = PathValidator.validate_path("test.stl")
        assert path.name == "test.stl"

        # Invalid paths
        with pytest.raises(Exception):
            PathValidator.validate_path("../../../etc/passwd")

        # Filename sanitization
        sanitized = PathValidator.validate_filename("test<>file.stl")
        assert "<" not in sanitized
        assert ">" not in sanitized

    def test_numeric_validator(self):
        """Test numeric validation."""
        # Positive values
        val = NumericValidator.validate_positive(5.0)
        assert val == 5.0

        with pytest.raises(ValueError):
            NumericValidator.validate_positive(-1.0)

        # Range validation
        val = NumericValidator.validate_range(50, 0, 100)
        assert val == 50

        with pytest.raises(ValueError):
            NumericValidator.validate_range(150, 0, 100)

        # Percentage
        val = NumericValidator.validate_percentage(75)
        assert val == 75

        with pytest.raises(ValueError):
            NumericValidator.validate_percentage(150)

    def test_print_settings_validator(self):
        """Test print settings validation."""
        # Layer height
        height = PrintSettingsValidator.validate_layer_height(0.2, 0.4)
        assert height == 0.2

        with pytest.raises(ValueError):
            PrintSettingsValidator.validate_layer_height(0.5, 0.4)

        # Temperature
        temp = PrintSettingsValidator.validate_temperature(210, "PLA")
        assert temp == 210

        with pytest.raises(ValueError):
            PrintSettingsValidator.validate_temperature(300, "PLA")

        # Speed
        speed = PrintSettingsValidator.validate_speed(60, "normal")
        assert speed == 60

        with pytest.raises(ValueError):
            PrintSettingsValidator.validate_speed(200, "normal")


class TestCaching:
    """Test caching functionality."""

    def test_memory_cache(self):
        """Test memory cache operations."""
        cache = MemoryCache(max_size=10, default_ttl=60)

        # Set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Non-existent key
        assert cache.get("nonexistent") is None

        # Delete
        assert cache.delete("key1")
        assert cache.get("key1") is None

        # Statistics
        stats = cache.get_stats()
        assert stats["hit_count"] >= 0
        assert stats["miss_count"] >= 0

    def test_file_cache(self):
        """Test file cache operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = FileCache(Path(tmpdir))

            # Set and get
            cache.set("key1", {"data": "value1"})
            assert cache.get("key1") == {"data": "value1"}

            # Non-existent key
            assert cache.get("nonexistent") is None

            # Delete
            assert cache.delete("key1")
            assert cache.get("key1") is None

            # Clear
            cache.set("key2", "value2")
            cache.set("key3", "value3")
            cache.clear()
            assert cache.get("key2") is None
            assert cache.get("key3") is None


class TestProgress:
    """Test progress tracking."""

    def test_progress_tracker(self):
        """Test progress tracker functionality."""
        tracker = ProgressTracker()

        # Create task
        task = tracker.create_task(
            "test_task",
            "Test Task",
            ["Step 1", "Step 2", "Step 3"]
        )

        assert task.task_id == "test_task"
        assert len(task.steps) == 3
        assert task.get_progress() == 0.0

        # Start task
        tracker.start_task("test_task")
        assert task.state.value == "running"

        # Update steps
        tracker.update_step("test_task", 0, 50, "Halfway")
        assert task.steps[0].progress == 50

        # Complete step
        tracker.complete_step("test_task", 0)
        assert task.steps[0].state.value == "completed"
        assert task.current_step == 1

        # Get task
        retrieved = tracker.get_task("test_task")
        assert retrieved is not None
        assert retrieved.task_id == "test_task"

        # Cleanup
        tracker.shutdown()

    def test_progress_context(self):
        """Test progress context manager."""
        with track_progress(
            "context_task",
            "Context Task",
            ["Setup", "Process", "Cleanup"]
        ) as progress:
            progress.update(25, "Setting up")
            progress.next_step()

            progress.update(50, "Processing")
            progress.next_step()

            progress.update(100, "Cleaning up")

        tracker = ProgressTracker()
        task = tracker.get_task("context_task")

        # Task should be completed
        if task:
            assert task.state.value == "completed"

        tracker.shutdown()


class TestI18n:
    """Test internationalization."""

    def test_translations(self):
        """Test translation system."""
        from src.core.i18n_manager import get_i18n_manager, Language

        i18n = get_i18n_manager()

        # English
        i18n.set_language(Language.EN)
        assert i18n.t("ui.upload") == "Upload File"

        # Japanese
        i18n.set_language(Language.JA)
        assert i18n.t("ui.upload") == "ファイルをアップロード"

        # With parameters
        i18n.set_language(Language.EN)
        text = i18n.t("file.size_limit", size=100)
        assert "100" in text

        # Missing key
        assert i18n.t("nonexistent.key") == "nonexistent.key"


class TestWebAPI:
    """Test Web API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.web import create_app
        app = create_app('testing')
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
        assert data['status'] == 'ok'

    def test_formats_endpoint(self, client):
        """Test supported formats endpoint."""
        response = client.get('/api/formats')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'formats' in data
        assert len(data['formats']) > 0

    def test_upload_validation(self, client, sample_mesh):
        """Test file upload validation."""
        # Create temporary STL file
        with tempfile.NamedTemporaryFile(suffix='.stl') as f:
            sample_mesh.export(f.name)
            f.seek(0)

            # Test upload
            data = {'file': (f, 'test.stl')}
            response = client.post(
                '/api/upload',
                data=data,
                content_type='multipart/form-data'
            )

            if response.status_code == 200:
                result = json.loads(response.data)
                assert 'file_id' in result
                assert 'filename' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])