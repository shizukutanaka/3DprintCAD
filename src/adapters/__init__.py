"""Input/output adapters for file formats and external systems."""

from .mesh_loader_optimized import (
    MeshLoadError,
    load_mesh,
    get_supported_extensions,
    can_load_file,
)

# Legacy compatibility
from .mesh_loader_optimized import (
    BaseMeshLoader as MeshLoader,
    FastSTLLoader as STLLoader,
    FastOBJLoader as OBJLoader,
    FastPLYLoader as PLYLoader,
    OptimizedMeshLoader as MeshLoaderRegistry,
)

def get_supported_formats():
    """Legacy compatibility for get_supported_formats."""
    return get_supported_extensions()

__all__ = [
    "MeshLoadError",
    "MeshLoader",
    "STLLoader",
    "OBJLoader",
    "PLYLoader",
    "MeshLoaderRegistry",
    "load_mesh",
    "get_supported_formats",
    "get_supported_extensions",
    "can_load_file",
]
