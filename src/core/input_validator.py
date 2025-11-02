"""Comprehensive input validation for production security."""
from __future__ import annotations

import re
import os
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """Input validation rule."""
    field_name: str
    required: bool = False
    data_type: type = str
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    custom_validator: Optional[callable] = None


class SecurityValidator:
    """Enhanced security validation for mesh processing inputs."""

    @staticmethod
    def validate_file_path(file_path: Union[str, Path]) -> bool:
        """Validate file path for security issues.

        Args:
            file_path: Path to validate

        Returns:
            bool: True if path is safe, False otherwise
        """
        try:
            path = Path(file_path).resolve()

            # Check for directory traversal
            if ".." in path.parts:
                return False

            # Check for absolute path outside allowed directories
            allowed_dirs = [
                Path.home() / ".3dprintcad",
                Path.cwd(),
            ]

            if not any(path.is_relative_to(allowed) for allowed in allowed_dirs):
                return False

            # Check file size limits
            if path.stat().st_size > 1024 * 1024 * 1024:  # 1GB limit
                return False

            return True

        except (OSError, ValueError):
            return False

    @staticmethod
    def validate_mesh_content(mesh_data: bytes) -> bool:
        """Validate mesh file content for malicious patterns.

        Args:
            mesh_data: Binary mesh data

        Returns:
            bool: True if content appears safe, False otherwise
        """
        # Check for suspicious patterns
        dangerous_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'<?php',
            b'<%',
        ]

        for pattern in dangerous_patterns:
            if pattern.lower() in mesh_data.lower():
                return False

        return True
    """
    Production-grade input validator with comprehensive security checks.

    Features:
    - Type validation
    - Range validation
    - Pattern matching
    - SQL injection prevention
    - XSS prevention
    - Command injection prevention
    """

    # Dangerous patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bUNION\b.*\bSELECT\b)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
    ]

    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$()\\]",
        r"\$\{.*\}",
        r"`.*`",
        r"\$\(.*\)",
    ]

    FILE_UPLOAD_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"\.\.%2f",
        r"\.\.%5c",
    ]

    # File size limits
    MAX_FILE_SIZE_MB = 500
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    def __init__(self):
        self.sql_regex = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self.xss_regex = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
        self.cmd_regex = [re.compile(p, re.IGNORECASE) for p in self.COMMAND_INJECTION_PATTERNS]

    def validate_file_size(self, file_path: str, max_size_mb: int = 500) -> Dict[str, Any]:
        """Validate file size against limits."""
        result = {"valid": True, "file_path": file_path, "errors": [], "warnings": []}

        try:
            file_size_bytes = os.path.getsize(file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)

            if file_size_mb > max_size_mb:
                result["valid"] = False
                result["errors"].append(f"File size {file_size_mb:.1f}MB exceeds limit of {max_size_mb}MB")
            elif file_size_mb > max_size_mb * 0.8:
                result["warnings"].append(f"File size {file_size_mb:.1f}MB is close to limit")

        except OSError as e:
            result["valid"] = False
            result["errors"].append(f"Cannot access file: {e}")

        return result

    def validate_file_path(self, file_path: str) -> Dict[str, Any]:
        """Validate file path for security."""
        result = {"valid": True, "file_path": file_path, "errors": [], "warnings": []}

        # Check for directory traversal
        for pattern in self.FILE_UPLOAD_PATTERNS:
            if re.search(pattern, file_path, re.IGNORECASE):
                result["valid"] = False
                result["errors"].append("Invalid file path detected")
                break

        # Check for absolute paths
        if os.path.isabs(file_path):
            result["valid"] = False
            result["errors"].append("Absolute paths not allowed")

        # Check file extension
        allowed_extensions = ['.stl', '.obj', '.ply', '.3mf', '.amf']
        if not any(file_path.lower().endswith(ext) for ext in allowed_extensions):
            result["warnings"].append("Unusual file extension")

        return result

    def validate_field(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """
        Validate a single field against a rule.

        Returns:
            Dict with validation results
        """
        result = {
            "valid": True,
            "errors": [],
            "sanitized_value": value
        }

        # Check required
        if rule.required and (value is None or value == ""):
            result["valid"] = False
            result["errors"].append(f"{rule.field_name} is required")
            return result

        # Skip validation if value is None and not required
        if value is None:
            return result
            return result

        # Type validation
        if rule.data_type and not isinstance(value, rule.data_type):
            try:
                value = rule.data_type(value)
                result["sanitized_value"] = value
            except (ValueError, TypeError):
                result["valid"] = False
                result["errors"].append(
                    f"{rule.field_name} must be of type {rule.data_type.__name__}"
                )
                return result

        # Numeric range validation
        if rule.data_type in (int, float):
            if rule.min_value is not None and value < rule.min_value:
                result["valid"] = False
                result["errors"].append(
                    f"{rule.field_name} must be >= {rule.min_value}"
                )
            if rule.max_value is not None and value > rule.max_value:
                result["valid"] = False
                result["errors"].append(
                    f"{rule.field_name} must be <= {rule.max_value}"
                )

        # String validation
        if rule.data_type == str:
            str_value = str(value)

            # Length validation
            if rule.min_length is not None and len(str_value) < rule.min_length:
                result["valid"] = False
                result["errors"].append(
                    f"{rule.field_name} must be at least {rule.min_length} characters"
                )
            if rule.max_length is not None and len(str_value) > rule.max_length:
                result["valid"] = False
                result["errors"].append(
                    f"{rule.field_name} must be at most {rule.max_length} characters"
                )

            # Pattern validation
            if rule.pattern and not re.match(rule.pattern, str_value):
                result["valid"] = False
                result["errors"].append(
                    f"{rule.field_name} does not match required pattern"
                )

            # Security checks for strings
            security_result = self.check_security_patterns(str_value, rule.field_name)
            if not security_result["safe"]:
                result["valid"] = False
                result["errors"].extend(security_result["threats"])

        # Allowed values validation
        if rule.allowed_values is not None and value not in rule.allowed_values:
            result["valid"] = False
            result["errors"].append(
                f"{rule.field_name} must be one of {rule.allowed_values}"
            )

        # Custom validator
        if rule.custom_validator:
            try:
                custom_result = rule.custom_validator(value)
                if not custom_result:
                    result["valid"] = False
                    result["errors"].append(
                        f"{rule.field_name} failed custom validation"
                    )
            except Exception as e:
                result["valid"] = False
                result["errors"].append(f"Custom validation error: {str(e)}")

        return result

    def validate_data(self, data: Dict[str, Any], rules: List[ValidationRule]) -> Dict[str, Any]:
        """
        Validate dictionary of data against multiple rules.

        Returns:
            Dict with validation results and sanitized data
        """
        result = {
            "valid": True,
            "errors": {},
            "sanitized_data": {}
        }

        for rule in rules:
            value = data.get(rule.field_name)
            field_result = self.validate_field(value, rule)

            if not field_result["valid"]:
                result["valid"] = False
                result["errors"][rule.field_name] = field_result["errors"]

            result["sanitized_data"][rule.field_name] = field_result["sanitized_value"]

        return result

    def check_security_patterns(self, value: str, field_name: str) -> Dict[str, Any]:
        """
        Check for SQL injection, XSS, and command injection patterns.

        Returns:
            Dict with safety status and detected threats
        """
        result = {
            "safe": True,
            "threats": []
        }

        # SQL Injection check
        for pattern in self.sql_regex:
            if pattern.search(value):
                result["safe"] = False
                result["threats"].append(
                    f"{field_name} contains potential SQL injection pattern"
                )
                logger.warning(f"SQL injection attempt detected in {field_name}: {value[:50]}")
                break

        # XSS check
        for pattern in self.xss_regex:
            if pattern.search(value):
                result["safe"] = False
                result["threats"].append(
                    f"{field_name} contains potential XSS pattern"
                )
                logger.warning(f"XSS attempt detected in {field_name}: {value[:50]}")
                break

        # Command injection check
        for pattern in self.cmd_regex:
            if pattern.search(value):
                result["safe"] = False
                result["threats"].append(
                    f"{field_name} contains potential command injection pattern"
                )
                logger.warning(f"Command injection attempt detected in {field_name}: {value[:50]}")
                break

        return result

    def sanitize_string(self, value: str, allow_html: bool = False) -> str:
        """
        Sanitize string input.

        Args:
            value: Input string
            allow_html: If True, allow safe HTML tags

        Returns:
            Sanitized string
        """
        if not value:
            return value

        # Remove null bytes
        value = value.replace('\x00', '')

        # Remove control characters except newline and tab
        value = ''.join(
            char for char in value
            if ord(char) >= 32 or char in ['\n', '\t']
        )

        if not allow_html:
            # Escape HTML special characters
            value = (value
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#x27;'))

        return value.strip()

    def validate_file_upload(
        self,
        filename: str,
        content_type: str,
        file_size: int,
        allowed_extensions: Optional[List[str]] = None,
        max_size_mb: int = 100
    ) -> Dict[str, Any]:
        """
        Validate file upload parameters.

        Returns:
            Dict with validation results
        """
        result = {
            "valid": True,
            "errors": []
        }

        # Validate filename
        if not filename:
            result["valid"] = False
            result["errors"].append("Filename is required")
            return result

        # Check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            result["valid"] = False
            result["errors"].append("Invalid filename: path traversal detected")
            return result

        # Validate extension
        if allowed_extensions:
            file_ext = Path(filename).suffix.lower()
            if file_ext not in allowed_extensions:
                result["valid"] = False
                result["errors"].append(
                    f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}"
                )

        # Validate file size
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            result["valid"] = False
            result["errors"].append(
                f"File size {file_size / 1024 / 1024:.2f}MB exceeds limit of {max_size_mb}MB"
            )

        # Validate content type (basic check)
        if not content_type or not content_type.strip():
            result["errors"].append("Warning: Content-Type header missing")

        return result

    def validate_json_schema(self, data: Dict, schema: Dict) -> Dict[str, Any]:
        """
        Validate JSON data against a simple schema.

        Args:
            data: JSON data to validate
            schema: Schema definition

        Returns:
            Dict with validation results
        """
        result = {
            "valid": True,
            "errors": []
        }

        for field, field_schema in schema.items():
            if 'required' in field_schema and field_schema['required']:
                if field not in data:
                    result["valid"] = False
                    result["errors"].append(f"Required field missing: {field}")
                    continue

            if field in data:
                value = data[field]
                expected_type = field_schema.get('type')

                if expected_type and not isinstance(value, expected_type):
                    result["valid"] = False
                    result["errors"].append(
                        f"Field {field} must be of type {expected_type.__name__}"
                    )

        return result


# Pre-defined validation rules for common use cases
MESH_VALIDATION_RULES = [
    ValidationRule(
        field_name="min_wall_thickness",
        required=False,
        data_type=float,
        min_value=0.1,
        max_value=10.0
    ),
    ValidationRule(
        field_name="min_feature_size",
        required=False,
        data_type=float,
        min_value=0.1,
        max_value=10.0
    ),
    ValidationRule(
        field_name="max_overhang_angle",
        required=False,
        data_type=int,
        min_value=0,
        max_value=90
    ),
]

SLICE_SETTINGS_RULES = [
    ValidationRule(
        field_name="layer_height",
        required=True,
        data_type=float,
        min_value=0.05,
        max_value=1.0
    ),
    ValidationRule(
        field_name="infill_density",
        required=False,
        data_type=int,
        min_value=0,
        max_value=100
    ),
    ValidationRule(
        field_name="print_speed",
        required=False,
        data_type=int,
        min_value=10,
        max_value=300
    ),
    ValidationRule(
        field_name="support_enabled",
        required=False,
        data_type=bool
    ),
]


# Global validator instance
input_validator = InputValidator()
