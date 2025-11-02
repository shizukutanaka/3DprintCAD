"""File compression utilities for reducing upload size."""
from __future__ import annotations

import gzip
import zlib
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FileCompressor:
    """Compress files before upload to reduce bandwidth usage."""

    def __init__(self, compression_level: int = 6):
        """
        Initialize compressor.

        Args:
            compression_level: Compression level (1-9, default 6)
        """
        self.compression_level = min(max(compression_level, 1), 9)

    def compress_file(self, file_path: Path, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Compress a file using gzip.

        Args:
            file_path: Path to file to compress
            output_path: Optional output path (default: file_path.gz)

        Returns:
            Dict with compression results
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if output_path is None:
            output_path = file_path.with_suffix(file_path.suffix + '.gz')

        original_size = file_path.stat().st_size

        try:
            with open(file_path, 'rb') as f_in:
                with gzip.open(output_path, 'wb', compresslevel=self.compression_level) as f_out:
                    f_out.writelines(f_in)

            compressed_size = output_path.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

            logger.info(
                f"Compressed {file_path.name}: {original_size} -> {compressed_size} bytes "
                f"({ratio:.1f}% reduction)"
            )

            return {
                'success': True,
                'original_path': str(file_path),
                'compressed_path': str(output_path),
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': ratio
            }

        except Exception as e:
            logger.error(f"Compression failed for {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_path': str(file_path)
            }

    def decompress_file(self, compressed_path: Path, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Decompress a gzip file.

        Args:
            compressed_path: Path to compressed file
            output_path: Optional output path

        Returns:
            Dict with decompression results
        """
        if not compressed_path.exists():
            raise FileNotFoundError(f"File not found: {compressed_path}")

        if output_path is None:
            # Remove .gz extension
            output_path = compressed_path.with_suffix('')

        try:
            with gzip.open(compressed_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    f_out.writelines(f_in)

            logger.info(f"Decompressed {compressed_path.name} to {output_path}")

            return {
                'success': True,
                'compressed_path': str(compressed_path),
                'output_path': str(output_path)
            }

        except Exception as e:
            logger.error(f"Decompression failed for {compressed_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'compressed_path': str(compressed_path)
            }

    def compress_bytes(self, data: bytes) -> bytes:
        """
        Compress bytes using zlib.

        Args:
            data: Bytes to compress

        Returns:
            Compressed bytes
        """
        return zlib.compress(data, level=self.compression_level)

    def decompress_bytes(self, data: bytes) -> bytes:
        """
        Decompress bytes using zlib.

        Args:
            data: Compressed bytes

        Returns:
            Decompressed bytes
        """
        return zlib.decompress(data)

    def should_compress(self, file_path: Path, min_size_kb: int = 100) -> bool:
        """
        Determine if file should be compressed.

        Args:
            file_path: Path to file
            min_size_kb: Minimum file size in KB to compress

        Returns:
            True if file should be compressed
        """
        if not file_path.exists():
            return False

        # Check file size
        size_kb = file_path.stat().st_size / 1024
        if size_kb < min_size_kb:
            return False

        # Check if already compressed
        compressed_extensions = {'.gz', '.zip', '.7z', '.rar', '.bz2', '.xz'}
        if file_path.suffix.lower() in compressed_extensions:
            return False

        # 3D file formats benefit from compression
        compressible_extensions = {'.stl', '.obj', '.ply', '.3mf', '.amf', '.gcode'}
        if file_path.suffix.lower() in compressible_extensions:
            return True

        return True


def estimate_compression_ratio(file_path: Path, sample_size: int = 10000) -> float:
    """
    Estimate compression ratio by sampling file.

    Args:
        file_path: Path to file
        sample_size: Number of bytes to sample

    Returns:
        Estimated compression ratio (0-100)
    """
    if not file_path.exists():
        return 0.0

    try:
        with open(file_path, 'rb') as f:
            sample = f.read(sample_size)

        if not sample:
            return 0.0

        compressed = zlib.compress(sample, level=6)
        ratio = (1 - len(compressed) / len(sample)) * 100 if len(sample) > 0 else 0

        return max(0.0, min(100.0, ratio))

    except Exception as e:
        logger.error(f"Failed to estimate compression ratio for {file_path}: {e}")
        return 0.0


# Global compressor instance
compressor = FileCompressor()
