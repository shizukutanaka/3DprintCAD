"""Unit tests for mesh loading adapters."""
from pathlib import Path
import tempfile

import numpy as np
import pytest
import trimesh

from src.adapters.mesh_loaders import (
    MeshLoadError,
    STLLoader,
    OBJLoader,
    PLYLoader,
    MeshLoaderRegistry,
    load_mesh,
    get_supported_formats
)


@pytest.fixture
def temp_stl_file():
    """Create a temporary STL file for testing."""
    mesh = trimesh.creation.box(extents=[10.0, 10.0, 10.0])

    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as f:
        mesh.export(f.name)
        yield Path(f.name)

    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def temp_obj_file():
    """Create a temporary OBJ file for testing."""
    mesh = trimesh.creation.box(extents=[5.0, 5.0, 5.0])

    with tempfile.NamedTemporaryFile(suffix='.obj', delete=False) as f:
        mesh.export(f.name)
        yield Path(f.name)

    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def temp_invalid_file():
    """Create a temporary invalid file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as f:
        f.write(b"invalid content")
        yield Path(f.name)

    Path(f.name).unlink(missing_ok=True)


def test_stl_loader_initialization():
    """Test STL loader initialization."""
    loader = STLLoader()
    assert loader.supported_extensions == ['.stl', '.STL']


def test_stl_loader_can_load():
    """Test STL loader can_load method."""
    loader = STLLoader()

    assert loader.can_load(Path("test.stl"))
    assert loader.can_load(Path("test.STL"))
    assert not loader.can_load(Path("test.obj"))
    assert not loader.can_load(Path("test.ply"))


def test_stl_loader_load_valid_file(temp_stl_file):
    """Test STL loader loading valid file."""
    loader = STLLoader()
    mesh = loader.load(temp_stl_file)

    assert isinstance(mesh, trimesh.Trimesh)
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0


def test_stl_loader_load_nonexistent_file():
    """Test STL loader with non-existent file."""
    loader = STLLoader()

    with pytest.raises(MeshLoadError):
        loader.load(Path("nonexistent.stl"))


def test_stl_loader_load_invalid_content(temp_invalid_file):
    """Test STL loader with invalid content."""
    loader = STLLoader()

    with pytest.raises(MeshLoadError):
        loader.load(temp_invalid_file)


def test_obj_loader_initialization():
    """Test OBJ loader initialization."""
    loader = OBJLoader()
    assert loader.supported_extensions == ['.obj', '.OBJ']


def test_obj_loader_can_load():
    """Test OBJ loader can_load method."""
    loader = OBJLoader()

    assert loader.can_load(Path("test.obj"))
    assert loader.can_load(Path("test.OBJ"))
    assert not loader.can_load(Path("test.stl"))
    assert not loader.can_load(Path("test.ply"))


def test_obj_loader_load_valid_file(temp_obj_file):
    """Test OBJ loader loading valid file."""
    loader = OBJLoader()
    mesh = loader.load(temp_obj_file)

    assert isinstance(mesh, trimesh.Trimesh)
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert 'has_materials' in mesh.metadata


def test_obj_loader_extract_material_info():
    """Test OBJ loader material extraction."""
    loader = OBJLoader()

    # Test with None visual
    info = loader._extract_material_info(None)
    assert isinstance(info, dict)

    # Test with mock visual object
    class MockVisual:
        def __init__(self):
            self.material = None
            self.uv = None
            self.face_materials = None

    visual = MockVisual()
    info = loader._extract_material_info(visual)
    assert 'has_uv_mapping' in info
    assert 'has_face_materials' in info


def test_ply_loader_initialization():
    """Test PLY loader initialization."""
    loader = PLYLoader()
    assert loader.supported_extensions == ['.ply', '.PLY']


def test_ply_loader_can_load():
    """Test PLY loader can_load method."""
    loader = PLYLoader()

    assert loader.can_load(Path("test.ply"))
    assert loader.can_load(Path("test.PLY"))
    assert not loader.can_load(Path("test.stl"))
    assert not loader.can_load(Path("test.obj"))


def test_mesh_loader_registry_initialization():
    """Test MeshLoaderRegistry initialization."""
    registry = MeshLoaderRegistry()
    assert len(registry._loaders) >= 3  # At least STL, OBJ, PLY


def test_mesh_loader_registry_get_loader():
    """Test getting appropriate loader from registry."""
    registry = MeshLoaderRegistry()

    stl_loader = registry.get_loader(Path("test.stl"))
    assert isinstance(stl_loader, STLLoader)

    obj_loader = registry.get_loader(Path("test.obj"))
    assert isinstance(obj_loader, OBJLoader)

    ply_loader = registry.get_loader(Path("test.ply"))
    assert isinstance(ply_loader, PLYLoader)

    unknown_loader = registry.get_loader(Path("test.xyz"))
    assert unknown_loader is None


def test_mesh_loader_registry_register():
    """Test registering new loader."""
    registry = MeshLoaderRegistry()
    initial_count = len(registry._loaders)

    # Create a mock loader
    class MockLoader:
        @property
        def supported_extensions(self):
            return ['.mock']

        def can_load(self, file_path):
            return file_path.suffix.lower() == '.mock'

    mock_loader = MockLoader()
    registry.register(mock_loader)

    assert len(registry._loaders) == initial_count + 1


def test_mesh_loader_registry_load_mesh(temp_stl_file):
    """Test loading mesh through registry."""
    registry = MeshLoaderRegistry()
    mesh = registry.load_mesh(temp_stl_file)

    assert isinstance(mesh, trimesh.Trimesh)
    assert 'source_file' in mesh.metadata
    assert 'file_format' in mesh.metadata
    assert 'loader_type' in mesh.metadata


def test_mesh_loader_registry_load_nonexistent():
    """Test loading non-existent file through registry."""
    registry = MeshLoaderRegistry()

    with pytest.raises(MeshLoadError, match="File not found"):
        registry.load_mesh("nonexistent.stl")


def test_mesh_loader_registry_load_unsupported():
    """Test loading unsupported format through registry."""
    registry = MeshLoaderRegistry()

    # Create a temporary file with unsupported extension
    with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
        f.write(b"test content")
        temp_file = Path(f.name)

    try:
        with pytest.raises(MeshLoadError, match="No loader found"):
            registry.load_mesh(temp_file)
    finally:
        temp_file.unlink(missing_ok=True)


def test_mesh_loader_registry_get_supported_formats():
    """Test getting supported formats from registry."""
    registry = MeshLoaderRegistry()
    formats = registry.get_supported_formats()

    assert '.stl' in formats
    assert '.obj' in formats
    assert '.ply' in formats
    assert all(fmt.startswith('.') for fmt in formats)


def test_convenience_load_mesh_function(temp_stl_file):
    """Test convenience load_mesh function."""
    mesh = load_mesh(temp_stl_file)

    assert isinstance(mesh, trimesh.Trimesh)
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0


def test_convenience_get_supported_formats_function():
    """Test convenience get_supported_formats function."""
    formats = get_supported_formats()

    assert isinstance(formats, list)
    assert '.stl' in formats
    assert '.obj' in formats
    assert '.ply' in formats


def test_mesh_load_error():
    """Test MeshLoadError exception."""
    error = MeshLoadError("Test error message")
    assert str(error) == "Test error message"


def test_stl_loader_scene_handling():
    """Test STL loader handling of Scene objects."""
    # Create a mesh that might be loaded as a Scene
    mesh = trimesh.creation.box(extents=[10.0, 10.0, 10.0])

    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as f:
        # Export and reload to ensure we get consistent behavior
        mesh.export(f.name)
        temp_file = Path(f.name)

    try:
        loader = STLLoader()
        loaded_mesh = loader.load(temp_file)

        assert isinstance(loaded_mesh, trimesh.Trimesh)
        assert len(loaded_mesh.vertices) > 0
    finally:
        temp_file.unlink(missing_ok=True)


def test_obj_loader_combine_with_materials():
    """Test OBJ loader material combination."""
    loader = OBJLoader()

    # Create test geometries with metadata
    geom1 = trimesh.creation.box(extents=[1, 1, 1])
    geom1.metadata['material_info'] = {'has_material': True, 'material_name': 'mat1'}

    geom2 = trimesh.creation.box(extents=[2, 2, 2])
    geom2.metadata['material_info'] = {'has_material': True, 'material_name': 'mat2'}

    combined = loader._combine_with_materials([geom1, geom2])

    assert 'material_info' in combined.metadata
    assert 'combined_materials' in combined.metadata['material_info']


def test_mesh_metadata_preservation(temp_stl_file):
    """Test that mesh metadata is properly set during loading."""
    mesh = load_mesh(temp_stl_file)

    assert 'source_file' in mesh.metadata
    assert 'file_format' in mesh.metadata
    assert 'loader_type' in mesh.metadata

    assert str(temp_stl_file.resolve()) == mesh.metadata['source_file']
    assert mesh.metadata['file_format'] == '.stl'
    assert 'STLLoader' in mesh.metadata['loader_type']


def test_case_insensitive_extensions():
    """Test that file extension matching is case insensitive."""
    registry = MeshLoaderRegistry()

    # Test various cases
    assert registry.get_loader(Path("test.STL")) is not None
    assert registry.get_loader(Path("test.stl")) is not None
    assert registry.get_loader(Path("test.OBJ")) is not None
    assert registry.get_loader(Path("test.obj")) is not None