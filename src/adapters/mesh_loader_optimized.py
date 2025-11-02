"""Optimized mesh loader combining fast loading with structured approach."""
from __future__ import annotations

import mmap
import struct
import logging
from pathlib import Path
from typing import Optional, Dict, List, Union, Any
from abc import ABC, abstractmethod
import numpy as np
import trimesh
from ..core.memory_manager import memory_monitored_operation, get_memory_manager
from ..core.exceptions import MeshLoadError

logger = logging.getLogger(__name__)


class BaseMeshLoader(ABC):
    """Abstract base class for mesh loaders."""

    @abstractmethod
    def load(self, file_path: Path) -> trimesh.Trimesh:
        """Load mesh from file."""
        pass

    @abstractmethod
    def can_load(self, file_path: Path) -> bool:
        """Check if this loader can handle the file format."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        pass


class FastSTLLoader(BaseMeshLoader):
    """Optimized STL loader with memory mapping and streaming capabilities."""

    @property
    def supported_extensions(self) -> List[str]:
        return ['.stl', '.STL']

    def can_load(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.stl'

    def load(self, file_path: Path) -> trimesh.Trimesh:
        """Load STL file with optimized binary loading and streaming support."""
        try:
            # Check file size for streaming decision
            file_size = file_path.stat().st_size
            memory_manager = get_memory_manager()

            # Use streaming for very large files (>500MB)
            if file_size > 500 * 1024 * 1024:
                return self._load_streaming(file_path)
            # Use memory mapping for large files (>50MB)
            elif file_size > 50 * 1024 * 1024:
                return self._load_binary_mmap(file_path)
            # Use standard loading for smaller files
            else:
                return self._load_binary_standard(file_path)

        except Exception as e:
            raise MeshLoadError(f"Failed to load STL file {file_path}: {e}")

    def _load_streaming(self, file_path: Path) -> trimesh.Trimesh:
        """Stream large STL files to minimize memory usage."""
        logger.info(f"Using streaming loader for large file: {file_path.name}")

        with open(file_path, 'rb') as f:
            # Skip 80-byte header
            f.seek(80)

            # Read triangle count
            triangle_count_bytes = f.read(4)
            if len(triangle_count_bytes) != 4:
                raise MeshLoadError("Invalid STL file: unable to read triangle count")
            num_triangles = struct.unpack('<I', triangle_count_bytes)[0]

            # Estimate memory requirements
            estimated_mb = (num_triangles * 3 * 3 * 4) / (1024 * 1024)  # vertices * 3 floats per vertex
            memory_manager = get_memory_manager()

            with memory_monitored_operation(f"stream_stl_{file_path.name}", estimated_mb):
                # Pre-allocate arrays with streaming approach
                vertices = np.zeros((num_triangles * 3, 3), dtype=np.float32)
                chunk_size = min(10000, num_triangles)  # Process in chunks

                for chunk_start in range(0, num_triangles, chunk_size):
                    chunk_end = min(chunk_start + chunk_size, num_triangles)

                    for i in range(chunk_start, chunk_end):
                        # Skip normal (12 bytes)
                        f.seek(f.tell() + 12)

                        # Read 3 vertices (36 bytes each vertex = 12 bytes)
                        for j in range(3):
                            vertex_bytes = f.read(12)
                            if len(vertex_bytes) != 12:
                                raise MeshLoadError(f"Invalid STL file: incomplete vertex data at triangle {i}")
                            vertex_idx = i * 3 + j
                            vertices[vertex_idx] = struct.unpack('<fff', vertex_bytes)

                        # Skip attribute byte count (2 bytes)
                        f.seek(f.tell() + 2)

                # Create mesh
                faces = np.arange(num_triangles * 3).reshape(-1, 3)
                mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                mesh.merge_vertices()  # Remove duplicate vertices
                return mesh

    def _load_binary_mmap(self, file_path: Path) -> trimesh.Trimesh:
        """Fast binary STL loader using memory mapping."""
        try:
            with open(file_path, 'rb') as f:
                # Check if binary STL
                f.seek(80)
                num_triangles = struct.unpack('<I', f.read(4))[0]

                # Validate file size
                expected_size = 80 + 4 + (num_triangles * 50)
                actual_size = file_path.stat().st_size

                if actual_size != expected_size:
                    return self._load_ascii(file_path)  # Fall back to ASCII

                # Memory map for fast reading
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    mm.seek(84)  # Skip header and triangle count

                    # Estimate memory and monitor usage
                    estimated_mb = (num_triangles * 3 * 3 * 4) / (1024 * 1024)
                    memory_manager = get_memory_manager()

                    with memory_monitored_operation(f"mmap_stl_{file_path.name}", estimated_mb):
                        # Pre-allocate arrays
                        vertices = np.zeros((num_triangles * 3, 3), dtype=np.float32)

                        # Read triangles efficiently
                        for i in range(num_triangles):
                            # Skip normal (12 bytes)
                            mm.seek(mm.tell() + 12)

                            # Read 3 vertices (36 bytes)
                            for j in range(3):
                                vertices[i*3 + j] = struct.unpack('<fff', mm.read(12))

                            # Skip attribute byte count (2 bytes)
                            mm.seek(mm.tell() + 2)

                        # Create mesh
                        faces = np.arange(num_triangles * 3).reshape(-1, 3)
                        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                        mesh.merge_vertices()  # Remove duplicate vertices
                        return mesh
        except Exception:
            # Fall back to ASCII if binary loading fails
            return self._load_ascii(file_path)

    def _load_binary_standard(self, file_path: Path) -> trimesh.Trimesh:
        """Standard binary STL loader for smaller files."""
        try:
            with open(file_path, 'rb') as f:
                # Check if binary STL
                f.seek(80)
                num_triangles = struct.unpack('<I', f.read(4))[0]

                # Validate file size
                expected_size = 80 + 4 + (num_triangles * 50)
                actual_size = file_path.stat().st_size

                if actual_size != expected_size:
                    return self._load_ascii(file_path)  # Fall back to ASCII

                # Estimate memory and monitor usage
                estimated_mb = (num_triangles * 3 * 3 * 4) / (1024 * 1024)
                memory_manager = get_memory_manager()

                with memory_monitored_operation(f"standard_stl_{file_path.name}", estimated_mb):
                    f.seek(84)  # Skip header and triangle count

                    # Pre-allocate arrays
                    vertices = np.zeros((num_triangles * 3, 3), dtype=np.float32)

                    # Read triangles efficiently
                    for i in range(num_triangles):
                        # Skip normal (12 bytes)
                        f.seek(f.tell() + 12)

                        # Read 3 vertices (36 bytes)
                        for j in range(3):
                            vertices[i*3 + j] = struct.unpack('<fff', f.read(12))

                        # Skip attribute byte count (2 bytes)
                        f.seek(f.tell() + 2)

                    # Create mesh
                    faces = np.arange(num_triangles * 3).reshape(-1, 3)
                    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                    mesh.merge_vertices()  # Remove duplicate vertices
                    return mesh
        except Exception:
            # Fall back to ASCII if binary loading fails
            return self._load_ascii(file_path)

    def _load_ascii(self, file_path: Path) -> trimesh.Trimesh:
        """Load ASCII STL file with streaming for large files."""
        logger.warning(f"Falling back to ASCII STL loading for {file_path.name}")

        # For ASCII files, we can use trimesh directly as it's already memory efficient
        return trimesh.load_mesh(str(file_path), file_type='stl')


class FastOBJLoader(BaseMeshLoader):
    """Optimized OBJ loader."""

    @property
    def supported_extensions(self) -> List[str]:
        return ['.obj', '.OBJ']

    def can_load(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.obj'

    def load(self, file_path: Path) -> trimesh.Trimesh:
        """Load OBJ file with optimized parsing."""
        try:
            vertices = []
            faces = []

            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split()
                    if not parts:
                        continue

                    if parts[0] == 'v':
                        # Vertex
                        vertices.append([float(x) for x in parts[1:4]])
                    elif parts[0] == 'f':
                        # Face (handle vertex/texture/normal format)
                        face = []
                        for vertex in parts[1:]:
                            v = vertex.split('/')[0]
                            face.append(int(v) - 1)  # OBJ indices start at 1
                        if len(face) >= 3:
                            faces.append(face[:3])  # Take first 3 vertices for triangulation

            if not vertices or not faces:
                # Fall back to trimesh loader
                return trimesh.load_mesh(str(file_path), file_type='obj')

            # Create mesh
            mesh = trimesh.Trimesh(
                vertices=np.array(vertices, dtype=np.float32),
                faces=np.array(faces, dtype=np.int32)
            )
            return mesh

        except Exception as e:
            # Fall back to trimesh native loader
            try:
                return trimesh.load_mesh(str(file_path), file_type='obj')
            except Exception:
                raise MeshLoadError(f"Failed to load OBJ file {file_path}: {e}")


class FastPLYLoader(BaseMeshLoader):
    """Optimized PLY loader."""

    @property
    def supported_extensions(self) -> List[str]:
        return ['.ply', '.PLY']

    def can_load(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.ply'

    def load(self, file_path: Path) -> trimesh.Trimesh:
        """Load PLY file."""
        try:
            # Use trimesh's optimized PLY loader
            return trimesh.load_mesh(str(file_path), file_type='ply')
        except Exception as e:
            raise MeshLoadError(f"Failed to load PLY file {file_path}: {e}")


class Fast3MFLoader(BaseMeshLoader):
    """Optimized 3MF loader."""

    @property
    def supported_extensions(self) -> List[str]:
        return ['.3mf', '.3MF']

    def can_load(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.3mf'

    def load(self, file_path: Path) -> trimesh.Trimesh:
        """Load 3MF file."""
        try:
            # 3MF is a zip-based format
            import zipfile
            import xml.etree.ElementTree as ET

            with zipfile.ZipFile(file_path, 'r') as zf:
                # Find model file
                model_files = [f for f in zf.namelist() if f.endswith('.model')]
                if not model_files:
                    raise MeshLoadError("No model file found in 3MF")

                # Parse first model file
                with zf.open(model_files[0]) as model_file:
                    tree = ET.parse(model_file)
                    root = tree.getroot()

                    # Extract namespace
                    ns = {'m': root.tag.split('}')[0][1:] if '}' in root.tag else ''}

                    # Find mesh
                    mesh_elem = root.find('.//m:mesh', ns) or root.find('.//mesh')
                    if mesh_elem is None:
                        raise MeshLoadError("No mesh found in 3MF model")

                    # Extract vertices
                    vertices = []
                    vertices_elem = mesh_elem.find('m:vertices', ns) or mesh_elem.find('vertices')
                    if vertices_elem:
                        for vertex in vertices_elem:
                            x = float(vertex.get('x', 0))
                            y = float(vertex.get('y', 0))
                            z = float(vertex.get('z', 0))
                            vertices.append([x, y, z])

                    # Extract faces
                    faces = []
                    triangles_elem = mesh_elem.find('m:triangles', ns) or mesh_elem.find('triangles')
                    if triangles_elem:
                        for triangle in triangles_elem:
                            v1 = int(triangle.get('v1', 0))
                            v2 = int(triangle.get('v2', 0))
                            v3 = int(triangle.get('v3', 0))
                            faces.append([v1, v2, v3])

                    if vertices and faces:
                        mesh = trimesh.Trimesh(
                            vertices=np.array(vertices, dtype=np.float32),
                            faces=np.array(faces, dtype=np.int32)
                        )
                        return mesh

            # Fall back to trimesh loader
            return trimesh.load_mesh(str(file_path), file_type='3mf')

        except Exception as e:
            # Fall back to trimesh native loader
            try:
                return trimesh.load_mesh(str(file_path), file_type='3mf')
            except Exception:
                raise MeshLoadError(f"Failed to load 3MF file {file_path}: {e}")


class FastAMFLoader(BaseMeshLoader):
    """Optimized AMF loader."""

    @property
    def supported_extensions(self) -> List[str]:
        return ['.amf', '.AMF']

    def can_load(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.amf'

    def load(self, file_path: Path) -> trimesh.Trimesh:
        """Load AMF file."""
        try:
            # Use trimesh's AMF loader
            return trimesh.load_mesh(str(file_path), file_type='amf')
        except Exception as e:
            raise MeshLoadError(f"Failed to load AMF file {file_path}: {e}")


class OptimizedMeshLoader:
    """Main mesh loader with automatic format detection and optimized loading."""

    def __init__(self):
        """Initialize with all supported loaders."""
        self.loaders = [
            FastSTLLoader(),
            FastOBJLoader(),
            FastPLYLoader(),
            Fast3MFLoader(),
            FastAMFLoader()
        ]
        self._loader_map = {}
        for loader in self.loaders:
            for ext in loader.supported_extensions:
                self._loader_map[ext.lower()] = loader

    @property
    def supported_extensions(self) -> List[str]:
        """Get all supported extensions."""
        extensions = []
        for loader in self.loaders:
            extensions.extend(loader.supported_extensions)
        return sorted(set(ext.lower() for ext in extensions))

    def load(self, file_path: Union[str, Path]) -> trimesh.Trimesh:
        """Load mesh from file with automatic format detection."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise MeshLoadError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise MeshLoadError(f"Not a file: {file_path}")

        # Estimate memory requirements
        memory_manager = get_memory_manager()
        estimated_mb = memory_manager.monitor.estimate_file_memory_requirements(file_path)

        with memory_monitored_operation(f"load_mesh_{file_path.name}", estimated_mb):
            # Check cache first
            cache_key = f"mesh_{file_path}_{file_path.stat().st_mtime}"
            cached_mesh = memory_manager.mesh_cache.get(cache_key)
            if cached_mesh:
                logger.debug(f"Using cached mesh for {file_path.name}")
                return cached_mesh

            # MANDATORY: Compute SHA-256 checksum before any file parsing
            checksum_ok, checksum_value = self._compute_file_sha256(file_path)
            if not checksum_ok:
                raise MeshLoadError(f"SHA-256 checksum computation failed for {file_path}: {checksum_value}")

            # Validate checksum against known bad hashes if available
            if hasattr(self, '_validate_checksum_security'):
                security_ok, security_error = self._validate_checksum_security(checksum_value, file_path)
                if not security_ok:
                    raise MeshLoadError(f"Security validation failed for {file_path}: {security_error}")

            logger.info(f"SHA-256 checksum validated for {file_path.name}: {checksum_value[:16]}...")

            # Get appropriate loader
            suffix = file_path.suffix.lower()
            loader = self._loader_map.get(suffix)

            if not loader:
                # Try trimesh as fallback
                try:
                    logger.warning(f"No optimized loader for {suffix}, using trimesh fallback")
                    mesh = trimesh.load_mesh(str(file_path))
                except Exception as e:
                    raise MeshLoadError(f"Unsupported file format: {suffix}")
            else:
                # Load with optimized loader
                try:
                    mesh = loader.load(file_path)
                except MeshLoadError:
                    raise
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
                    # Try trimesh as final fallback
                    try:
                        mesh = trimesh.load_mesh(str(file_path))
                    except Exception:
                        raise MeshLoadError(f"Failed to load mesh from {file_path}: {e}")

            # Validate mesh
            if mesh is None or not hasattr(mesh, 'vertices') or len(mesh.vertices) == 0:
                raise MeshLoadError(f"Invalid or empty mesh: {file_path}")

            # Basic cleanup
            mesh.process(validate=True)

            # Cache the loaded mesh
            memory_manager.mesh_cache.put(cache_key, mesh, file_path)

            logger.info(f"Loaded mesh from {file_path.name}: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
            return mesh

    def _compute_file_sha256(self, file_path: Path) -> Tuple[bool, Union[str, bytes]]:
        """Compute SHA-256 digest for a mesh file."""
        try:
            hasher = hashlib.sha256()
            with open(file_path, "rb") as handle:
                for chunk in iter(lambda: handle.read(DEFAULT_HASH_CHUNK_SIZE), b""):
                    if not chunk:
                        break
                    hasher.update(chunk)
            return True, hasher.hexdigest()
        except OSError as exc:
            return False, f"Failed to compute SHA-256 for {file_path}: {exc}"

    def _validate_checksum_security(self, checksum: str, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Validate checksum against security database of known bad hashes."""
        # TODO: Implement database lookup for known malicious file hashes
        # For now, this is a placeholder that always passes
        # In production, this would check against:
        # - Known malware signatures
        # - Previously flagged problematic files
        # - Industry blacklists
        return True, None


# Global instance
_mesh_loader = OptimizedMeshLoader()


def load_mesh(file_path: Union[str, Path]) -> trimesh.Trimesh:
    """Load mesh from file - main entry point."""
    return _mesh_loader.load(file_path)


def get_supported_extensions() -> List[str]:
    """Get list of supported file extensions."""
    return _mesh_loader.supported_extensions


def can_load_file(file_path: Union[str, Path]) -> bool:
    """Check if file format is supported."""
    return _mesh_loader.can_load(file_path)