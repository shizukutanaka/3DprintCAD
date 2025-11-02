"""Custom exceptions for 3D print CAD assistant."""


class CADAssistantError(Exception):
    """Base exception for all CAD assistant errors."""
    pass


class MeshError(CADAssistantError):
    """Base exception for mesh-related errors."""
    pass


class MeshLoadError(MeshError):
    """Raised when a mesh file cannot be loaded."""
    pass


class MeshValidationError(MeshError):
    """Raised when mesh validation fails."""
    pass


class MeshRepairError(MeshError):
    """Raised when mesh repair fails."""
    pass


class SlicingError(CADAssistantError):
    """Raised when slicing operation fails."""
    pass


class GcodeGenerationError(CADAssistantError):
    """Raised when G-code generation fails."""
    pass


class ConfigurationError(CADAssistantError):
    """Raised when configuration is invalid."""
    pass


class MaterialError(CADAssistantError):
    """Raised when material-related operations fail."""
    pass


class PrinterProfileError(CADAssistantError):
    """Raised when printer profile operations fail."""
    pass


class FileProcessingError(CADAssistantError):
    """Raised when file processing fails."""
    pass


class BatchProcessingError(CADAssistantError):
    """Raised when batch processing fails."""
    pass


class SecurityError(CADAssistantError):
    """Raised when security checks fail."""
    pass


class ValidationWarning(Warning):
    """Warning for non-critical validation issues."""
    pass