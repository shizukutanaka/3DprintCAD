"""Lightweight automation features for 3D print workflow."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from ..adapters import load_mesh
from .analysis.mesh_validator import validate_mesh, MeshValidationSettings
from .analysis.mesh_repair import repair_mesh
from .recommendation import RecommendationEngine

logger = logging.getLogger(__name__)


class AutoValidator:
    """Automatic validation on file upload/load."""

    def __init__(self, settings: Optional[MeshValidationSettings] = None):
        self.settings = settings or MeshValidationSettings()

    def validate_and_report(self, file_path: Path) -> Dict[str, Any]:
        """
        Auto-validate mesh and return structured report.

        Args:
            file_path: Path to mesh file

        Returns:
            Validation report with issues and recommendations
        """
        try:
            mesh = load_mesh(file_path)
            validation_result = validate_mesh(mesh, settings=self.settings)

            # Generate recommendations automatically
            recommender = RecommendationEngine()
            recommendations = recommender.generate_recommendations(validation_result)

            return {
                'success': True,
                'file': str(file_path),
                'validation': validation_result.to_dict(),
                'recommendations': recommendations.to_dict(),
                'auto_repairable': self._check_auto_repairable(validation_result)
            }

        except Exception as e:
            logger.error(f"Auto-validation failed for {file_path}: {e}")
            return {
                'success': False,
                'file': str(file_path),
                'error': str(e)
            }

    def _check_auto_repairable(self, validation_result) -> bool:
        """Check if issues are automatically repairable."""
        auto_repairable_types = {
            'non_manifold_edges',
            'degenerate_faces',
            'duplicate_vertices',
            'inverted_normals'
        }

        for issue in validation_result.issues:
            if issue.type in auto_repairable_types:
                return True

        return False


class AutoRepair:
    """Automatic mesh repair workflow."""

    def __init__(self):
        self.validator = AutoValidator()

    def repair_if_needed(
        self,
        file_path: Path,
        output_path: Optional[Path] = None,
        aggressive: bool = False
    ) -> Dict[str, Any]:
        """
        Automatically repair mesh if issues are detected.

        Args:
            file_path: Input mesh file
            output_path: Output path for repaired mesh (optional)
            aggressive: Use aggressive repair mode

        Returns:
            Repair report with before/after validation
        """
        # First validate
        validation = self.validator.validate_and_report(file_path)

        if not validation['success']:
            return validation

        # Check if repair is needed
        if validation['validation']['is_valid']:
            return {
                'success': True,
                'repair_needed': False,
                'message': 'Mesh is already valid, no repair needed',
                'validation': validation
            }

        # Check if auto-repairable
        if not validation['auto_repairable']:
            return {
                'success': False,
                'repair_needed': True,
                'auto_repairable': False,
                'message': 'Mesh has issues that cannot be automatically repaired',
                'validation': validation
            }

        # Perform repair
        try:
            mesh = load_mesh(file_path)
            repaired_mesh = repair_mesh(mesh, aggressive=aggressive)

            if repaired_mesh is None:
                return {
                    'success': False,
                    'repair_needed': True,
                    'message': 'Repair failed - mesh could not be fixed',
                    'validation': validation
                }

            # Save repaired mesh
            if output_path is None:
                output_path = file_path.parent / f"{file_path.stem}_repaired{file_path.suffix}"

            repaired_mesh.export(str(output_path))

            # Re-validate repaired mesh
            post_validation = self.validator.validate_and_report(output_path)

            return {
                'success': True,
                'repair_needed': True,
                'repaired': True,
                'output_file': str(output_path),
                'before_validation': validation,
                'after_validation': post_validation,
                'improvement': {
                    'issues_before': len(validation['validation']['issues']),
                    'issues_after': len(post_validation['validation']['issues'])
                }
            }

        except Exception as e:
            logger.error(f"Auto-repair failed for {file_path}: {e}")
            return {
                'success': False,
                'repair_needed': True,
                'error': str(e)
            }


class BatchProcessor:
    """Simple batch file processor."""

    def __init__(self, auto_repair: bool = False, auto_validate: bool = True):
        self.auto_repair = auto_repair
        self.auto_validate = auto_validate
        self.validator = AutoValidator()
        self.repairer = AutoRepair()

    def process_directory(
        self,
        input_dir: Path,
        output_dir: Optional[Path] = None,
        pattern: str = "*.stl"
    ) -> Dict[str, Any]:
        """
        Process all files in directory.

        Args:
            input_dir: Input directory
            output_dir: Output directory for processed files
            pattern: File pattern to match

        Returns:
            Batch processing report
        """
        input_path = Path(input_dir)
        if not input_path.exists() or not input_path.is_dir():
            return {
                'success': False,
                'error': f'Invalid input directory: {input_dir}'
            }

        files = list(input_path.glob(pattern))
        if not files:
            return {
                'success': False,
                'error': f'No files matching {pattern} found in {input_dir}'
            }

        results = {
            'total_files': len(files),
            'processed': 0,
            'valid': 0,
            'repaired': 0,
            'failed': 0,
            'files': []
        }

        for file_path in files:
            try:
                if self.auto_repair:
                    result = self.repairer.repair_if_needed(
                        file_path,
                        output_path=output_dir / file_path.name if output_dir else None
                    )
                elif self.auto_validate:
                    result = self.validator.validate_and_report(file_path)
                else:
                    result = {'success': True, 'file': str(file_path)}

                results['files'].append(result)
                results['processed'] += 1

                if result.get('success'):
                    if result.get('repaired'):
                        results['repaired'] += 1
                    elif result.get('validation', {}).get('is_valid'):
                        results['valid'] += 1
                else:
                    results['failed'] += 1

            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                results['failed'] += 1
                results['files'].append({
                    'success': False,
                    'file': str(file_path),
                    'error': str(e)
                })

        results['success'] = results['failed'] < results['total_files']
        return results


class FileTypeDetector:
    """Automatic file format detection."""

    SUPPORTED_FORMATS = {
        '.stl': 'stereolithography',
        '.obj': 'wavefront',
        '.ply': 'polygon',
        '.3mf': '3d_manufacturing',
        '.amf': 'additive_manufacturing',
        '.off': 'object_file_format',
        '.gltf': 'gltf',
        '.glb': 'gltf_binary'
    }

    BINARY_SIGNATURES = {
        b'solid ': 'stl_ascii',
        b'\x80\x00\x00\x00': 'stl_binary',
        b'PK\x03\x04': '3mf',
        b'<?xml': 'xml_based'
    }

    @classmethod
    def detect_format(cls, file_path: Path) -> Dict[str, Any]:
        """
        Detect file format from extension and content.

        Args:
            file_path: Path to file

        Returns:
            Format detection result
        """
        if not file_path.exists():
            return {
                'success': False,
                'error': 'File does not exist'
            }

        # Check extension
        ext = file_path.suffix.lower()
        format_name = cls.SUPPORTED_FORMATS.get(ext)

        # Check binary signature
        try:
            with open(file_path, 'rb') as f:
                header = f.read(512)

            detected_type = None
            for signature, type_name in cls.BINARY_SIGNATURES.items():
                if header.startswith(signature):
                    detected_type = type_name
                    break

            return {
                'success': True,
                'extension': ext,
                'format_name': format_name,
                'detected_type': detected_type,
                'is_binary': detected_type and 'binary' in detected_type,
                'supported': format_name is not None
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


def auto_validate_file(file_path: Path) -> Dict[str, Any]:
    """
    Quick helper to auto-validate a file.

    Args:
        file_path: Path to mesh file

    Returns:
        Validation report
    """
    validator = AutoValidator()
    return validator.validate_and_report(file_path)


def auto_repair_file(
    file_path: Path,
    output_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Quick helper to auto-repair a file.

    Args:
        file_path: Input mesh file
        output_path: Output path (optional)

    Returns:
        Repair report
    """
    repairer = AutoRepair()
    return repairer.repair_if_needed(file_path, output_path)


def process_batch(
    input_dir: Path,
    output_dir: Optional[Path] = None,
    auto_repair: bool = False
) -> Dict[str, Any]:
    """
    Quick helper to process batch of files.

    Args:
        input_dir: Input directory
        output_dir: Output directory
        auto_repair: Enable auto-repair

    Returns:
        Batch processing report
    """
    processor = BatchProcessor(auto_repair=auto_repair)
    return processor.process_directory(input_dir, output_dir)
