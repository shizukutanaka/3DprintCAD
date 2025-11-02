"""Input validation utilities for secure processing."""
from pathlib import Path
from typing import Optional, Union, List, Any
import re

from .exceptions import SecurityError, ValidationWarning


class PathValidator:
    """Validate and sanitize file paths."""

    @staticmethod
    def validate_path(path: Union[str, Path], base_dir: Optional[Path] = None) -> Path:
        """Validate and sanitize a file path.

        Args:
            path: Path to validate
            base_dir: Optional base directory for relative paths

        Returns:
            Validated Path object

        Raises:
            SecurityError: If path contains security issues
        """
        path = Path(path)

        # Check for path traversal attempts
        if ".." in path.parts:
            raise SecurityError("Path traversal detected")

        # Resolve to absolute path
        if base_dir:
            path = (Path(base_dir) / path).resolve()
        else:
            path = path.resolve()

        # Check if path is within allowed directory
        if base_dir and not path.is_relative_to(Path(base_dir).resolve()):
            raise SecurityError(f"Path {path} is outside allowed directory")

        return path

    @staticmethod
    def validate_filename(filename: str) -> str:
        """Validate and sanitize a filename.

        Args:
            filename: Filename to validate

        Returns:
            Sanitized filename

        Raises:
            SecurityError: If filename contains invalid characters
        """
        # Remove path separators
        if "/" in filename or "\\" in filename:
            raise SecurityError("Filename cannot contain path separators")

        # Check for null bytes
        if "\x00" in filename:
            raise SecurityError("Filename cannot contain null bytes")

        # Sanitize special characters
        sanitized = re.sub(r'[^\w\s.-]', '_', filename)

        # Limit length
        if len(sanitized) > 255:
            sanitized = sanitized[:255]

        return sanitized


class NumericValidator:
    """Validate numeric inputs."""

    @staticmethod
    def validate_positive(value: Union[int, float], name: str = "value") -> Union[int, float]:
        """Ensure value is positive.

        Args:
            value: Value to validate
            name: Name for error messages

        Returns:
            Validated value

        Raises:
            ValueError: If value is not positive
        """
        if value <= 0:
            raise ValueError(f"{name} must be positive, got {value}")
        return value

    @staticmethod
    def validate_range(
        value: Union[int, float],
        min_val: Optional[Union[int, float]] = None,
        max_val: Optional[Union[int, float]] = None,
        name: str = "value"
    ) -> Union[int, float]:
        """Validate value is within range.

        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            name: Name for error messages

        Returns:
            Validated value

        Raises:
            ValueError: If value is out of range
        """
        if min_val is not None and value < min_val:
            raise ValueError(f"{name} must be >= {min_val}, got {value}")

        if max_val is not None and value > max_val:
            raise ValueError(f"{name} must be <= {max_val}, got {value}")

        return value

    @staticmethod
    def validate_percentage(value: Union[int, float], name: str = "percentage") -> Union[int, float]:
        """Validate percentage value (0-100).

        Args:
            value: Percentage value
            name: Name for error messages

        Returns:
            Validated percentage

        Raises:
            ValueError: If value is not valid percentage
        """
        return NumericValidator.validate_range(value, 0, 100, name)


class MeshValidator:
    """Validate mesh-specific parameters."""

    @staticmethod
    def validate_file_size(file_path: Path, max_size_mb: float = 100) -> None:
        """Validate mesh file size.

        Args:
            file_path: Path to mesh file
            max_size_mb: Maximum allowed size in MB

        Raises:
            ValueError: If file is too large
        """
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")

        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            raise ValueError(f"File size {size_mb:.1f}MB exceeds maximum {max_size_mb}MB")

    @staticmethod
    def validate_extension(file_path: Path, allowed_extensions: List[str]) -> None:
        """Validate file extension.

        Args:
            file_path: Path to validate
            allowed_extensions: List of allowed extensions (e.g., ['.stl', '.obj'])

        Raises:
            ValueError: If extension is not allowed
        """
        extension = file_path.suffix.lower()
        if extension not in allowed_extensions:
            raise ValueError(f"Unsupported file type: {extension}. Allowed: {allowed_extensions}")


class PrintSettingsValidator:
    """Validate 3D printing parameters."""

    @staticmethod
    def validate_layer_height(height: float, nozzle_diameter: float = 0.4) -> float:
        """Validate layer height.

        Args:
            height: Layer height in mm
            nozzle_diameter: Nozzle diameter in mm

        Returns:
            Validated layer height

        Raises:
            ValueError: If layer height is invalid
        """
        min_height = 0.05
        max_height = nozzle_diameter * 0.75

        return NumericValidator.validate_range(
            height,
            min_height,
            max_height,
            "Layer height"
        )

    @staticmethod
    def validate_temperature(temp: float, material: str = "PLA") -> float:
        """Validate print temperature.

        Args:
            temp: Temperature in Celsius
            material: Material type

        Returns:
            Validated temperature

        Raises:
            ValueError: If temperature is out of range for material
        """
        temp_ranges = {
            "PLA": (180, 230),
            "ABS": (220, 260),
            "PETG": (220, 250),
            "TPU": (210, 240),
            "Nylon": (240, 280)
        }

        if material.upper() in temp_ranges:
            min_temp, max_temp = temp_ranges[material.upper()]
            return NumericValidator.validate_range(
                temp,
                min_temp,
                max_temp,
                f"{material} temperature"
            )

        # Default range for unknown materials
        return NumericValidator.validate_range(temp, 150, 300, "Temperature")

    @staticmethod
    def validate_speed(speed: float, print_type: str = "normal") -> float:
        """Validate print speed.

        Args:
            speed: Speed in mm/s
            print_type: Type of print (normal, fast, slow)

        Returns:
            Validated speed

        Raises:
            ValueError: If speed is out of range
        """
        speed_ranges = {
            "slow": (10, 30),
            "normal": (30, 80),
            "fast": (80, 150)
        }

        if print_type in speed_ranges:
            min_speed, max_speed = speed_ranges[print_type]
        else:
            min_speed, max_speed = 10, 150

        return NumericValidator.validate_range(
            speed,
            min_speed,
            max_speed,
            "Print speed"
        )


class BatchValidator:
    """Validate batch processing parameters."""

    @staticmethod
    def validate_worker_count(workers: int, max_workers: Optional[int] = None) -> int:
        """Validate number of parallel workers.

        Args:
            workers: Requested worker count
            max_workers: Maximum allowed workers

        Returns:
            Validated worker count

        Raises:
            ValueError: If worker count is invalid
        """
        import multiprocessing

        if max_workers is None:
            max_workers = min(32, multiprocessing.cpu_count() * 2)

        return int(NumericValidator.validate_range(
            workers,
            1,
            max_workers,
            "Worker count"
        ))

    @staticmethod
    def validate_batch_size(batch_size: int, max_batch: int = 1000) -> int:
        """Validate batch size.

        Args:
            batch_size: Requested batch size
            max_batch: Maximum allowed batch size

        Returns:
            Validated batch size

        Raises:
            ValueError: If batch size is invalid
        """
        return int(NumericValidator.validate_range(
            batch_size,
            1,
            max_batch,
            "Batch size"
        ))