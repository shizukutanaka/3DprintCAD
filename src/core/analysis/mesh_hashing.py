"""File hashing utilities for mesh processing workflows."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import hashlib

from ..logging import get_logger


__all__ = [
    "FileHashResult",
    "calculate_mesh_hash",
    "calculate_file_hash",
    "calculate_parallel_hashes",
]


@dataclass
class FileHashResult:
    """Result container for file hashing operations."""

    file_path: Path
    hash_value: str
    success: bool
    error: Optional[str] = None


def calculate_mesh_hash(file_path: Path, *, block_size: int = 65536) -> str:
    """Calculate the SHA-256 hash of ``file_path``."""

    hash_sha256 = hashlib.sha256()

    with open(file_path, "rb") as source:
        for chunk in iter(lambda: source.read(block_size), b""):
            hash_sha256.update(chunk)

    return hash_sha256.hexdigest()


def calculate_file_hash(file_path: Path) -> FileHashResult:
    """Calculate the hash for a single file and capture failures."""

    try:
        return FileHashResult(
            file_path=file_path,
            hash_value=calculate_mesh_hash(file_path),
            success=True,
        )
    except Exception as exc:  # pragma: no cover - failure surface logged upstream
        return FileHashResult(file_path=file_path, hash_value="", success=False, error=str(exc))


def calculate_parallel_hashes(file_paths: List[Path], *, max_workers: int = 4) -> Dict[Path, str]:
    """Calculate hashes for *file_paths* in parallel."""

    logger = get_logger(__name__)

    if not file_paths:
        return {}

    results: Dict[Path, str] = {}
    failed_results: List[FileHashResult] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(calculate_file_hash, file_path): file_path for file_path in file_paths
        }

        for future in as_completed(futures):
            result = future.result()
            if result.success:
                results[result.file_path] = result.hash_value
            else:
                failed_results.append(result)

    for failed in failed_results:
        logger.warning("Failed to hash file %s: %s", failed.file_path, failed.error)

    return results
