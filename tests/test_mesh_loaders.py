"""Unit tests for mesh loading adapters."""
from pathlib import Path
import tempfile

import numpy as np
import pytest
import trimesh

from src.adapters import (
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
    assert len(registry.loaders) >= 3  # At least STL, OBJ, PLY





def test_mesh_loader_registry_load_nonexistent():
    """Test loading non-existent file through registry."""
    registry = MeshLoaderRegistry()

    with pytest.raises(MeshLoadError, match="File not found"):
        registry.load("nonexistent.stl")



def test_mesh_loader_registry_get_supported_formats():
    """Test getting supported formats from registry."""
    registry = MeshLoaderRegistry()
    formats = registry.supported_extensions

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




