"""Streaming STL loader for processing large files without loading entire file into memory."""

import struct
import logging
from pathlib import Path
from typing import Iterator, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np

from .watchdog_timer import watchdog_timeout, calculate_timeout_for_file_size
from .error_recovery import error_recovery_manager, OperationType


@dataclass
class STLHeader:
    """STL file header information."""
    name: str
    triangle_count: int
    file_size: int


@dataclass
class STLTriangle:
    """Represents a single triangle in an STL file."""
    normal: Tuple[float, float, float]
    vertices: Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]
    attribute_byte_count: int


class StreamingSTLLoader:
    """Streaming loader for STL files that processes large files without loading entirely into memory."""

    def __init__(self, chunk_size: int = 1024 * 1024):  # 1MB chunks
        """Initialize the streaming STL loader.

        Args:
            chunk_size: Size of chunks to read from file
        """
        self.logger = logging.getLogger(__name__)
        self.chunk_size = chunk_size

    def load_stl_header(self, file_path: Path) -> STLHeader:
        """Load and parse STL file header.

        Args:
            file_path: Path to STL file

        Returns:
            STL header information

        Raises:
            ValueError: If file is not a valid STL file
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"STL file not found: {file_path}")

        file_size = file_path.stat().st_size

        with open(file_path, 'rb') as f:
            # Read 80-byte header
            header_data = f.read(80)

            if len(header_data) < 80:
                raise ValueError("Invalid STL file: header too short")

            # Parse header (first 80 bytes)
            # Try to extract triangle count from bytes 80-84 (little endian)
            if len(header_data) >= 84:
                triangle_count_bytes = header_data[80:84]
                triangle_count = struct.unpack('<I', triangle_count_bytes)[0]
            else:
                # Estimate triangle count from file size if header is malformed
                # Each triangle is approximately 50 bytes in binary STL
                triangle_count = file_size // 50

            # Extract name from header (null-terminated string)
            header_name = header_data[:80].decode('ascii', errors='ignore').rstrip('\x00')

            return STLHeader(
                name=header_name or "Unnamed STL",
                triangle_count=triangle_count,
                file_size=file_size
            )

    def stream_triangles(self, file_path: Path) -> Iterator[STLTriangle]:
        """Stream triangles from STL file one by one.

        Args:
            file_path: Path to STL file

        Yields:
            STL triangles as they are read

        Raises:
            ValueError: If file format is invalid
        """
        header = self.load_stl_header(file_path)
        self.logger.info(f"Streaming {header.triangle_count} triangles from {file_path}")

        file_size_mb = header.file_size / (1024 * 1024)
        timeout_seconds = calculate_timeout_for_file_size(file_size_mb, base_timeout=300)

        def _load_triangles():
            with open(file_path, 'rb') as f:
                # Skip 80-byte header
                f.read(80)

                # Skip triangle count (4 bytes)
                f.read(4)

                bytes_read = 84  # Header + triangle count

                for triangle_idx in range(header.triangle_count):
                    # Each triangle is 50 bytes: 12 floats (4 bytes each) + 2 bytes attribute
                    triangle_data = f.read(50)

                    if len(triangle_data) < 50:
                        self.logger.warning(f"Incomplete triangle data at index {triangle_idx}")
                        break

                    bytes_read += 50

                    try:
                        triangle = self._parse_triangle_data(triangle_data)
                        yield triangle

                    except (struct.error, ValueError) as e:
                        self.logger.warning(f"Failed to parse triangle {triangle_idx}: {e}")
                        continue

        # Use error recovery for the streaming operation
        try:
            with watchdog_timeout(timeout_seconds, f"STL streaming for {file_path.name}"):
                yield from error_recovery_manager.execute_with_recovery(
                    OperationType.MESH_LOADING,
                    _load_triangles,
                    fallback_func=self._fallback_streaming_loader
                )
        except Exception as e:
            self.logger.error(f"Failed to stream STL file {file_path}: {e}")
            raise

    def _parse_triangle_data(self, triangle_data: bytes) -> STLTriangle:
        """Parse raw triangle data into STLTriangle object.

        Args:
            triangle_data: 50 bytes of triangle data

        Returns:
            Parsed triangle

        Raises:
            struct.error: If data format is invalid
        """
        # STL binary format: 12 floats (4 bytes each) + 2-byte attribute count
        # Normal vector (3 floats), 3 vertices (9 floats), attribute byte count (2 bytes)

        format_string = '<12f H'  # 12 floats + 1 unsigned short
        unpacked = struct.unpack(format_string, triangle_data)

        normal = (unpacked[0], unpacked[1], unpacked[2])
        vertices = (
            (unpacked[3], unpacked[4], unpacked[5]),
            (unpacked[6], unpacked[7], unpacked[8]),
            (unpacked[9], unpacked[10], unpacked[11])
        )
        attribute_byte_count = unpacked[12]

        return STLTriangle(
            normal=normal,
            vertices=vertices,
            attribute_byte_count=attribute_byte_count
        )

    def _fallback_streaming_loader(self, file_path: Path) -> Iterator[STLTriangle]:
        """Fallback loader that reads entire file into memory.

        This is used when streaming fails or for smaller files.
        """
        self.logger.warning(f"Using fallback loader for {file_path}")

        try:
            import trimesh
            # Load entire mesh into memory as fallback
            mesh = trimesh.load(str(file_path))

            # Convert to triangles and yield them
            for face in mesh.faces:
                # Get vertex positions
                vertices = tuple(tuple(mesh.vertices[vertex_idx]) for vertex_idx in face)

                # Calculate normal (simplified)
                normal = (0.0, 0.0, 1.0)  # Placeholder normal

                yield STLTriangle(
                    normal=normal,
                    vertices=vertices,
                    attribute_byte_count=0
                )

        except ImportError:
            self.logger.error("trimesh not available for fallback loading")
            raise RuntimeError("Cannot load STL file: trimesh not available")
        except Exception as e:
            self.logger.error(f"Fallback loading failed: {e}")
            raise

    def get_mesh_stats(self, file_path: Path) -> Dict[str, Any]:
        """Get basic statistics about the STL file without loading all triangles.

        Args:
            file_path: Path to STL file

        Returns:
            Dictionary with mesh statistics
        """
        header = self.load_stl_header(file_path)

        # Estimate mesh properties
        estimated_vertices = header.triangle_count * 3
        estimated_file_size_mb = header.file_size / (1024 * 1024)

        return {
            'header_name': header.name,
            'triangle_count': header.triangle_count,
            'estimated_vertices': estimated_vertices,
            'file_size_mb': estimated_file_size_mb,
            'format': 'binary_stl'
        }

    def validate_stl_integrity(self, file_path: Path) -> Dict[str, Any]:
        """Validate STL file integrity without loading all data.

        Args:
            file_path: Path to STL file

        Returns:
            Validation results
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        try:
            header = self.load_stl_header(file_path)

            # Check for reasonable triangle count
            if header.triangle_count == 0:
                result['errors'].append("STL file contains no triangles")
                result['valid'] = False
            elif header.triangle_count > 10_000_000:  # Sanity check
                result['warnings'].append(f"Very large triangle count: {header.triangle_count:,}")

            # Check file size consistency
            expected_size = 80 + 4 + (header.triangle_count * 50)  # Header + count + triangles
            if abs(header.file_size - expected_size) > 1000:  # Allow some tolerance
                result['warnings'].append(
                    f"File size mismatch: expected ~{expected_size} bytes, got {header.file_size}"
                )

        except Exception as e:
            result['errors'].append(f"Failed to validate STL file: {e}")
            result['valid'] = False

        return result


# Global instance for easy access
streaming_stl_loader = StreamingSTLLoader()
