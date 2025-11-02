#!/usr/bin/env python3
"""Optimized unified CLI for 3D print CAD assistant with lazy loading."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
import unicodedata
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Iterable, Set
from concurrent.futures import ProcessPoolExecutor, BrokenProcessPool, wait, FIRST_COMPLETED
import multiprocessing
import threading
import gc
import signal
import resource
import traceback
import psutil
from typing import Any, Dict, List, Tuple, Optional, Callable
from pathlib import Path
from tqdm import tqdm

from .core.parallel_processor import ParallelProcessor, MemoryMonitor, init_worker

# Lazy-loaded heavy imports
_trimesh = None
_numpy = None
_mesh_validator = None
_RecommendationEngine = None
_SliceSettings = None
_SlicingEngine = None
_GcodeSettings = None
_GcodeGenerator = None
_evaluate_print_readiness = None

def _lazy_import_trimesh():
    """Lazy import trimesh."""
    global _trimesh
    if _trimesh is None:
        import trimesh
        _trimesh = trimesh
    return _trimesh

def _lazy_import_numpy():
    """Lazy import numpy."""
    global _numpy
    if _numpy is None:
        import numpy as np
        _numpy = np
    return _numpy

def _lazy_import_mesh_validator():
    """Lazy import mesh validator."""
    global _mesh_validator
    if _mesh_validator is None:
        from .core.analysis import mesh_validator
        _mesh_validator = mesh_validator
    return _mesh_validator

def _lazy_import_recommendation_engine():
    """Lazy import recommendation engine."""
    global _RecommendationEngine
    if _RecommendationEngine is None:
        from .core.recommendation import RecommendationEngine
        _RecommendationEngine = RecommendationEngine
    return _RecommendationEngine

def _lazy_import_slicing():
    """Lazy import slicing components."""
    global _SliceSettings, _SlicingEngine, _GcodeSettings, _GcodeGenerator
    if _SliceSettings is None:
        from .core.slicing import SlicingEngine, SliceSettings
        from .core.slicing.gcode_generator import GcodeGenerator, GcodeSettings
        _SliceSettings = SliceSettings
        _SlicingEngine = SlicingEngine
        _GcodeSettings = GcodeSettings
        _GcodeGenerator = GcodeGenerator
    return _SliceSettings, _SlicingEngine, _GcodeSettings, _GcodeGenerator

def _lazy_import_readiness():
    """Lazy import readiness evaluation."""
    global _evaluate_print_readiness
    if _evaluate_print_readiness is None:
        from .reporting.readiness import evaluate_print_readiness
        _evaluate_print_readiness = evaluate_print_readiness
    return _evaluate_print_readiness

# Always import these lightweight modules
from .adapters import load_mesh, MeshLoadError
from .core.logging import get_logger, configure_logging, LogLevel, create_context
from .core.config import get_config
from .core.i18n_optimized import set_language as set_global_language

# Constants
MESH_EXTENSIONS = (".stl", ".obj", ".ply", ".3mf", ".amf")
DEFAULT_HASH_CHUNK_SIZE = 1024 * 1024
MIN_THRESHOLD_MM = 0.01
MAX_THRESHOLD_MM = 500.0


def init_worker():
    """Initialize worker process."""
    # Reset signal handlers (for Ctrl+C handling)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    # Set memory limits (in bytes)
    if hasattr(resource, 'RLIMIT_AS'):
        resource.setrlimit(
            resource.RLIMIT_AS,
            (4 * 1024 * 1024 * 1024, 8 * 1024 * 1024 * 1024)  # 4GB soft, 8GB hard
        )


class ErrorRecoveryManager:
    """Manages error recovery strategies for failed processing operations."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.recovery_strategies = {
            "mesh_load": self._recover_mesh_load_failure,
            "validation": self._recover_validation_failure,
            "repair": self._recover_repair_failure,
            "slicing": self._recover_slicing_failure,
            "gcode": self._recover_gcode_failure,
            "recommendations": self._recover_recommendations_failure,
        }
        self.max_retries = 3
        self.retry_delays = [1, 2, 5]  # seconds

    def attempt_recovery(self, operation: str, error: Exception, context: Dict[str, Any]) -> Optional[Any]:
        """Attempt to recover from a failed operation."""
        if operation not in self.recovery_strategies:
            self.logger.warning(f"No recovery strategy for operation: {operation}")
            return None

        strategy = self.recovery_strategies[operation]

        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Attempting recovery for {operation}, attempt {attempt + 1}/{self.max_retries}")
                result = strategy(error, context, attempt)
                if result is not None:
                    self.logger.info(f"Recovery successful for {operation} on attempt {attempt + 1}")
                    return result
            except Exception as recovery_error:
                self.logger.warning(f"Recovery attempt {attempt + 1} failed for {operation}: {recovery_error}")

            if attempt < self.max_retries - 1:
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                time.sleep(delay)

        self.logger.error(f"All recovery attempts failed for {operation}")
        return None

    def _recover_mesh_load_failure(self, error: Exception, context: Dict[str, Any], attempt: int) -> Optional[trimesh.Trimesh]:
        """Recover from mesh loading failures."""
        file_path = context.get("file_path")
        if not file_path:
            return None

        # Try alternative loading methods
        try:
            # For ASCII STL files that failed binary loading
            if isinstance(error, (UnicodeDecodeError, struct.error)) and file_path.suffix.lower() == '.stl':
                self.logger.info(f"Trying ASCII STL loading for {file_path}")
                trimesh_module = _lazy_import_trimesh()
                return trimesh_module.load_mesh(str(file_path), file_type='stl', force='mesh')

            # For OBJ files with encoding issues
            elif isinstance(error, UnicodeDecodeError) and file_path.suffix.lower() == '.obj':
                self.logger.info(f"Trying alternative encoding for {file_path}")
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                # Convert to UTF-8 and save temporarily
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.obj', delete=False, encoding='utf-8') as tmp:
                    tmp.write(content)
                    tmp.flush()
                    trimesh_module = _lazy_import_trimesh()
                    mesh = trimesh_module.load_mesh(tmp.name)
                    os.unlink(tmp.name)
                    return mesh

        except Exception as recovery_error:
            self.logger.debug(f"Mesh load recovery failed: {recovery_error}")

        return None

    def _recover_validation_failure(self, error: Exception, context: Dict[str, Any], attempt: int) -> Optional[Dict[str, Any]]:
        """Recover from validation failures by using relaxed settings."""
        mesh = context.get("mesh")
        args = context.get("args")
        if not mesh or not args:
            return None

        try:
            # Try with relaxed validation settings
            mesh_validator = _lazy_import_mesh_validator()
            relaxed_settings = mesh_validator.MeshValidationSettings(
                min_wall_thickness_mm=max(args.min_wall * 0.5, 0.1),  # More relaxed
                min_feature_size_mm=max(args.min_feature * 0.7, 0.05),
                support_overhang_angle_deg=min(args.overhang_angle + 10, 75),  # Less strict
            )

            validation = mesh_validator.validate_mesh(mesh, settings=relaxed_settings)
            result = validation.as_dict()
            result["validation_relaxed"] = True
            result["original_error"] = str(error)
            return result

        except Exception as recovery_error:
            self.logger.debug(f"Validation recovery failed: {recovery_error}")

        return None

    def _recover_repair_failure(self, error: Exception, context: Dict[str, Any], attempt: int) -> Optional[Dict[str, Any]]:
        """Recover from repair failures by using aggressive repair."""
        mesh = context.get("mesh")
        args = context.get("args")
        if not mesh or not args:
            return None

        try:
            # Try aggressive repair if not already used
            if not getattr(args, "aggressive_repair", False):
                self.logger.info("Trying aggressive repair recovery")
                from .core.analysis.mesh_repair import repair_mesh
                repaired_mesh, repair_summary = repair_mesh(mesh, aggressive=True)

                if repaired_mesh is not None:
                    return {
                        "mesh": repaired_mesh,
                        "repair_summary": {
                            "operations": [op.operation.value for op in repair_summary.operations_performed],
                            "issues_fixed": repair_summary.issues_fixed,
                            "remaining_issues": repair_summary.remaining_issues,
                            "success": repair_summary.repair_success,
                            "recovery_used": True,
                        }
                    }

        except Exception as recovery_error:
            self.logger.debug(f"Repair recovery failed: {recovery_error}")

        return None

    def _recover_slicing_failure(self, error: Exception, context: Dict[str, Any], attempt: int) -> Optional[Dict[str, Any]]:
        """Recover from slicing failures by adjusting parameters."""
        mesh = context.get("mesh")
        args = context.get("args")
        if not mesh or not args:
            return None

        try:
            # Try with adjusted slicing parameters
            SliceSettings, SlicingEngine = _lazy_import_slicing()[:2]

            # Adjust layer height to be more conservative
            adjusted_height = min(args.layer_height * 1.5, 0.5)
            slice_settings = SliceSettings(
                layer_height=adjusted_height,
                infill_density=max(args.infill * 0.8, 5),  # Reduce infill
                print_speed=max(args.speed * 0.9, 20),  # Reduce speed
            )

            slicer = SlicingEngine(slice_settings)
            slicing_result = slicer.slice_mesh(mesh)

            return {
                "slicing": {
                    "layers": slicing_result.total_layers,
                    "print_time_seconds": slicing_result.total_print_time_seconds,
                    "print_time_hours": slicing_result.total_print_time_seconds / 3600,
                    "material_grams": slicing_result.total_material_grams,
                    "recovery_used": True,
                    "adjusted_layer_height": adjusted_height,
                }
            }

        except Exception as recovery_error:
            self.logger.debug(f"Slicing recovery failed: {recovery_error}")

        return None

    def _recover_gcode_failure(self, error: Exception, context: Dict[str, Any], attempt: int) -> Optional[str]:
        """Recover from G-code generation failures."""
        slicing_result = context.get("slicing_result")
        args = context.get("args")
        if not slicing_result or not args:
            return None

        try:
            # Try with conservative G-code settings
            _, _, GcodeSettings, GcodeGenerator = _lazy_import_slicing()

            gcode_settings = GcodeSettings(
                nozzle_temperature=min(args.temp_nozzle, 220),  # Cap temperature
                bed_temperature=min(args.temp_bed, 70),  # Cap bed temp
                print_speed=min(args.speed, 40),  # Reduce speed
            )

            generator = GcodeGenerator(gcode_settings)
            gcode = generator.generate(slicing_result)

            return gcode

        except Exception as recovery_error:
            self.logger.debug(f"G-code recovery failed: {recovery_error}")

        return None

    def _recover_recommendations_failure(self, error: Exception, context: Dict[str, Any], attempt: int) -> Optional[Dict[str, Any]]:
        """Recover from recommendations failures by using simplified evaluation."""
        validation = context.get("validation")
        if not validation:
            return None

        try:
            # Try simplified recommendations without complex analysis
            return {
                "recommendations": {
                    "rationales": [],
                    "recovery_used": True,
                },
                "readiness": {
                    "score": 50,  # Neutral score
                    "status_en": "Unable to evaluate",
                    "status_ja": "評価できません",
                    "recovery_used": True,
                }
            }

        except Exception as recovery_error:
            self.logger.debug(f"Recommendations recovery failed: {recovery_error}")

        return None


class CLIProcessor:
    """Main CLI processor with all functionality consolidated."""

    def __init__(self):
        # Auto-detect and load configuration
        self.config = self._load_configuration()
        self.logger = get_logger(__name__)
        self.session_id = str(uuid.uuid4())[:8]
        self.max_file_size_bytes = self._resolve_max_file_size()
        self.read_only_output = getattr(self.config.application, "default_read_only_output", False)
        self.roi_settings = self._load_roi_settings()
        self.max_worker_limit = self._compute_max_workers_limit()
        self.max_manifest_bytes = getattr(self.config.application, "max_manifest_bytes", 5 * 1024 * 1024)
        self.max_manifest_entries = getattr(self.config.application, "max_manifest_entries", 2000)
        self.worker_timeout_seconds = getattr(self.config.application, "worker_timeout_seconds", 60.0)
        self.hash_policy = "strict"
        self.hash_manifest_lookup = {}
        self.hash_manifest_required = False
        self.hash_manifest_source = None

        # Initialize error recovery manager
        self.error_recovery = ErrorRecoveryManager(self.logger)
        
        # Initialize parallel processor
        self.parallel_processor = ParallelProcessor(
            logger=self.logger,
            verbose=getattr(self.config.application, "verbose", False)
        )

        # Initialize cache
        self._manifest_cache: Dict[Path, Tuple[float, Dict[str, str]]] = {}
        self._cache_dir = None

        # Initialize i18n manager
        from .core.i18n_optimized import I18nManager
        self.i18n_manager = I18nManager()

        default_language = getattr(self.config.application, "default_language_mode", "bilingual")
        self.language_mode: str = default_language if default_language in {"en", "ja", "bilingual"} else "bilingual"
        self._apply_language_mode(self.language_mode)

    def _load_configuration(self):
        """Auto-detect and load configuration from multiple sources."""
        from .core.config import get_config as original_get_config

        # Determine environment for config selection
        environment = os.environ.get('PRINTCAD_ENV', os.environ.get('FLASK_ENV', 'production'))

        # Configuration file search paths (in priority order)
        config_paths = []

        # 1. Environment variable specified directory
        config_dir_env = os.environ.get('PRINTCAD_CONFIG_DIR')
        if config_dir_env:
            config_paths.extend([
                Path(config_dir_env) / f'printcad-{environment}.yaml',
                Path(config_dir_env) / f'printcad-{environment}.yml',
                Path(config_dir_env) / f'config-{environment}.yaml',
                Path(config_dir_env) / f'config-{environment}.yml',
                Path(config_dir_env) / 'printcad.yaml',
                Path(config_dir_env) / 'printcad.yml',
                Path(config_dir_env) / 'config.yaml',
                Path(config_dir_env) / 'config.yml',
            ])

        # 2. Current working directory
        cwd = Path.cwd()
        config_paths.extend([
            cwd / f'printcad-{environment}.yaml',
            cwd / f'printcad-{environment}.yml',
            cwd / f'.printcad-{environment}.yaml',
            cwd / f'.printcad-{environment}.yml',
            cwd / f'config-{environment}.yaml',
            cwd / f'config-{environment}.yml',
            cwd / 'printcad.yaml',
            cwd / 'printcad.yml',
            cwd / '.printcad.yaml',
            cwd / '.printcad.yml',
            cwd / 'config.yaml',
            cwd / 'config.yml',
        ])

        # 3. User home directory
        home = Path.home()
        config_paths.extend([
            home / f'.printcad-{environment}.yaml',
            home / f'.printcad-{environment}.yml',
            home / f'.config/printcad/{environment}.yaml',
            home / f'.config/printcad/{environment}.yml',
            home / '.printcad.yaml',
            home / '.printcad.yml',
            home / '.config' / 'printcad' / 'config.yaml',
            home / '.config' / 'printcad' / 'config.yml',
        ])

        # 4. System-wide configuration
        if os.name == 'posix':  # Unix-like systems
            config_paths.extend([
                Path(f'/etc/printcad/{environment}.yaml'),
                Path(f'/etc/printcad/{environment}.yml'),
                Path('/etc/printcad/config.yaml'),
                Path('/etc/printcad/config.yml'),
            ])

        # Try to load from discovered paths
        loaded_config = None
        config_path = None

        for candidate_path in config_paths:
            if candidate_path.exists() and candidate_path.is_file():
                try:
                    # Temporarily set environment to force loading from this path
                    original_env = os.environ.get('PRINTCAD_CONFIG_FILE')
                    os.environ['PRINTCAD_CONFIG_FILE'] = str(candidate_path)

                    config = original_get_config()
                    loaded_config = config
                    config_path = candidate_path
                    print(f"Loaded {environment} configuration from: {candidate_path}", file=sys.stderr)
                    break

                except Exception as exc:
                    print(f"Failed to load config from {candidate_path}: {exc}", file=sys.stderr)
                finally:
                    # Restore original environment
                    if original_env is not None:
                        os.environ['PRINTCAD_CONFIG_FILE'] = original_env
                    elif 'PRINTCAD_CONFIG_FILE' in os.environ:
                        del os.environ['PRINTCAD_CONFIG_FILE']

        # Fall back to default configuration
        if loaded_config is None:
            print(f"Using default configuration for {environment} environment", file=sys.stderr)
            loaded_config = original_get_config()

        # Store config metadata for hot reload
        self._config_path = config_path
        self._config_environment = environment
        self._config_mtime = config_path.stat().st_mtime if config_path else None
        self._last_config_check = time.time()

        return loaded_config

    def _check_config_hot_reload(self) -> bool:
        """Check if configuration file has been modified and reload if needed."""
        if not self._config_path or not self._config_path.exists():
            return False

        # Only check every 5 seconds to avoid excessive I/O
        current_time = time.time()
        if current_time - self._last_config_check < 5.0:
            return False

        self._last_config_check = current_time

        try:
            current_mtime = self._config_path.stat().st_mtime
            if current_mtime != self._config_mtime:
                print(f"Configuration file changed, reloading: {self._config_path}", file=sys.stderr)

                # Create backup before reloading
                self._backup_config_file(self._config_path)

                # Reload configuration
                from .core.config import get_config as original_get_config

                original_env = os.environ.get('PRINTCAD_CONFIG_FILE')
                os.environ['PRINTCAD_CONFIG_FILE'] = str(self._config_path)

                try:
                    new_config = original_get_config()
                    self.config = new_config
                    self._config_mtime = current_mtime

                    # Update dependent settings
                    self.max_file_size_bytes = self._resolve_max_file_size()
                    self.read_only_output = getattr(self.config.application, "default_read_only_output", False)
                    self.roi_settings = self._load_roi_settings()
                    self.max_worker_limit = self._compute_max_workers_limit()
                    self.max_manifest_bytes = getattr(self.config.application, "max_manifest_bytes", 5 * 1024 * 1024)
                    self.max_manifest_entries = getattr(self.config.application, "max_manifest_entries", 2000)
                    self._manifest_cache.clear()

                    print("Configuration reloaded successfully", file=sys.stderr)
                    return True

                finally:
                    if original_env is not None:
                        os.environ['PRINTCAD_CONFIG_FILE'] = original_env
                    elif 'PRINTCAD_CONFIG_FILE' in os.environ:
                        del os.environ['PRINTCAD_CONFIG_FILE']

        except Exception as exc:
            print(f"Failed to reload configuration: {exc}", file=sys.stderr)

        return False

    def _backup_config_file(self, config_path: Path) -> None:
        """Create a backup of the configuration file before modification."""
        try:
            # Create backup directory if it doesn't exist
            backup_dir = config_path.parent / ".printcad_backups"
            backup_dir.mkdir(exist_ok=True)

            # Generate backup filename with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_name = f"{config_path.name}.{timestamp}.backup"
            backup_path = backup_dir / backup_name

            # Copy the current config file to backup
            import shutil
            shutil.copy2(config_path, backup_path)

            # Keep only the last 5 backups to avoid disk space issues
            backup_files = sorted(backup_dir.glob(f"{config_path.name}.*.backup"))
            if len(backup_files) > 5:
                for old_backup in backup_files[:-5]:
                    try:
                        old_backup.unlink()
                    except OSError:
                        pass  # Ignore if we can't delete

            print(f"Configuration backup created: {backup_path}", file=sys.stderr)

        except Exception as exc:
            print(f"Warning: Failed to create configuration backup: {exc}", file=sys.stderr)

    def _validate_json_output(self, data: Any) -> Dict[str, Any]:
        """Validate JSON output data structure."""
        try:
            # Basic structure validation
            if not isinstance(data, dict):
                return {"valid": False, "error": "Output must be a JSON object"}

            # Check for required fields based on data type
            if "files" in data:
                # Batch output
                if not isinstance(data["files"], list):
                    return {"valid": False, "error": "files field must be an array"}

                for i, file_result in enumerate(data["files"]):
                    if not isinstance(file_result, dict):
                        return {"valid": False, "error": f"files[{i}] must be an object"}

                    required_fields = ["file", "success", "processing_time"]
                    for field in required_fields:
                        if field not in file_result:
                            return {"valid": False, "error": f"files[{i}] missing required field: {field}"}

            elif "file" in data:
                # Single file output
                required_fields = ["file", "success", "processing_time"]
                for field in required_fields:
                    if field not in data:
                        return {"valid": False, "error": f"missing required field: {field}"}

            elif "summary" in data:
                # Summary output
                if not isinstance(data["summary"], dict):
                    return {"valid": False, "error": "summary field must be an object"}

                required_summary_fields = ["total_files", "successful", "failed", "success_rate"]
                for field in required_summary_fields:
                    if field not in data["summary"]:
                        return {"valid": False, "error": f"summary missing required field: {field}"}

            # Additional validation rules
            validation_issues = []

            # Check data types
            if "files" in data:
                for i, file_result in enumerate(data["files"]):
                    if "processing_time" in file_result:
                        if not isinstance(file_result["processing_time"], (int, float)):
                            validation_issues.append(f"files[{i}].processing_time must be a number")

                    if "success" in file_result:
                        if not isinstance(file_result["success"], bool):
                            validation_issues.append(f"files[{i}].success must be a boolean")

            # Check for invalid field combinations
            if "files" in data and "summary" in data:
                # This is acceptable - combined output
                pass

            if validation_issues:
                return {"valid": False, "error": "; ".join(validation_issues)}

            return {"valid": True, "error": None}

        except Exception as exc:
            return {"valid": False, "error": f"Validation failed with exception: {exc}"}

    def _run_benchmark(self, file_path: Path, iterations: int, args: argparse.Namespace) -> None:
        """Run benchmark on a single file with specified number of iterations."""
        print(f"Benchmarking {file_path.name} with {iterations} iterations...", file=sys.stderr)

        times = []
        memory_deltas = []

        for i in range(iterations):
            print(f"  Iteration {i+1}/{iterations}...", end="", flush=True, file=sys.stderr)

            start_time = time.time()
            start_memory = self._get_current_memory_usage_mb()

            try:
                result = self.process_mesh(file_path, args)

                end_time = time.time()
                end_memory = self._get_current_memory_usage_mb()

                processing_time = end_time - start_time
                memory_delta = end_memory - start_memory

                times.append(processing_time)
                memory_deltas.append(memory_delta)

                success = result.get("success", False)
                status = "✓" if success else "✗"
                print(f" {status} ({processing_time:.2f}s, {memory_delta:+.1f}MB)", file=sys.stderr)

                # Clear cache for next iteration to ensure fair comparison
                if getattr(args, 'enable_cache', False):
                    try:
                        args_dict = vars(args).copy()
                        args_dict.pop('files', None)
                        args_hash = hashlib.sha256(json.dumps(args_dict, sort_keys=True).encode()).hexdigest()[:16]
                        cache_key = self._get_cache_key(file_path, args_hash)
                        self._invalidate_cache_entry(cache_key)
                    except Exception:
                        pass

            except Exception as exc:
                print(f" ✗ (Error: {exc})", file=sys.stderr)
                continue

        if not times:
            print("No successful benchmark iterations", file=sys.stderr)
            return

        # Calculate statistics
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        sorted_times = sorted(times)
        median_time = sorted_times[len(sorted_times) // 2]

        avg_memory = sum(memory_deltas) / len(memory_deltas) if memory_deltas else 0

        print(f"\nBenchmark Results for {file_path.name}:", file=sys.stderr)
        print(f"  Iterations: {len(times)}/{iterations}", file=sys.stderr)
        print(f"  Average time: {avg_time:.3f}s", file=sys.stderr)
        print(f"  Min time: {min_time:.3f}s", file=sys.stderr)
        print(f"  Max time: {max_time:.3f}s", file=sys.stderr)
        print(f"  Median time: {median_time:.3f}s", file=sys.stderr)
        print(f"  Average memory delta: {avg_memory:+.1f}MB", file=sys.stderr)

        # Performance assessment
        if avg_time < 0.1:
            perf = "Excellent (real-time capable)"
        elif avg_time < 1.0:
            perf = "Good (interactive)"
        elif avg_time < 10.0:
            perf = "Fair (batch processing)"
        else:
            perf = "Slow (consider optimization)"

        print(f"  Performance: {perf}", file=sys.stderr)

    def _invalidate_cache_entry(self, cache_key: str) -> None:
        """Invalidate a specific cache entry."""
        try:
            cache_dir = Path.home() / ".3dprintcad" / "cache"
            cache_file = cache_dir / f"{hash(cache_key)}.json"
            if cache_file.exists():
                cache_file.unlink()
        except Exception:
            pass

    def _generate_completion_script(self, shell: str) -> None:
        """Generate shell completion script for the specified shell."""

        script_name = f"printcad-completion.{shell}"

        if shell == "bash":
            script = self._generate_bash_completion()
        elif shell == "zsh":
            script = self._generate_zsh_completion()
        elif shell == "fish":
            script = self._generate_fish_completion()
        else:
            print(f"Unsupported shell: {shell}", file=sys.stderr)
            return

        print(f"# {shell.upper()} completion script for 3D Print CAD Assistant")
        print(f"# Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"# Install: source {script_name}")
        print()
        print(script)

        print(f"\n# To install permanently, add the above to your {shell} completion directory", file=sys.stderr)
        if shell == "bash":
            print(f"# Example: sudo cp {script_name} /etc/bash_completion.d/", file=sys.stderr)
        elif shell == "zsh":
            print(f"# Example: cp {script_name} ~/.zsh/completions/ && echo 'fpath+=~/.zsh/completions' >> ~/.zshrc", file=sys.stderr)

    def _generate_bash_completion(self) -> str:
        """Generate bash completion script."""
        return '''_printcad_complete() {
    local cur prev opts files mesh_files
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Main options
    opts="--help --verbose --quiet --progress --no-progress --batch --parallel --summary --validate --repair --slice --gcode --recommendations --no-recommendations --list-files --list-formats --read-only-output --save-repaired --hash-only --enable-cache --generate-completion"

    # File extensions for mesh files
    mesh_exts=".stl .obj .ply .3mf .amf"

    case "${prev}" in
        --output|--summary-output|--metrics-output|--failure-output|--save-repaired|--hash-manifest|--cdn-resources-file|--config-dir)
            # File path completion
            COMPREPLY=( $(compgen -f -- "${cur}") )
            return 0
            ;;
        --generate-completion)
            COMPREPLY=( $(compgen -W "bash zsh fish" -- "${cur}") )
            return 0
            ;;
        --language)
            COMPREPLY=( $(compgen -W "en ja bilingual" -- "${cur}") )
            return 0
            ;;
        --hash-policy)
            COMPREPLY=( $(compgen -W "strict warn" -- "${cur}") )
            return 0
            ;;
        --input-dir|--upload-dir|--results-dir)
            # Directory completion
            COMPREPLY=( $(compgen -d -- "${cur}") )
            return 0
            ;;
        --pattern)
            # No completion for glob patterns
            return 0
            ;;
        *)
            ;;
    esac

    # If current word starts with dash, complete options
    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
        return 0
    fi

    # Complete mesh files
    if [[ ${cur} == *.* ]]; then
        for ext in $mesh_exts; do
            if [[ ${cur} == *${ext} ]]; then
                COMPREPLY=( $(compgen -f -- "${cur}") )
                return 0
            fi
        done
    fi

    # Default to file completion
    COMPREPLY=( $(compgen -f -- "${cur}") )
}

complete -F _printcad_complete printcad'''

    def _generate_zsh_completion(self) -> str:
        """Generate zsh completion script."""
        return '''#compdef printcad

_printcad() {
    local -a commands options mesh_files
    local curcontext="$curcontext" state line
    typeset -A opt_args

    # Main options
    options=(
        "--help[Show help message]"
        "--verbose[Enable verbose output]"
        "--quiet[Quiet mode]"
        "--progress[Show progress]"
        "--no-progress[Disable progress]"
        "--batch[Batch processing mode]"
        "--parallel[Parallel processing]"
        "--summary[Show summary]"
        "--validate[Validate mesh]"
        "--repair[Repair mesh]"
        "--slice[Generate slices]"
        "--gcode[Generate G-code]"
        "--recommendations[Generate recommendations]"
        "--no-recommendations[Disable recommendations]"
        "--list-files[List files only]"
        "--list-formats[List supported formats]"
        "--read-only-output[Prevent writing files]"
        "--save-repaired[Export repaired mesh]:file:_files"
        "--hash-only[Hash files only]"
        "--enable-cache[Enable result caching]"
        "--generate-completion[Generate completion script]:shell:(bash zsh fish)"
        "--output[Output file]:file:_files"
        "--summary-output[Summary output file]:file:_files"
        "--metrics-output[Metrics output file]:file:_files"
        "--failure-output[Failure output file]:file:_files"
        "--hash-manifest[Hash manifest file]:file:_files"
        "--cdn-resources-file[CDN resources file]:file:_files"
        "--config-dir[Configuration directory]:directory:_directories"
        "--language[Language mode]:(en ja bilingual)"
        "--hash-policy[Hash policy]:(strict warn)"
        "--input-dir[Input directory]:directory:_directories"
        "--upload-dir[Upload directory]:directory:_directories"
        "--results-dir[Results directory]:directory:_directories"
        "--pattern[File pattern]: "
        "--max-workers[Maximum worker count]: "
        "--layer-height[Layer height]: "
        "--infill[Infill density]: "
        "--speed[Print speed]: "
        "--temp-nozzle[Nozzle temperature]: "
        "--temp-bed[Bed temperature]: "
        "--min-wall[Minimum wall thickness]: "
        "--min-feature[Minimum feature size]: "
        "--overhang-angle[Maximum overhang angle]: "
        "--max-file-size[Maximum file size]: "
        "--worker-timeout[Worker timeout]: "
        "--max-warning-count[Maximum warning count]: "
    )

    _arguments -C "$options[@]" "*:mesh files:_files -g '*.stl *.obj *.ply *.3mf *.amf'"
}

_printcad "$@"'''

    def _generate_fish_completion(self) -> str:
        """Generate fish completion script."""
        return '''# Fish completion for 3D Print CAD Assistant

# Main command completion
complete -c printcad -f

# File arguments (mesh files)
complete -c printcad -a "*.stl" -d "STL mesh file"
complete -c printcad -a "*.obj" -d "OBJ mesh file"
complete -c printcad -a "*.ply" -d "PLY mesh file"
complete -c printcad -a "*.3mf" -d "3MF mesh file"
complete -c printcad -a "*.amf" -d "AMF mesh file"

# Boolean flags
complete -c printcad -l help -d "Show help message"
complete -c printcad -l verbose -d "Enable verbose output"
complete -c printcad -l quiet -d "Quiet mode"
complete -c printcad -l progress -d "Show progress"
complete -c printcad -l no-progress -d "Disable progress"
complete -c printcad -l batch -d "Batch processing mode"
complete -c printcad -l parallel -d "Parallel processing"
complete -c printcad -l summary -d "Show summary"
complete -c printcad -l validate -d "Validate mesh"
complete -c printcad -l repair -d "Repair mesh"
complete -c printcad -l slice -d "Generate slices"
complete -c printcad -l gcode -d "Generate G-code"
complete -c printcad -l recommendations -d "Generate recommendations"
complete -c printcad -l no-recommendations -d "Disable recommendations"
complete -c printcad -l list-files -d "List files only"
complete -c printcad -l list-formats -d "List supported formats"
complete -c printcad -l read-only-output -d "Prevent writing files"
complete -c printcad -l hash-only -d "Hash files only"
complete -c printcad -l enable-cache -d "Enable result caching"

# Options with values
complete -c printcad -l output -r -d "Output file"
complete -c printcad -l summary-output -r -d "Summary output file"
complete -c printcad -l metrics-output -r -d "Metrics output file"
complete -c printcad -l failure-output -r -d "Failure output file"
complete -c printcad -l save-repaired -r -d "Export repaired mesh"
complete -c printcad -l hash-manifest -r -d "Hash manifest file"
complete -c printcad -l cdn-resources-file -r -d "CDN resources file"
complete -c printcad -l config-dir -r -d "Configuration directory"
complete -c printcad -l input-dir -r -d "Input directory"
complete -c printcad -l upload-dir -r -d "Upload directory"
complete -c printcad -l results-dir -r -d "Results directory"
complete -c printcad -l pattern -r -d "File pattern"
complete -c printcad -l max-workers -r -d "Maximum worker count"
complete -c printcad -l layer-height -r -d "Layer height (mm)"
complete -c printcad -l infill -r -d "Infill density (%)"
complete -c printcad -l speed -r -d "Print speed (mm/s)"
complete -c printcad -l temp-nozzle -r -d "Nozzle temperature (°C)"
complete -c printcad -l temp-bed -r -d "Bed temperature (°C)"
complete -c printcad -l min-wall -r -d "Minimum wall thickness (mm)"
complete -c printcad -l min-feature -r -d "Minimum feature size (mm)"
complete -c printcad -l overhang-angle -r -d "Maximum overhang angle (°)"
complete -c printcad -l max-file-size -r -d "Maximum file size"
complete -c printcad -l worker-timeout -r -d "Worker timeout (seconds)"
complete -c printcad -l max-warning-count -r -d "Maximum warning count"

# Choice options
complete -c printcad -l language -a "en ja bilingual" -d "Language mode"
complete -c printcad -l hash-policy -a "strict warn" -d "Hash policy"
complete -c printcad -l generate-completion -a "bash zsh fish" -d "Generate completion script"'''

    def _generate_config_template(self, output_path: Path) -> None:
        """Generate a sample configuration file template."""

        template = {
            "#": "3D Print CAD Assistant Configuration Template",
            "#": "Generated on: " + time.strftime('%Y-%m-%d %H:%M:%S'),
            "#": "Copy this file and customize the settings for your environment",
            "#": "",
            "application": {
                "#": "Application-wide settings",
                "environment": "production",  # development, staging, production
                "default_language_mode": "bilingual",  # en, ja, bilingual
                "default_read_only_output": False,
                "max_file_size_mb": 100,
                "max_workers": 4,
                "worker_timeout_seconds": 300.0,
                "#": "ROI calculation settings",
                "manual_review_base_minutes": 8.0,
                "manual_review_per_issue_minutes": 4.0,
                "manual_repair_overhead_minutes": 6.0,
                "manual_slicing_setup_minutes": 7.0,
                "manual_review_cost_rate_usd": 32.0
            },
            "validation": {
                "#": "Mesh validation thresholds",
                "min_wall_thickness_mm": 0.8,
                "min_feature_size_mm": 0.4,
                "max_overhang_angle_deg": 45,
                "max_aspect_ratio": 100.0,
                "min_bed_adhesion_area_cm2": 10.0
            },
            "processing": {
                "#": "Processing settings",
                "default_layer_height_mm": 0.2,
                "default_infill_density_percent": 15,
                "default_print_speed_mm_per_sec": 50,
                "default_nozzle_temp_celsius": 200,
                "default_bed_temp_celsius": 60,
                "enable_parallel_processing": True,
                "batch_progress_update_interval": 1.0
            },
            "logging": {
                "#": "Logging configuration",
                "log_level": "INFO",  # DEBUG, INFO, WARNING, ERROR
                "enable_file_logging": False,
                "log_file_path": "logs/printcad.log",
                "max_log_file_size_mb": 10,
                "log_retention_days": 30,
                "redaction_rules": [
                    "api_key",
                    "password",
                    "secret",
                    "token"
                ]
            },
            "security": {
                "#": "Security settings",
                "enforce_hash_manifest": True,
                "hash_policy": "strict",  # strict, warn
                "path_safety_enforced": True,
                "symlink_protection_enforced": True,
                "input_validation_enabled": True,
                "rate_limiting_enabled": True
            },
            "output": {
                "#": "Output settings",
                "default_output_format": "json",  # json, jsonl, text
                "include_timestamps": True,
                "include_processing_metadata": True,
                "compress_large_outputs": False,
                "output_encoding": "utf-8"
            },
            "cache": {
                "#": "Caching settings",
                "enable_result_caching": False,
                "cache_directory": "~/.3dprintcad/cache",
                "cache_max_age_hours": 24,
                "cache_max_size_mb": 100,
                "cache_compression_enabled": True
            },
            "reporting": {
                "#": "Reporting settings",
                "generate_detailed_reports": True,
                "include_visualizations": False,
                "report_format": "html",  # html, json, pdf
                "email_notifications_enabled": False,
                "report_retention_days": 90
            },
            "integration": {
                "#": "External service integrations",
                "collab_api_enabled": False,
                "collab_base_url": "",
                "collab_ws_url": "",
                "cdn_resources_enabled": True,
                "cdn_resources_file": "",
                "webhook_notifications_enabled": False,
                "webhook_url": ""
            }
        }

        # Convert to YAML format
        try:
            import yaml
            yaml_content = yaml.dump(template, default_flow_style=False, allow_unicode=True, sort_keys=False)
        except ImportError:
            # Fallback to JSON if yaml is not available
            import json
            yaml_content = json.dumps(template, indent=2, ensure_ascii=False)

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the template
        output_path.write_text(yaml_content, encoding='utf-8')

        print(f"Configuration template generated: {output_path}", file=sys.stderr)
        print(f"You can now edit this file and use it with --config-dir or PRINTCAD_CONFIG_DIR", file=sys.stderr)

        # Show usage examples
        print(f"\nUsage examples:", file=sys.stderr)
        print(f"  printcad --config-dir {output_path.parent}", file=sys.stderr)
        print(f"  PRINTCAD_CONFIG_DIR={output_path.parent} printcad model.stl", file=sys.stderr)

    def _compare_config_files(self, config1_path: str, config2_path: str) -> None:
        """Compare two configuration files and show differences."""
        try:
            import yaml
            loader = yaml.FullLoader
        except ImportError:
            import json
            loader = json.loads

        # Load first config
        try:
            with open(config1_path, 'r', encoding='utf-8') as f:
                if config1_path.endswith(('.yaml', '.yml')):
                    try:
                        config1 = yaml.load(f, Loader=loader)
                    except ImportError:
                        # Fallback to JSON if YAML not available
                        import json
                        f.seek(0)
                        config1 = json.load(f)
                else:
                    import json
                    config1 = json.load(f)
        except Exception as exc:
            print(f"Error loading {config1_path}: {exc}", file=sys.stderr)
            return

        # Load second config
        try:
            with open(config2_path, 'r', encoding='utf-8') as f:
                if config2_path.endswith(('.yaml', '.yml')):
                    try:
                        config2 = yaml.load(f, Loader=loader)
                    except ImportError:
                        import json
                        f.seek(0)
                        config2 = json.load(f)
                else:
                    import json
                    config2 = json.load(f)
        except Exception as exc:
            print(f"Error loading {config2_path}: {exc}", file=sys.stderr)
            return

        # Compare configurations
        differences = self._compare_dicts(config1, config2)

        print(f"Configuration comparison: {config1_path} vs {config2_path}")
        print("=" * 80)

        if not differences:
            print("✓ Configurations are identical")
            return

        # Group differences by type
        added = [d for d in differences if d['type'] == 'added']
        removed = [d for d in differences if d['type'] == 'removed']
        modified = [d for d in differences if d['type'] == 'modified']

        if added:
            print(f"\n📄 Added in {config2_path}:")
            for diff in added:
                print(f"  + {diff['path']}: {diff['value2']}")

        if removed:
            print(f"\n🗑️  Removed from {config2_path}:")
            for diff in removed:
                print(f"  - {diff['path']}: {diff['value1']}")

        if modified:
            print(f"\n🔄 Modified:")
            for diff in modified:
                print(f"  ~ {diff['path']}:")
                print(f"    {config1_path}: {diff['value1']}")
                print(f"    {config2_path}: {diff['value2']}")

        print(f"\nSummary: {len(added)} added, {len(removed)} removed, {len(modified)} modified")

    def _compare_dicts(self, dict1: Dict[str, Any], dict2: Dict[str, Any], path: str = "") -> List[Dict[str, Any]]:
        """Compare two dictionaries recursively and return differences."""
        differences = []

        # Get all keys from both dictionaries
        all_keys = set(dict1.keys()) | set(dict2.keys())

        for key in all_keys:
            current_path = f"{path}.{key}" if path else key

            if key not in dict1:
                # Key added in dict2
                differences.append({
                    'type': 'added',
                    'path': current_path,
                    'value1': None,
                    'value2': dict2[key]
                })
            elif key not in dict2:
                # Key removed from dict2
                differences.append({
                    'type': 'removed',
                    'path': current_path,
                    'value1': dict1[key],
                    'value2': None
                })
            else:
                # Key exists in both
                val1, val2 = dict1[key], dict2[key]

                if isinstance(val1, dict) and isinstance(val2, dict):
                    # Recursively compare nested dictionaries
                    nested_diffs = self._compare_dicts(val1, val2, current_path)
                    differences.extend(nested_diffs)
                elif val1 != val2:
                    # Values differ
                    differences.append({
                        'type': 'modified',
                        'path': current_path,
                        'value1': val1,
                        'value2': val2
                    })

        return differences

    def _resolve_max_file_size(self) -> Optional[int]:
        """Derive max allowable file size in bytes from configuration."""
        try:
            application_config = getattr(self.config, "application", None)
            size_mb = getattr(application_config, "max_file_size_mb", None)
            if size_mb is None:
                return None
            return int(size_mb) * 1024 * 1024
        except Exception:  # pragma: no cover - defensive fallback
            return None

    def _compute_max_workers_limit(self) -> int:
        """Determine safe upper bound for worker processes."""
        cpu_count = os.cpu_count() or multiprocessing.cpu_count()
        cpu_count = max(1, cpu_count)
        return min(32, cpu_count * 2)

    def _load_roi_settings(self) -> Dict[str, float]:
        """Load ROI heuristic values from configuration with safe defaults."""

        application_config = getattr(self.config, "application", None)
        defaults = {
            "manual_review_base_minutes": 8.0,
            "manual_review_per_issue_minutes": 4.0,
            "manual_repair_overhead_minutes": 6.0,
            "manual_slicing_setup_minutes": 7.0,
            "manual_review_cost_rate_usd": 32.0,
        }

        if not application_config:
            return defaults

        settings = {}
        for key, fallback in defaults.items():
            value = getattr(application_config, key, fallback)
            try:
                settings[key] = float(value)
            except (TypeError, ValueError):
                settings[key] = fallback

        return settings

    def _estimate_manual_minutes_saved(self, result: Dict[str, Any]) -> float:
        """Estimate manual effort saved by automation."""

        minutes = self.roi_settings["manual_review_base_minutes"]
        issue_count = len(result.get("issues", []) or [])
        minutes += issue_count * self.roi_settings["manual_review_per_issue_minutes"]

        if result.get("repaired"):
            minutes += self.roi_settings["manual_repair_overhead_minutes"]

        if result.get("gcode_file") or result.get("gcode_lines"):
            minutes += self.roi_settings["manual_slicing_setup_minutes"]

        return minutes

    def _compliance_metadata(self) -> Dict[str, Any]:
        """Generate compliance metadata snapshot for reports."""

        return {
            "path_safety_enforced": True,
            "symlink_protection_enforced": True,
            "max_file_size_bytes": self.max_file_size_bytes,
            "hash_chunk_bytes": DEFAULT_HASH_CHUNK_SIZE,
            "policy_reference": "printcad-compliance-2025-09"
        }

    def _validate_output_path(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        """Ensure output path is safe and uses an expected extension."""
        if not args.output:
            return

        if self.read_only_output:
            parser.error("--read-only-output cannot be combined with --output")

        raw_output = args.output.expanduser()
        if ".." in raw_output.parts:
            parser.error("Parent directory traversal detected in --output path")

        target_directory = raw_output.parent if raw_output.suffix else raw_output

        try:
            resolved_directory = target_directory.resolve(strict=True)
        except FileNotFoundError:
            parser.error("Directory for --output does not exist")

        if resolved_directory.is_symlink():
            parser.error("Output directory cannot be a symbolic link")

        if not resolved_directory.is_dir():
            parser.error("--output parent must be a directory")

        allowed_root = getattr(self.config.application, "allowed_output_root", None)
        if allowed_root:
            try:
                allowed_base = Path(allowed_root).expanduser().resolve(strict=True)
            except FileNotFoundError:
                parser.error("Configured output root does not exist; update application.allowed_output_root")

            try:
                self._assert_within_base(resolved_directory, allowed_base)
            except ValueError:
                parser.error("--output path is outside the allowed output root")

        if not raw_output.suffix:
            parser.error("--output file must include an extension")

        if args.gcode:
            if raw_output.suffix.lower() != ".gcode":
                parser.error("--output must point to a .gcode file")
        elif raw_output.suffix.lower() != ".json":
            parser.error("--output must point to a .json file")

        args.output = (resolved_directory / raw_output.name).resolve()
        if args.output.is_dir():
            parser.error("--output must point to a file, not a directory")

    def _validate_candidate_file(self, path: Path, hints: List[str]) -> Optional[Path]:
        """Validate mesh file safety constraints before processing."""
        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError:
            hints.append(f"File not found: {path}")
            return None

        if resolved.is_symlink():
            hints.append(f"Skipped symbolic link: {resolved}")
            return None

        allowed_roots = getattr(self.config.application, "allowed_input_roots", []) or []
        if allowed_roots:
            allowed_paths = []
            for root in allowed_roots:
                try:
                    allowed_paths.append(Path(root).expanduser().resolve(strict=True))
                except FileNotFoundError:
                    hints.append(f"Configured allowed input root not found: {root}")
            if allowed_paths:
                try:
                    next(
                        base for base in allowed_paths
                        if self._is_within_base(resolved, base)
                    )
                except StopIteration:
                    hints.append(f"Skipped {resolved}: outside allowed input roots")
                    return None
            else:
                hints.append("No allowed input roots are currently resolvable; denying access")
                return None

        # Guard against parent traversal escaping workspace
        if any(part == ".." for part in resolved.parts):
            hints.append(f"Skipped unsafe path traversal: {resolved}")
            return None

        if self.max_file_size_bytes is not None:
            try:
                file_size = resolved.stat().st_size
            except OSError as exc:  # pragma: no cover - filesystem error
                hints.append(f"Failed to read file size for {resolved}: {exc}")
                return None

            if file_size > self.max_file_size_bytes:
                size_mb = file_size / (1024 * 1024)
                limit_mb = self.max_file_size_bytes / (1024 * 1024)
                hints.append(
                    f"Skipped {resolved}: size {size_mb:.1f} MB exceeds limit {limit_mb:.1f} MB"
                )
                return None

        return resolved

    def _ensure_within_size_limit(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Check whether a mesh file respects configured size limits."""
        if self.max_file_size_bytes is None:
            return True, None

        try:
            size_bytes = file_path.stat().st_size
        except OSError as exc:
            return False, f"Failed to check file size: {exc}"

        if size_bytes > self.max_file_size_bytes:
            size_mb = size_bytes / (1024 * 1024)
            limit_mb = self.max_file_size_bytes / (1024 * 1024)
            return False, (
                f"File size {size_mb:.1f} MB exceeds configured limit {limit_mb:.1f} MB"
            )

        return True, None

    def parse_args(self, argv: Optional[list[str]] = None) -> argparse.Namespace:
        """Build and parse arguments."""
        parser = argparse.ArgumentParser(
            prog="printcad",
            description="3D Print CAD Assistant - Validate, repair, and optimize 3D models for additive manufacturing",
            epilog="""
Examples:
  # Basic validation
  printcad model.stl

  # Batch processing with parallel execution
  printcad --batch "models/*.stl" --parallel --max-workers 4

  # Advanced analysis with repair and slicing
  printcad model.stl --repair --slice --gcode --layer-height 0.15

  # Quality control with custom thresholds
  printcad model.stl --min-wall 1.0 --min-feature 0.5 --overhang-angle 45

  # Compliance and security
  printcad model.stl --hash-manifest manifest.json --enable-cache

  # Export results
  printcad model.stl --output results.json --summary-output summary.json

  # Batch with detailed reporting
  printcad --batch "*.stl" --summary --metrics-output metrics.jsonl --failure-output failures.json

Environment Variables:
  SECRET_KEY              Flask session encryption key
  MAX_UPLOAD_MB          Maximum file size (default: 100MB)
  MAX_BATCH_FILES        Maximum files in batch (default: 20)
  UPLOAD_DIR             Upload directory path
  RESULTS_DIR            Results directory path
  PRINTCAD_COLLAB_BASE_URL Collaboration API base URL

Configuration Files:
  Search order: working directory, PRINTCAD_CONFIG_DIR, embedded defaults
  Format: YAML with sections for application, validation, processing, logging
            """,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        # Input files
        parser.add_argument("files", nargs="*", help="Mesh file(s) to process")
        parser.add_argument("--pattern", type=str, help="Glob pattern for files")
        parser.add_argument("--input-dir", type=Path, help="Directory to scan")

        # Output
        parser.add_argument("-o", "--output", type=Path, help="Output file")
        parser.add_argument(
            "--export-format",
            choices=["json", "jsonl", "csv", "xml"],
            default="json",
            help="Export format for results (default: json)"
        )

        # Processing modes
        parser.add_argument(
            "--save-history",
            action="store_true",
            help="Save processing results to history file"
        )
        parser.add_argument(
            "--show-history",
            nargs="?",
            const="recent",
            choices=["recent", "all", "summary"],
            help="Show processing history (recent, all, or summary)"
        )
        parser.add_argument(
            "-w",
            "--max-workers",
            type=int,
            default=min(4, self.max_worker_limit),
            help="Worker count",
        )

        # Operations
        parser.add_argument("--validate", action="store_true", default=True, help="Validate mesh")
        parser.add_argument("--repair", action="store_true", help="Repair mesh")
        parser.add_argument("--aggressive-repair", action="store_true", help="Aggressive repair")
        parser.add_argument("--slice", action="store_true", help="Generate slices")
        parser.add_argument("--gcode", action="store_true", help="Generate G-code")
        parser.add_argument("--recommendations", action="store_true", default=True, help="Generate recommendations")
        parser.add_argument("--no-recommendations", action="store_false", dest="recommendations")

        # Settings
        parser.add_argument("--layer-height", type=float, default=0.2, help="Layer height (mm) [default: 0.2]")
        parser.add_argument("--infill", type=float, default=15, help="Infill density (%%) [default: 15]")
        parser.add_argument("--speed", type=float, default=50, help="Print speed (mm/s) [default: 50]")
        parser.add_argument("--temp-nozzle", type=float, default=200, help="Nozzle temp (°C) [default: 200]")
        parser.add_argument("--temp-bed", type=float, default=60, help="Bed temp (°C) [default: 60]")

        # Validation thresholds
        parser.add_argument("--min-wall", type=float, default=0.8, help="Min wall thickness (mm) [default: 0.8]")
        parser.add_argument("--min-feature", type=float, default=0.4, help="Min feature size (mm) [default: 0.4]")
        parser.add_argument("--overhang-angle", type=float, default=45, help="Max overhang angle (°) [default: 45]")

        # Output control
        parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
        parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode")
        parser.add_argument("--progress", action="store_true", default=True, help="Show progress")
        parser.add_argument("--no-progress", action="store_false", dest="progress")
        parser.add_argument("--summary", action="store_true", help="Show summary")
        parser.add_argument("--list-files", action="store_true", help="List files only")
        parser.add_argument("--list-formats", action="store_true", help="List supported formats")
        parser.add_argument("--filter-success", action="store_true", help="Show only successful results")
        parser.add_argument("--filter-failed", action="store_true", help="Show only failed results")
        parser.add_argument("--filter-warnings", action="store_true", help="Show only results with warnings")
        parser.add_argument("--filter-errors", action="store_true", help="Show only results with errors")
        parser.add_argument("--filter-cached", action="store_true", help="Show only cached results")
        parser.add_argument("--help-config", action="store_true", help="Show configuration help and current settings")
        parser.add_argument("--help-examples", action="store_true", help="Show detailed usage examples")
        parser.add_argument(
            "--validate-output",
            action="store_true",
            help="Validate JSON output against schema before writing"
        )
        parser.add_argument(
            "--language",
            choices=["en", "ja", "bilingual"],
            default=self.language_mode,
            help="Output language (en, ja, or bilingual)",
        )
        parser.add_argument(
            "--fail-on-warnings",
            action="store_true",
            help="Treat validation warnings as failures to enforce strict automation",
        )
        parser.add_argument(
            "--compare-config",
            nargs=2,
            metavar=("CONFIG1", "CONFIG2"),
            help="Compare two configuration files and show differences"
        )
        parser.add_argument(
            "--auto-summary",
            action="store_true",
            help="Automatically create a session summary JSON in the working directory",
        )
        parser.add_argument(
            "--max-risk-score",
            type=float,
            help="Fail run if computed risk score exceeds the specified value",
        )
        parser.add_argument(
            "--metrics-output",
            type=Path,
            help="Write per-file metrics to a JSONL or JSON file",
        )
        parser.add_argument(
            "--auto-metrics",
            action="store_true",
            help="Automatically create a per-run metrics JSONL in the working directory",
        )
        parser.add_argument(
            "--min-readiness-score",
            type=float,
            help="Fail run if readiness score falls below the specified minimum",
        )
        parser.add_argument(
            "--exit-on-first-failure",
            action="store_true",
            help="Stop processing additional files after the first failure",
        )
        parser.add_argument(
            "--max-warning-count",
            type=int,
            help="Fail run if warning count exceeds the specified maximum",
        )
        parser.add_argument(
            "--failure-output",
            type=Path,
            help="Write list of failed files and details to the specified JSON file",
        )
        parser.add_argument(
            "--benchmark",
            type=int,
            help="Run benchmark with specified number of iterations on first file"
        )
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help="Set logging level (overrides config)"
        )

        # Advanced options
        parser.add_argument("--hash-only", action="store_true", help="Hash files only")
        parser.add_argument(
            "--hash-manifest",
            type=Path,
            help="Path to JSON manifest containing expected SHA-256 digests"
        )
        parser.add_argument(
            "--hash-policy",
            choices=["strict", "warn"],
            default="strict",
            help="Control hash-manifest enforcement: strict (default) or warn",
        )
        parser.add_argument(
            "--worker-timeout",
            type=float,
            default=self.worker_timeout_seconds,
            help="Maximum seconds to wait for a worker result before triggering a watchdog fallback",
        )

        args = parser.parse_args(argv)

        # Auto-load environment variables
        self._load_environment_variables(args)

        # Validate arguments
        self._validate_argument_encoding(parser, args)
        self._validate_args(parser, args)
        self.hash_policy = getattr(args, "hash_policy", "strict")
        self.worker_timeout_seconds = max(args.worker_timeout, 0.0)
        self._apply_language_mode(getattr(args, "language", "bilingual"))

        return args

    def _load_environment_variables(self, args: argparse.Namespace) -> None:
        """Auto-load environment variables into args if not already set."""

        # Environment variable mappings
        env_mappings = {
            'MAX_UPLOAD_MB': ('max_upload_mb', int),
            'MAX_BATCH_FILES': ('max_batch_files', int),
            'UPLOAD_DIR': ('upload_dir', lambda x: Path(x).expanduser()),
            'RESULTS_DIR': ('results_dir', lambda x: Path(x).expanduser()),
            'SECRET_KEY': ('secret_key', str),
            'PRINTCAD_COLLAB_BASE_URL': ('collab_base_url', str),
            'PRINTCAD_COLLAB_WS_URL': ('collab_ws_url', str),
            'CDN_RESOURCES_FILE': ('cdn_resources_file', lambda x: Path(x).expanduser()),
            'PRINTCAD_CONFIG_DIR': ('config_dir', lambda x: Path(x).expanduser()),
            'ALLOWED_UPLOAD_MIMETYPES': ('allowed_mimetypes', str),
        }

        for env_var, (arg_name, converter) in env_mappings.items():
            if env_var in os.environ and getattr(args, arg_name, None) is None:
                try:
                    env_value = os.environ[env_var]
                    if env_value:  # Only set if not empty
                        converted_value = converter(env_value)
                        setattr(args, arg_name, converted_value)
                        self.logger.debug(f"Loaded {env_var} from environment as {arg_name}")
                except (ValueError, TypeError, OSError) as exc:
                    self.logger.warning(f"Failed to parse environment variable {env_var}: {exc}")

        # Special handling for boolean flags
        if os.environ.get('PRINTCAD_READ_ONLY_OUTPUT', '').lower() in ('1', 'true', 'yes'):
            args.read_only_output = True

        if os.environ.get('PRINTCAD_ENABLE_CACHE', '').lower() in ('1', 'true', 'yes'):
            args.enable_cache = True

        if os.environ.get('PRINTCAD_VERBOSE', '').lower() in ('1', 'true', 'yes'):
            args.verbose = True

        if os.environ.get('PRINTCAD_QUIET', '').lower() in ('1', 'true', 'yes'):
            args.quiet = True

    def _validate_argument_encoding(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        """Detect mixed encodings or invalid Unicode sequences in CLI arguments with enhanced security."""

        def _validate_entry(value: Any, label: str) -> None:
            if value is None:
                return

            if isinstance(value, (list, tuple, set)):
                for idx, entry in enumerate(value):
                    _validate_entry(entry, f"{label}[{idx}]")
                return

            if isinstance(value, Path):
                text = str(value)
            else:
                text = str(value)

            if not text:
                return

            # Enhanced security checks
            # Reject embedded NULLs or control characters that may indicate tampering
            for ch in text:
                code_point = ord(ch)
                if ch == "\u0000" or (code_point < 32 and ch not in {"\t", "\n", "\r"}):
                    parser.error(f"{label} contains disallowed control characters")

                if 0xD800 <= code_point <= 0xDFFF:
                    parser.error(f"{label} contains invalid Unicode surrogate code points")

            if "\ufffd" in text:
                parser.error(f"{label} contains Unicode replacement characters -- mixed encoding detected")

            try:
                text.encode("utf-8", errors="strict")
            except UnicodeEncodeError:
                parser.error(f"{label} includes characters that cannot be safely encoded as UTF-8")

            normalized = unicodedata.normalize("NFC", text)
            if normalized != text:
                parser.error(f"{label} is not in NFC-normalized form; mixed encoding detected")

            # Additional security checks for file paths and arguments
            if label in ["files", "pattern", "input_dir", "output", "summary_output", "metrics_output", "failure_output", "save_repaired", "hash_manifest"]:
                # Check for suspicious patterns that might indicate encoding attacks
                suspicious_patterns = [
                    # Double-encoded characters or homoglyph attacks
                    r'[^\x00-\x7F]',  # Non-ASCII characters in file paths can be suspicious
                    # Check for potential shell injection patterns
                    r'[;&|`$()]',
                    # Check for suspicious Unicode ranges that might be used for obfuscation
                    r'[\u200B-\u200D\uFEFF]',  # Zero-width characters
                    r'[\u0300-\u036f]',  # Combining diacritical marks
                ]

                for pattern in suspicious_patterns:
                    if re.search(pattern, text):
                        parser.error(f"{label} contains suspicious characters that may indicate encoding attack: {pattern}")

        _validate_entry(args.files, "files")
        _validate_entry(getattr(args, "pattern", None), "pattern")
        _validate_entry(getattr(args, "input_dir", None), "input_dir")
        _validate_entry(getattr(args, "output", None), "output")
        _validate_entry(getattr(args, "summary_output", None), "summary_output")
        _validate_entry(getattr(args, "metrics_output", None), "metrics_output")
        _validate_entry(getattr(args, "failure_output", None), "failure_output")
        _validate_entry(getattr(args, "save_repaired", None), "save_repaired")
        _validate_entry(getattr(args, "hash_manifest", None), "hash_manifest")
        _validate_entry(getattr(args, "language", None), "language")

    def _validate_args(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        """Validate CLI arguments."""
        # Validate numeric ranges
        if args.min_wall and not (MIN_THRESHOLD_MM <= args.min_wall <= MAX_THRESHOLD_MM):
            parser.error(f"--min-wall must be between {MIN_THRESHOLD_MM} and {MAX_THRESHOLD_MM}")

        if args.min_feature and not (MIN_THRESHOLD_MM <= args.min_feature <= MAX_THRESHOLD_MM):
            parser.error(f"--min-feature must be between {MIN_THRESHOLD_MM} and {MAX_THRESHOLD_MM}")

        if args.overhang_angle and not (0 <= args.overhang_angle <= 85):
            parser.error("--overhang-angle must be between 0 and 85 degrees")

        if args.layer_height and not (0.05 <= args.layer_height <= 1.0):
            parser.error("--layer-height must be between 0.05 and 1.0 mm")

        if args.infill and not (0 <= args.infill <= 100):
            parser.error("--infill must be between 0 and 100%")

        # Validate workers
        if args.max_workers < 1:
            parser.error("--max-workers must be at least 1")

        if args.max_workers and not args.parallel:
            parser.error("--max-workers requires --parallel")

        if args.parallel and not args.batch:
            parser.error("--parallel requires --batch")

        if args.max_workers > self.max_worker_limit:
            print(
                f"--max-workers requested {args.max_workers} but limit is {self.max_worker_limit}; using {self.max_worker_limit}.",
                file=sys.stderr,
            )
            args.max_workers = self.max_worker_limit

        if getattr(args, "exit_on_first_failure", False) and args.parallel:
            parser.error("--exit-on-first-failure cannot be combined with --parallel")

        if getattr(args, "worker_timeout", None) is not None and args.worker_timeout <= 0:
            parser.error("--worker-timeout must be positive")

        # Validate file requirements
        source_count = len(args.files or []) + (1 if args.pattern else 0) + (1 if args.input_dir else 0)
        if args.batch and source_count < 2:
            parser.error("--batch requires multiple mesh paths")

        if args.pattern and not args.batch:
            parser.error("--pattern requires --batch")

        if args.aggressive_repair and not args.repair:
            args.repair = True

        if getattr(args, "save_repaired", None) and not args.repair:
            parser.error("--save-repaired requires --repair")

        # Enhanced consistency validation
        if args.layer_height and args.min_feature and args.layer_height > args.min_feature:
            parser.error("--layer-height should not exceed --min-feature for printability")

        if args.layer_height and args.min_wall and args.layer_height > args.min_wall:
            parser.error("--layer-height should not exceed --min-wall for structural integrity")

        # Validate temperature ranges for common materials
        if args.temp_nozzle and not (150 <= args.temp_nozzle <= 300):
            parser.error("--temp-nozzle must be between 150°C and 300°C")

        if args.temp_bed and not (0 <= args.temp_bed <= 150):
            parser.error("--temp-bed must be between 0°C and 150°C")

        # Validate speed ranges
        if args.speed and not (10 <= args.speed <= 200):
            parser.error("--speed must be between 10 and 200 mm/s")

        # Validate hash manifest path if provided
        if getattr(args, "hash_manifest", None):
            manifest_path = Path(args.hash_manifest).expanduser()
            if not manifest_path.exists():
                parser.error(f"Hash manifest file does not exist: {manifest_path}")
            if not manifest_path.is_file():
                parser.error(f"Hash manifest must be a file: {manifest_path}")

        if getattr(args, "read_only_output", False):
            self.read_only_output = True
            if getattr(args, "save_repaired", None):
                parser.error("--read-only-output cannot be combined with --save-repaired")
            if args.output:
                parser.error("--read-only-output cannot be combined with --output")
        elif getattr(self.config.application, "default_read_only_output", False):
            self.read_only_output = True

        if getattr(args, "save_repaired", None):
            save_path = args.save_repaired.expanduser()
            if ".." in save_path.parts:
                parser.error("--save-repaired path cannot contain parent directory traversal")
            if save_path.suffix.lower() not in MESH_EXTENSIONS:
                parser.error("--save-repaired must use a supported mesh extension")
            save_parent = save_path.parent
            if save_parent.exists():
                resolved_parent = save_parent.resolve()
                if resolved_parent.is_symlink():
                    parser.error("--save-repaired parent directory cannot be a symbolic link")

        # Detect unsafe file inputs
        for file_arg in args.files or []:
            file_path = Path(file_arg)
            if ".." in file_path.parts:
                parser.error("Parent directory traversal detected in input paths")
            if file_path.is_symlink():
                parser.error("Symbolic links are not permitted")

        if args.pattern and ".." in Path(args.pattern).parts:
            parser.error("Parent directory traversal detected in pattern")

        if getattr(args, "max_risk_score", None) is not None:
            if args.max_risk_score < 0:
                parser.error("--max-risk-score must be non-negative")

        if getattr(args, "min_readiness_score", None) is not None:
            if not (0 <= args.min_readiness_score <= 100):
                parser.error("--min-readiness-score must be between 0 and 100")

        if getattr(args, "max_warning_count", None) is not None and args.max_warning_count < 0:
            parser.error("--max-warning-count must be non-negative")

        self._maybe_prepare_auto_metrics(parser, args)
        self._validate_metrics_output(parser, args)
        self._maybe_prepare_auto_failures(parser, args)
        self._validate_failure_output(parser, args)
        self._validate_output_path(parser, args)
        self._maybe_prepare_auto_summary(parser, args)
        self._validate_summary_output(parser, args)
        self._configure_hash_manifest(parser, args)

    def _configure_hash_manifest(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        """Validate and load hash manifest when provided."""

        manifest_path = getattr(args, "hash_manifest", None)
        self.hash_policy = getattr(args, "hash_policy", self.hash_policy)

        # Check if hash manifest requirement can be disabled via configuration
        enforce_required = getattr(self.config.application, "enforce_hash_manifest", True)
        allow_optional = getattr(self.config.application, "allow_optional_hash_manifest", False)

        if self.hash_policy != "strict" and enforce_required:
            parser.error("Configuration requires strict hash manifest enforcement; remove --hash-policy warn")

        if not manifest_path:
            if enforce_required and not allow_optional:
                parser.error("A hash manifest is required by default security policy. Use --hash-manifest to specify one, or set application.allow_optional_hash_manifest=true to disable this requirement.")
            self.hash_manifest_lookup = {}
            self.hash_manifest_required = False
            self.hash_manifest_source = None
            return

        self._apply_language_mode(getattr(args, "language", "bilingual"))

        manifest_candidate = manifest_path.expanduser()
        if ".." in manifest_candidate.parts:
            parser.error("--hash-manifest path cannot contain parent directory traversal")

        try:
            resolved_manifest = manifest_candidate.resolve(strict=True)
        except FileNotFoundError:
            parser.error("Hash manifest file not found")

        if resolved_manifest.is_dir():
            parser.error("--hash-manifest must point to a file")

        if resolved_manifest.is_symlink():
            parser.error("--hash-manifest cannot reference a symbolic link")

        manifest_stat = resolved_manifest.stat()
        if self.max_manifest_bytes and manifest_stat.st_size > self.max_manifest_bytes:
            parser.error("Hash manifest exceeds configured size limit")

        cache_entry = self._manifest_cache.get(resolved_manifest)
        if cache_entry and cache_entry[0] == manifest_stat.st_mtime:
            manifest_lookup = dict(cache_entry[1])
        else:
            try:
                manifest_lookup = self._load_hash_manifest(resolved_manifest)
            except ValueError as exc:
                parser.error(f"Invalid hash manifest: {exc}")

            if self.max_manifest_entries and len(manifest_lookup) > self.max_manifest_entries:
                parser.error("Hash manifest contains more entries than permitted")

            self._manifest_cache[resolved_manifest] = (manifest_stat.st_mtime, manifest_lookup)

        self.hash_manifest_lookup = dict(manifest_lookup)
        self.hash_manifest_required = self.hash_policy == "strict" or enforce_required
        self.hash_manifest_source = resolved_manifest
        args.hash_manifest = resolved_manifest

    def _validate_summary_output(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        summary_target = getattr(args, "summary_output", None)
        if not summary_target:
            return

        if getattr(args, "read_only_output", False) or self.read_only_output:
            parser.error("--summary-output cannot be used when read-only output is enforced")

        summary_path = summary_target.expanduser()
        if ".." in summary_path.parts:
            parser.error("--summary-output path cannot contain parent directory traversal")

        if summary_path.suffix.lower() != ".json":
            parser.error("--summary-output must point to a .json file")

        summary_parent = summary_path.parent
        if not summary_parent.exists():
            parser.error("Directory for --summary-output does not exist")

        if summary_parent.is_symlink():
            parser.error("--summary-output directory cannot be a symbolic link")

    def _maybe_prepare_auto_summary(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        if not getattr(args, "auto_summary", False):
            return

        if getattr(args, "summary_output", None):
            return

        if getattr(args, "read_only_output", False) or self.read_only_output:
            parser.error("--auto-summary cannot be used when read-only output is enforced")

        preferred_dir = getattr(self.config.application, "auto_summary_directory", None)
        if preferred_dir:
            base_dir = Path(preferred_dir).expanduser()
        else:
            base_dir = Path.cwd() / "reports"

        try:
            resolved_base = base_dir.resolve(strict=False)
        except FileNotFoundError:
            resolved_base = base_dir

        if resolved_base.exists() and resolved_base.is_symlink():
            parser.error("Auto summary directory cannot be a symbolic link")

        try:
            resolved_base.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            parser.error(f"Failed to prepare auto summary directory: {exc}")

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        auto_summary_path = resolved_base / f"summary_{self.session_id}_{timestamp}.json"
        args.summary_output = auto_summary_path

    def _validate_metrics_output(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        metrics_target = getattr(args, "metrics_output", None)
        if not metrics_target:
            return

        if getattr(args, "read_only_output", False) or self.read_only_output:
            parser.error("--metrics-output cannot be used when read-only output is enforced")

        metrics_path = metrics_target.expanduser()
        if ".." in metrics_path.parts:
            parser.error("--metrics-output path cannot contain parent directory traversal")

        extension = metrics_path.suffix.lower()
        if extension not in {".jsonl", ".json"}:
            parser.error("--metrics-output must point to a .jsonl or .json file")

        metrics_parent = metrics_path.parent
        if not metrics_parent.exists():
            parser.error("Directory for --metrics-output does not exist")

        if metrics_parent.is_symlink():
            parser.error("--metrics-output directory cannot be a symbolic link")

    def _maybe_prepare_auto_metrics(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        if not getattr(args, "auto_metrics", False):
            return

        if getattr(args, "metrics_output", None):
            return

        if getattr(args, "read_only_output", False) or self.read_only_output:
            parser.error("--auto-metrics cannot be used when read-only output is enforced")

        preferred_dir = getattr(self.config.application, "auto_metrics_directory", None)
        if preferred_dir:
            base_dir = Path(preferred_dir).expanduser()
        else:
            base_dir = Path.cwd() / "reports"

        try:
            resolved_base = base_dir.resolve(strict=False)
        except FileNotFoundError:
            resolved_base = base_dir

        if resolved_base.exists() and resolved_base.is_symlink():
            parser.error("Auto metrics directory cannot be a symbolic link")

        try:
            resolved_base.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            parser.error(f"Failed to prepare auto metrics directory: {exc}")

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        auto_metrics_path = resolved_base / f"metrics_{self.session_id}_{timestamp}.jsonl"
        args.metrics_output = auto_metrics_path

    def _validate_failure_output(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        failure_target = getattr(args, "failure_output", None)
        if not failure_target:
            return

        if getattr(args, "read_only_output", False) or self.read_only_output:
            parser.error("--failure-output cannot be used when read-only output is enforced")

        failure_path = failure_target.expanduser()
        if ".." in failure_path.parts:
            parser.error("--failure-output path cannot contain parent directory traversal")

        if failure_path.suffix.lower() != ".json":
            parser.error("--failure-output must point to a .json file")

        failure_parent = failure_path.parent
        if not failure_parent.exists():
            parser.error("Directory for --failure-output does not exist")

        if failure_parent.is_symlink():
            parser.error("--failure-output directory cannot be a symbolic link")

    def _maybe_prepare_auto_failures(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        if not getattr(args, "auto_failures", False):
            return

        if getattr(args, "failure_output", None):
            return

        if getattr(args, "read_only_output", False) or self.read_only_output:
            parser.error("--auto-failures cannot be used when read-only output is enforced")

        preferred_dir = getattr(self.config.application, "auto_failures_directory", None)
        if preferred_dir:
            base_dir = Path(preferred_dir).expanduser()
        else:
            base_dir = Path.cwd() / "reports"

        try:
            resolved_base = base_dir.resolve(strict=False)
        except FileNotFoundError:
            resolved_base = base_dir

        if resolved_base.exists() and resolved_base.is_symlink():
            parser.error("Auto failures directory cannot be a symbolic link")

        try:
            resolved_base.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            parser.error(f"Failed to prepare auto failures directory: {exc}")

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        auto_failure_path = resolved_base / f"failures_{self.session_id}_{timestamp}.json"
        args.failure_output = auto_failure_path

    def _apply_language_mode(self, mode: str) -> None:
        self.language_mode = mode or "bilingual"
        if self.language_mode == "en":
            set_global_language("en")
        elif self.language_mode == "ja":
            set_global_language("ja")
        else:
            set_global_language("en")

    def _format_locale_string(self, en: Optional[str], ja: Optional[str]) -> Optional[str]:
        """Format locale-aware string using i18n system."""
        if not en and not ja:
            return None

        # Try to find existing translation key first
        if en and ja:
            # Look for existing translation
            for key, trans in self.i18n_manager.translations.items():
                if trans.en == en and trans.ja == ja:
                    return self.i18n_manager.t(key)

        # Create a temporary key for this translation
        temp_key = f"temp_{hash(en or ja)}"
        if temp_key not in self.i18n_manager.translations:
            from .core.i18n_optimized import Translation
            temp_translation = Translation(temp_key, en, ja, category="temp")
            self.i18n_manager.add_translation(temp_translation)

        return self.i18n_manager.t(temp_key)

    def _format_locale_lines(self, en: Optional[str], ja: Optional[str]) -> List[str]:
        """Format locale-aware lines using i18n system."""
        if not en and not ja:
            return []

        # Try to find existing translation first
        if en and ja:
            # Look for existing translation
            for key, trans in self.i18n_manager.translations.items():
                if trans.en == en and trans.ja == ja:
                    return [self.i18n_manager.t(key)]

        # Create a temporary key for this translation
        temp_key = f"temp_lines_{hash(en or ja)}"
        if temp_key not in self.i18n_manager.translations:
            from .core.i18n_optimized import Translation
            temp_translation = Translation(temp_key, en, ja, category="temp")
            self.i18n_manager.add_translation(temp_translation)

        translated = self.i18n_manager.t(temp_key)
        return [translated] if translated else []

    @staticmethod
    def _is_within_base(candidate: Path, base: Path) -> bool:
        """Return True if `candidate` is equal to or within `base`."""

        try:
            candidate.relative_to(base)
            return True
        except ValueError:
            return False

    def _assert_within_base(self, candidate: Path, base: Path) -> None:
        """Raise ValueError if candidate is not within base."""

        if not self._is_within_base(candidate, base):
            raise ValueError(f"{candidate} is not within {base}")

    def _load_hash_manifest(self, manifest_path: Path) -> Dict[str, str]:
        """Load and normalize checksum manifest."""

        try:
            with manifest_path.open("r", encoding="utf-8") as fh:
                manifest_data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON: {exc}") from exc
        except OSError as exc:
            raise ValueError(f"Unable to read manifest: {exc}") from exc

        if isinstance(manifest_data, dict) and "files" in manifest_data and isinstance(manifest_data["files"], dict):
            manifest_entries = manifest_data["files"]
        elif isinstance(manifest_data, dict):
            manifest_entries = manifest_data
        else:
            raise ValueError("Manifest must be a JSON object mapping file identifiers to SHA-256 digests")

        normalized: Dict[str, str] = {}
        base_dir = manifest_path.parent.resolve()

        for raw_key, raw_value in manifest_entries.items():
            if not isinstance(raw_value, str):
                raise ValueError(f"Digest for entry '{raw_key}' must be a string")
            digest_candidate = raw_value.strip().lower()
            if not re.fullmatch(r"[0-9a-f]{64}", digest_candidate):
                raise ValueError(f"Digest for entry '{raw_key}' is not a valid SHA-256 value")

            for variant in self._manifest_key_variants(str(raw_key), base_dir):
                normalized[variant] = digest_candidate

        if not normalized:
            raise ValueError("Manifest does not contain any file entries")

        return normalized

    def _manifest_key_variants(self, raw_key: str, base_dir: Path) -> Iterable[str]:
        """Produce normalized keys for lookup (absolute, relative, filename)."""

        variants = set()
        stripped = raw_key.strip()

        if not stripped:
            return variants

        variants.add(stripped.lower())

        try:
            key_path = Path(stripped)
        except Exception:
            return variants

        variants.add(key_path.name.lower())

        try:
            if key_path.is_absolute():
                resolved_key = key_path.resolve()
            else:
                resolved_key = (base_dir / key_path).resolve()
            variants.add(str(resolved_key).lower())
        except Exception:
            pass

        return variants

    def find_mesh_files(self, args: argparse.Namespace) -> Tuple[List[Path], List[str]]:
        """Find all mesh files based on arguments."""
        files = []
        hints = []
        seen = set()

        # From direct file arguments
        if args.files:
            for file_arg in args.files:
                path = Path(file_arg)
                if path.is_file():
                    if path.suffix.lower() in MESH_EXTENSIONS:
                        candidate = self._validate_candidate_file(path, hints)
                        if candidate and candidate not in seen:
                            files.append(candidate)
                            seen.add(candidate)
                    else:
                        hints.append(f"Skipped unsupported file: {path.name}")
                elif path.is_dir():
                    # Treat as input directory
                    for ext in MESH_EXTENSIONS:
                        for f in sorted(path.glob(f"**/*{ext}")):
                            if f.is_symlink():
                                hints.append(f"Skipped symbolic link: {f}")
                                continue
                            candidate = self._validate_candidate_file(f, hints)
                            if candidate and candidate not in seen:
                                files.append(candidate)
                                seen.add(candidate)
                else:
                    hints.append(f"File not found: {file_arg}")

        # From pattern
        if args.pattern:
            pattern_path = Path(args.pattern)
            if pattern_path.parent.exists():
                for f in sorted(pattern_path.parent.glob(pattern_path.name)):
                    if f.suffix.lower() in MESH_EXTENSIONS:
                        if f.is_symlink():
                            hints.append(f"Skipped symbolic link: {f}")
                            continue
                        candidate = self._validate_candidate_file(f, hints)
                        if candidate and candidate not in seen:
                            files.append(candidate)
                            seen.add(candidate)
            else:
                hints.append(f"Pattern directory not found: {pattern_path.parent}")

        # From input directory
        if args.input_dir:
            if args.input_dir.is_dir():
                for ext in MESH_EXTENSIONS:
                    for f in sorted(args.input_dir.glob(f"**/*{ext}")):
                        if f.is_symlink():
                            hints.append(f"Skipped symbolic link: {f}")
                            continue
                        candidate = self._validate_candidate_file(f, hints)
                        if candidate and candidate not in seen:
                            files.append(candidate)
                            seen.add(candidate)
            else:
                hints.append(f"Input directory not found: {args.input_dir}")

        return sorted(files), hints

    def _compute_file_sha256(self, file_path: Path) -> Tuple[bool, Optional[str]]:
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

    def _manifest_candidates_for_path(self, file_path: Path) -> List[str]:
        """Generate lookup keys for a file against the manifest."""

        candidates = {str(file_path).lower(), file_path.name.lower()}
        try:
            resolved = file_path.resolve()
            candidates.add(str(resolved).lower())
            if self.hash_manifest_source:
                manifest_base = self.hash_manifest_source.parent.resolve()
                try:
                    relative = resolved.relative_to(manifest_base)
                    candidates.add(str(relative).lower())
                except ValueError:
                    pass
        except FileNotFoundError:
            pass
        return list(candidates)

    def _verify_manifest_digest(self, file_path: Path, digest: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Verify digest against manifest when required."""

        if not self.hash_manifest_lookup:
            return True, None, None

        expected_digest: Optional[str] = None
        for candidate in self._manifest_candidates_for_path(file_path):
            expected_digest = self.hash_manifest_lookup.get(candidate)
            if expected_digest:
                break

        if expected_digest is None:
            return False, "Hash manifest does not contain an entry for the requested mesh", None

        if digest.lower() != expected_digest.lower():
            return False, "SHA-256 digest does not match manifest entry", expected_digest

    def _get_cache_key(self, file_path: Path, args_hash: str) -> str:
        """Generate cache key for a file and processing arguments."""
        file_stat = file_path.stat()
        return f"{file_path}:{file_stat.st_mtime}:{file_stat.st_size}:{args_hash}"

    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load cached result if available and valid."""
        try:
            cache_dir = Path.home() / ".3dprintcad" / "cache"
            cache_file = cache_dir / f"{hash(cache_key)}.json"

            if cache_file.exists():
                cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
                # Check if cache is still valid (within 24 hours)
                cache_time = cache_data.get("cache_time", 0)
                if time.time() - cache_time < 86400:  # 24 hours
                    self.logger.debug(f"Cache hit for {cache_key}")
                    return cache_data.get("result")

            return None
        except Exception:
            return None

    def _save_to_cache(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Save result to cache."""
        try:
            cache_dir = Path.home() / ".3dprintcad" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"{hash(cache_key)}.json"

            cache_data = {
                "cache_time": time.time(),
                "cache_key": cache_key,
                "result": result
            }
            cache_file.write_text(json.dumps(cache_data, ensure_ascii=False), encoding="utf-8")
            self.logger.debug(f"Cached result for {cache_key}")
        except Exception:
            pass  # Cache save failure should not affect processing
        """Get current process memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convert bytes to MB
        except ImportError:
            # psutil not available, return 0
            return 0.0
        except Exception:
            # Any other error, return 0
            return 0.0
        return result

        # Save to cache if enabled and processing was successful
        if cache_enabled and result.get("success"):
            try:
                self._save_to_cache(cache_key, result)
            except Exception:
                pass  # Cache save failure should not affect result

        result["processing_time"] = time.time() - start_time
        return result

    def _analyze_processing_times(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze processing times and provide detailed breakdown."""
        if not results:
            return {}

        processing_times = [r.get("processing_time", 0) for r in results if r.get("success")]
        if not processing_times:
            return {}

        analysis = {
            "total_files": len(results),
            "successful_files": len(processing_times),
            "total_time": sum(processing_times),
            "average_time": sum(processing_times) / len(processing_times),
            "min_time": min(processing_times),
            "max_time": max(processing_times),
            "median_time": sorted(processing_times)[len(processing_times) // 2],
            "time_distribution": {
                "fast": len([t for t in processing_times if t < 1.0]),  # < 1 second
                "medium": len([t for t in processing_times if 1.0 <= t < 10.0]),  # 1-10 seconds
                "slow": len([t for t in processing_times if 10.0 <= t < 60.0]),  # 10-60 seconds
                "very_slow": len([t for t in processing_times if t >= 60.0])  # >= 60 seconds
            }
        }

        # Calculate percentiles
        sorted_times = sorted(processing_times)
        analysis["percentiles"] = {
            "p25": sorted_times[int(len(sorted_times) * 0.25)],
            "p50": sorted_times[int(len(sorted_times) * 0.50)],
            "p75": sorted_times[int(len(sorted_times) * 0.75)],
            "p90": sorted_times[int(len(sorted_times) * 0.90)],
            "p95": sorted_times[int(len(sorted_times) * 0.95)],
            "p99": sorted_times[int(len(sorted_times) * 0.99)]
        }

        # Performance insights
        avg_time = analysis["average_time"]
        if avg_time < 1.0:
            analysis["performance_rating"] = "excellent"
            analysis["performance_insight"] = "Very fast processing - suitable for real-time applications"
        elif avg_time < 5.0:
            analysis["performance_rating"] = "good"
            analysis["performance_insight"] = "Good performance for batch processing"
        elif avg_time < 15.0:
            analysis["performance_rating"] = "fair"
            analysis["performance_insight"] = "Acceptable performance - consider optimization for large batches"
        else:
            analysis["performance_rating"] = "slow"
            analysis["performance_insight"] = "Slow processing - optimization recommended"

        return analysis

    def _apply_result_filters(self, results: List[Dict[str, Any]], args: argparse.Namespace) -> List[Dict[str, Any]]:
        """Apply result filters based on command line arguments."""
        if not any([
            getattr(args, 'filter_success', False),
            getattr(args, 'filter_failed', False),
            getattr(args, 'filter_warnings', False),
            getattr(args, 'filter_errors', False),
            getattr(args, 'filter_cached', False)
        ]):
            return results  # No filters applied

        filtered = []

        for result in results:
            success = result.get("success", False)
            warning_count = result.get("warning_count", 0)
            error_count = len([i for i in result.get("issues", []) if i.get("severity") == "error"])
            is_cached = result.get("cached", False)

            # Apply filters
            if getattr(args, 'filter_success', False) and not success:
                continue
            if getattr(args, 'filter_failed', False) and success:
                continue
            if getattr(args, 'filter_warnings', False) and warning_count == 0:
                continue
            if getattr(args, 'filter_errors', False) and error_count == 0:
                continue
            if getattr(args, 'filter_cached', False) and not is_cached:
                continue

            filtered.append(result)

        return filtered

    def _print_enhanced_batch_statistics(self, results: List[Dict[str, Any]], start_time: float, args: argparse.Namespace) -> None:
        """Print enhanced batch processing statistics."""
        # Apply filters if specified
        filtered_results = self._apply_result_filters(results, args)

        total_files = len(results)
        successful_files = sum(1 for r in results if r.get("success"))
        failed_files = total_files - successful_files

        total_time = time.time() - start_time
        avg_time_per_file = total_time / total_files if total_files > 0 else 0

        # Get processing time analysis
        time_analysis = self._analyze_processing_times(results)

        # Calculate memory statistics
        memory_stats = []
        processing_times = []

        for result in results:
            if result.get("success"):
                memory_info = result.get("memory_usage_mb", {})
                if memory_info:
                    memory_stats.append(memory_info.get("delta", 0))
                processing_times.append(result.get("processing_time", 0))

        avg_memory_delta = sum(memory_stats) / len(memory_stats) if memory_stats else 0
        cached_files = sum(1 for r in results if r.get("cached"))

        print("\n" + "="*60)
        stats_title = self._format_locale_string("Batch Processing Statistics", "バッチ処理統計")
        print(f"{stats_title}")
        print("="*60)

        print(f"Files processed: {total_files}")
        print(f"Successful: {successful_files} ({successful_files/total_files*100:.1f}%)")
        print(f"Failed: {failed_files} ({failed_files/total_files*100:.1f}%)")
        if cached_files > 0:
            print(f"Cached: {cached_files} ({cached_files/total_files*100:.1f}%)")

        # Show filter information if filters are applied
        filter_count = len(filtered_results)
        if filter_count != total_files:
            filter_info = self._format_locale_string(
                f"Filtered results: {filter_count} of {total_files} files match criteria",
                f"フィルタリング結果: {filter_count}/{total_files} 件のファイルが条件に一致"
            )
            print(f"{filter_info}")

        print(f"\nOverall timing:")
        print(f"Total batch time: {total_time:.2f}s")
        print(f"Average per file: {avg_time_per_file:.2f}s")

        # Detailed timing analysis
        if time_analysis:
            print(f"\nDetailed timing analysis:")
            print(f"Min processing time: {time_analysis['min_time']:.2f}s")
            print(f"Max processing time: {time_analysis['max_time']:.2f}s")
            print(f"Median processing time: {time_analysis['median_time']:.2f}s")

            percentiles = time_analysis.get("percentiles", {})
            print(f"25th percentile: {percentiles.get('p25', 0):.2f}s")
            print(f"75th percentile: {percentiles.get('p75', 0):.2f}s")
            print(f"95th percentile: {percentiles.get('p95', 0):.2f}s")

            distribution = time_analysis.get("time_distribution", {})
            print(f"\nProcessing time distribution:")
            print(f"Fast (< 1s): {distribution.get('fast', 0)} files")
            print(f"Medium (1-10s): {distribution.get('medium', 0)} files")
            print(f"Slow (10-60s): {distribution.get('slow', 0)} files")
            print(f"Very slow (≥ 60s): {distribution.get('very_slow', 0)} files")

            rating = time_analysis.get("performance_rating", "unknown")
            insight = time_analysis.get("performance_insight", "")
            print(f"\nPerformance rating: {rating.title()}")
            if insight:
                print(f"Insight: {insight}")

        if memory_stats:
            print(f"\nMemory usage:")
            print(f"Average memory delta: +{avg_memory_delta:.1f} MB")

        # Calculate issue statistics
        total_warnings = sum(r.get("warning_count", 0) for r in results)
        total_errors = sum(len([i for i in r.get("issues", []) if i.get("severity") == "error"]) for r in results)

        print(f"\nQuality metrics:")
        print(f"Total warnings: {total_warnings}")
        print(f"Total errors: {total_errors}")
        print(f"Average issues per file: {(total_warnings + total_errors)/total_files:.1f}")

        print("="*60)

    def process_batch(self, files: List[Path], args: argparse.Namespace) -> List[Dict[str, Any]]:
        """Process a batch of mesh files."""
        start_time = time.time()
        start_memory_mb = self._get_current_memory_usage_mb()

        results = []
        total_files = len(files)
        batch_start_time = start_time

        for file in files:
            result = self.process_mesh(file, args)
            results.append(result)

        results.sort(key=lambda entry: entry.get("file", ""))
        return results

    def process_mesh(self, file_path: Path, args: argparse.Namespace) -> Dict[str, Any]:
        """Process a single mesh file with watchdog timer protection."""
        import signal
        from contextlib import contextmanager

        @contextmanager
        def watchdog_timer(timeout_seconds: float, operation_name: str):
            """Context manager for watchdog timer that terminates long-running operations."""
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Operation '{operation_name}' timed out after {timeout_seconds} seconds")

            # Set up the signal handler
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout_seconds))

            try:
                yield
            finally:
                # Restore the old handler and cancel the alarm
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

        # Determine appropriate timeout based on file size and operation type
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        base_timeout = getattr(self.config.application, "mesh_processing_timeout_seconds", 300.0)

        # Scale timeout based on file size (larger files need more time)
        if file_size_mb > 100:  # Very large files
            timeout_seconds = base_timeout * 3
        elif file_size_mb > 50:  # Large files
            timeout_seconds = base_timeout * 2
        elif file_size_mb > 10:  # Medium files
            timeout_seconds = base_timeout * 1.5
        else:  # Small files
            timeout_seconds = base_timeout

        # Apply minimum timeout
        timeout_seconds = max(timeout_seconds, 30.0)  # At least 30 seconds

        cache_enabled = getattr(args, 'enable_cache', False)
        if cache_enabled:
            # Create args hash for cache key (exclude file-specific args)
            args_dict = vars(args).copy()
            args_dict.pop('files', None)  # Remove file list
            args_hash = hashlib.sha256(json.dumps(args_dict, sort_keys=True).encode()).hexdigest()[:16]
            cache_key = self._get_cache_key(file_path, args_hash)

            cached_result = self._load_from_cache(cache_key)
            if cached_result:
                cached_result["cached"] = True
                self.logger.debug(f"Using cached result for {file_path}")
                return cached_result

        result = {
            "file": str(file_path),
            "success": False,
            "processing_time": 0,
            "error": None
        }

        start_time = time.time()
        start_memory_mb = self._get_current_memory_usage_mb()

        try:
            # Apply watchdog timer to the entire mesh processing operation
            with watchdog_timer(timeout_seconds, f"process_mesh_{file_path.name}"):
                file_path = file_path.resolve(strict=True)
                size_ok, size_error = self._ensure_within_size_limit(file_path)
                if not size_ok:
                    result["error"] = size_error
                    return result

                digest_ok, digest_value = self._compute_file_sha256(file_path)
                if not digest_ok:
                    result["error"] = f"SHA-256 computation failed: {digest_value}"
                    return result

                result["sha256"] = digest_value

                # Always compute hash for integrity, but only verify if manifest is provided
                if self.hash_manifest_lookup:
                    manifest_ok, manifest_error, expected_digest = self._verify_manifest_digest(file_path, digest_value)
                    if not manifest_ok:
                        if expected_digest:
                            result["expected_sha256"] = expected_digest

                        if self.hash_policy == "strict":
                            result["error"] = manifest_error
                            return result

                        # Add warning for hash mismatch in warn mode
                        warning_en = manifest_error or "Hash manifest mismatch detected"
                        warning_ja = manifest_error or "ハッシュマニフェスト不一致を検出しました"
                        result.setdefault("issues", []).append({
                            "severity": "warning",
                            "code": "HASH_MANIFEST",
                            "message_en": warning_en,
                            "message_ja": warning_ja,
                            "expected": expected_digest,
                            "observed": digest_value
                        })
                        result["warning_count"] = result.get("warning_count", 0) + 1
                else:
                    # No manifest provided - hash computed for integrity but not verified
                    result["hash_computed"] = True

                # Load mesh with individual timeout protection
                with watchdog_timer(min(timeout_seconds * 0.7, 120), f"load_mesh_{file_path.name}"):
                    mesh = load_mesh(file_path)
                    result["mesh_info"] = {
                        "vertices": len(mesh.vertices),
                        "faces": len(mesh.faces),
                        "bounds": mesh.bounds.tolist() if hasattr(mesh, 'bounds') else None
                    }

                # Validate with timeout protection
                if args.validate:
                    with watchdog_timer(min(timeout_seconds * 0.2, 60), f"validate_mesh_{file_path.name}"):
                        mesh_validator = _lazy_import_mesh_validator()
                        settings = mesh_validator.MeshValidationSettings(
                            min_wall_thickness=args.min_wall,
                            min_feature_size=args.min_feature,
                            support_overhang_angle_deg=args.overhang_angle,
                        )
                        validation = mesh_validator.validate_mesh(mesh, settings=settings)
                        result["validation"] = validation.as_dict()
                        result["is_valid"] = validation.success
                        result["issues"] = [issue.as_dict() for issue in validation.issues]

                        # Repair if needed
                        if args.repair and validation.issues:
                            with watchdog_timer(min(timeout_seconds * 0.3, 90), f"repair_mesh_{file_path.name}"):
                                # Lazy import repair_mesh
                                from .core.analysis.mesh_repair import repair_mesh
                                repaired_mesh, repair_summary = repair_mesh(mesh, aggressive=args.aggressive_repair)
                                if repaired_mesh is not None:
                                    mesh = repaired_mesh
                                    result["repaired"] = True
                                    result["repair_summary"] = {
                                        "operations": [op.operation.value for op in repair_summary.operations_performed],
                                        "issues_fixed": repair_summary.issues_fixed,
                                        "remaining_issues": repair_summary.remaining_issues,
                                        "success": repair_summary.repair_success
                                    }
                                    if getattr(args, "save_repaired", None) and not self.read_only_output:
                                        repaired_path = args.save_repaired.expanduser().resolve()
                                        repaired_path.parent.mkdir(parents=True, exist_ok=True)
                                        mesh.export(repaired_path)
                                        result["repaired_file"] = str(repaired_path)

                                    # Re-validate after repair
                                    validation = mesh_validator.validate_mesh(repaired_mesh, settings=settings)
                                    result["validation_after_repair"] = validation.as_dict()

                # Slice with timeout protection
                if args.slice or args.gcode:
                    with watchdog_timer(min(timeout_seconds * 0.2, 60), f"slice_mesh_{file_path.name}"):
                        SliceSettings, SlicingEngine, GcodeSettings, GcodeGenerator = _lazy_import_slicing()
                        slice_settings = SliceSettings(
                            layer_height=args.layer_height,
                            infill_density=args.infill,
                            print_speed=args.speed
                        )
                        slicer = SlicingEngine(slice_settings)
                        slicing_result = slicer.slice_mesh(mesh)
                        result["slicing"] = {
                            "layers": slicing_result.total_layers,
                            "print_time_seconds": slicing_result.total_print_time_seconds,
                            "print_time_hours": slicing_result.total_print_time_seconds / 3600,
                            "material_grams": slicing_result.total_material_grams
                        }

                        # Generate G-code
                        if args.gcode:
                            with watchdog_timer(min(timeout_seconds * 0.1, 30), f"generate_gcode_{file_path.name}"):
                                gcode_settings = GcodeSettings(
                                    nozzle_temperature=args.temp_nozzle,
                                    bed_temperature=args.temp_bed,
                                    print_speed=args.speed
                                )
                                generator = GcodeGenerator(gcode_settings)
                                gcode = generator.generate(slicing_result)

                                # Save G-code if output specified
                                if args.output and args.output.suffix == ".gcode" and not self.read_only_output:
                                    args.output.write_text(gcode)
                                    result["gcode_file"] = str(args.output)
                                else:
                                    result["gcode_lines"] = len(gcode.splitlines())

                # Recommendations with timeout protection
                readiness_payload: Optional[Dict[str, Any]] = None
                if args.recommendations and "validation" in result:
                    with watchdog_timer(min(timeout_seconds * 0.1, 30), f"generate_recommendations_{file_path.name}"):
                        RecommendationEngine = _lazy_import_recommendation_engine()
                        recommender = RecommendationEngine()
                        recommendations = recommender.generate_recommendations(validation)
                        recommendation_dict = recommendations.to_dict()
                        result["recommendations"] = recommendation_dict
                        result["rationales"] = recommendation_dict.get("rationales", [])
                        try:
                            evaluate_print_readiness = _lazy_import_readiness()
                            readiness_payload = evaluate_print_readiness(
                                validation,
                                recommendations=recommendation_dict,
                                repair=result.get("repair_summary"),
                            )
                        except Exception as readiness_exc:
                            if args.verbose:
                                result.setdefault("notes", []).append({
                                    "note_en": f"Readiness evaluation failed: {readiness_exc}",
                                    "note_ja": f"造形準備評価に失敗しました: {readiness_exc}",
                                })
                elif "validation" in result:
                    with watchdog_timer(min(timeout_seconds * 0.05, 15), f"evaluate_readiness_{file_path.name}"):
                        try:
                            evaluate_print_readiness = _lazy_import_readiness()
                            readiness_payload = evaluate_print_readiness(
                                validation,
                                recommendations=None,
                                repair=result.get("repair_summary"),
                            )
                        except Exception as readiness_exc:
                            if args.verbose:
                                result.setdefault("notes", []).append({
                                    "note_en": f"Readiness evaluation failed: {readiness_exc}",
                                    "note_ja": f"造形準備評価に失敗しました: {readiness_exc}",
                                })

                if readiness_payload:
                    result["readiness"] = readiness_payload

                result["risk_score"] = self._compute_risk_score(result)
                manual_minutes_saved = self._estimate_manual_minutes_saved(result)
                result["estimated_manual_minutes_saved"] = manual_minutes_saved
                result["estimated_manual_cost_saved_usd"] = round(
                    (manual_minutes_saved / 60.0) * self.roi_settings["manual_review_cost_rate_usd"],
                    2,
                )
                result["success"] = True

                warnings_present = any(
                    issue.get("severity") == "warning"
                    for issue in result.get("issues", []) or []
                )
                warning_issues = [
                    issue for issue in (result.get("issues") or []) if issue.get("severity") == "warning"
                ]
                warning_count = len(warning_issues)
                result["warning_count"] = warning_count

                if args.fail_on_warnings and warnings_present and result.get("success"):
                    fail_message = self._format_locale_string(
                        "Warnings detected; failing per --fail-on-warnings",
                        "警告が検出されたため --fail-on-warnings により失敗扱いです",
                    ) or "Warnings detected; failing per --fail-on-warnings"
                    result.setdefault("notes", []).append(
                        {
                            "note_en": "Validation warnings present under --fail-on-warnings.",
                            "note_ja": "--fail-on-warnings 指定により警告検出時は失敗扱いです。",
                        }
                    )
                    result["success"] = False
                    result.setdefault("error", fail_message)

                if (
                    args.max_risk_score is not None
                    and isinstance(result.get("risk_score"), (int, float))
                    and result["risk_score"] > args.max_risk_score
                    and result.get("success")
                ):
                    risk_fail_message = self._format_locale_string(
                        f"Risk score {result['risk_score']:.2f} exceeds threshold {args.max_risk_score:.2f}",
                        f"リスクスコア {result['risk_score']:.2f} が閾値 {args.max_risk_score:.2f} を超過しました",
                    ) or "Risk score exceeds threshold"
                    result.setdefault("notes", []).append(
                        {
                            "note_en": "Risk score exceeded configured threshold; run marked as failure.",
                            "note_ja": "リスクスコアが設定閾値を超過したため失敗扱いです。",
                        }
                    )
                    result["success"] = False
                    result.setdefault("error", risk_fail_message)

                readiness_payload = result.get("readiness")
                readiness_score = None
                if readiness_payload:
                    readiness_score = readiness_payload.get("score")

                if (
                    args.min_readiness_score is not None
                    and readiness_score is not None
                    and readiness_score < args.min_readiness_score
                    and result.get("success")
                ):
                    readiness_fail_message = self._format_locale_string(
                        f"Readiness score {readiness_score:.1f} below threshold {args.min_readiness_score:.1f}",
                        f"造形準備スコア {readiness_score:.1f} が閾値 {args.min_readiness_score:.1f} を下回りました",
                    ) or "Readiness score below threshold"
                    result.setdefault("notes", []).append(
                        {
                            "note_en": "Readiness score below configured minimum; run marked as failure.",
                            "note_ja": "設定された最小造形準備スコアを下回ったため失敗扱いです。",
                        }
                    )
                    result["success"] = False
                    result.setdefault("error", readiness_fail_message)

                if args.min_readiness_score is not None and readiness_score is None and result.get("success"):
                    readiness_missing_message = self._format_locale_string(
                        "Readiness score unavailable; failing per --min-readiness-score",
                        "造形準備スコアが取得できないため --min-readiness-score により失敗扱いです",
                    ) or "Readiness score unavailable"
                    result.setdefault("notes", []).append(
                        {
                            "note_en": "Readiness evaluation missing while --min-readiness-score specified.",
                            "note_ja": "--min-readiness-score 指定時に造形準備スコアが生成されませんでした。",
                        }
                    )
                    result["success"] = False
                    result.setdefault("error", readiness_missing_message)

                if (
                    args.max_warning_count is not None
                    and warning_count > args.max_warning_count
                    and result.get("success")
                ):
                    warning_limit_message = self._format_locale_string(
                        f"Warning count {warning_count} exceeds limit {args.max_warning_count}",
                        f"警告数 {warning_count} が上限 {args.max_warning_count} を超えました",
                    ) or "Warning count exceeds limit"
                    result.setdefault("notes", []).append(
                        {
                            "note_en": "Warning count exceeded configured threshold; run marked as failure.",
                            "note_ja": "警告数が設定閾値を超過したため失敗扱いです。",
                        }
                    )
                    result["success"] = False
                    result.setdefault("error", warning_limit_message)

        except TimeoutError as timeout_exc:
            result["error"] = f"Processing timeout: {timeout_exc}"
            result["was_timeout"] = True
            self.logger.warning(f"Mesh processing timed out for {file_path}: {timeout_exc}")
        except Exception as e:
            result["error"] = str(e)
            if args.verbose:
                import traceback
                result["traceback"] = traceback.format_exc()

        # Memory usage monitoring
        end_memory_mb = self._get_current_memory_usage_mb()
        memory_delta_mb = end_memory_mb - start_memory_mb
        result["memory_usage_mb"] = {
            "start": start_memory_mb,
            "end": end_memory_mb,
            "delta": memory_delta_mb
        }

        # Warn if memory usage is excessive
        memory_threshold_mb = getattr(self.config.application, "memory_warning_threshold_mb", 500.0)
        if memory_delta_mb > memory_threshold_mb:
            memory_warning = self._format_locale_string(
                f"High memory usage detected: +{memory_delta_mb:.1f} MB",
                f"高いメモリ使用量を検出しました: +{memory_delta_mb:.1f} MB"
            ) or f"High memory usage detected: +{memory_delta_mb:.1f} MB"
            result.setdefault("issues", []).append({
                "severity": "warning",
                "code": "MEMORY_USAGE",
                "message_en": f"High memory usage detected: +{memory_delta_mb:.1f} MB",
                "message_ja": f"高いメモリ使用量を検出しました: +{memory_delta_mb:.1f} MB"
            })
            result["warning_count"] = result.get("warning_count", 0) + 1
            self.logger.warning("High memory usage for %s: +%.1f MB", file_path, memory_delta_mb)

        result["processing_time"] = time.time() - start_time
        return result

    def _calculate_optimal_batch_size(self, avg_file_size: float, max_workers: int) -> int:
        """Calculate optimal batch size based on file size and available resources.
        
        Args:
            avg_file_size: Average file size in bytes
            max_workers: Maximum number of worker processes
            
        Returns:
            Optimal batch size
        """
        # ファイルサイズに基づいてバッチサイズを調整
        if avg_file_size > 100 * 1024 * 1024:  # >100MB
            return max(1, max_workers // 2)
        elif avg_file_size > 10 * 1024 * 1024:  # 10-100MB
            return max(2, max_workers)
        else:  # <10MB
            return max(4, max_workers * 2)
            
    def _process_batch_with_retry(
        self,
        pool: multiprocessing.Pool,
        batch: List[Path],
        args: argparse.Namespace,
        pbar: Any
    ) -> List[Dict[str, Any]]:
        """Process a batch of files with retry logic.
        
        Args:
            pool: Multiprocessing pool to use
            batch: List of files to process
            args: Command line arguments
            pbar: Progress bar instance
            
        Returns:
            List of processing results
        """
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                results = []
                for result in pool.imap_unordered(
                    self._process_file_wrapper,
                    [(str(f), vars(args)) for f in batch]
                ):
                    results.append(result)
                    pbar.update(1)
                return results
                
            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    self.logger.error(
                        f"Failed to process batch after {max_retries} attempts: {str(e)}"
                    )
                    # Return error for all files in batch
                    return [{
                        'file': str(f),
                        'error': f"Failed after {max_retries} attempts: {str(e)}",
                        'success': False
                    } for f in batch]
                
                # Exponential backoff
                time.sleep(retry_delay * (2 ** attempt))
                
        return []

    def _process_file_wrapper(self, args_tuple: Tuple[str, Dict]) -> Dict[str, Any]:
        """Wrapper function for processing a single file in a worker process."""
        file_path, args_dict = args_tuple
        args = argparse.Namespace(**args_dict)
        
        try:
            return self.process_mesh(Path(file_path), args)
        except Exception as e:
            return {
                'file': file_path,
                'error': str(e),
                'success': False,
                'traceback': traceback.format_exc()
            }

    def _process_files_sequential(
        self,
        files: List[Path],
        args: argparse.Namespace,
        processed_count: int,
        total_count: int,
        batch_start_time: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Process files sequentially with consistent progress output."""

        sequential_results: List[Dict[str, Any]] = []

        for offset, file in enumerate(files, 1):
            current_index = processed_count + offset
            progress_percent = (current_index / total_count) * 100

            if args.progress:
                # Calculate ETA if we have start time and processed some files
                eta_str = ""
                if batch_start_time and current_index > 1:
                    elapsed = time.time() - batch_start_time
                    avg_time_per_file = elapsed / (current_index - 1)
                    remaining_files = total_count - current_index + 1
                    eta_seconds = avg_time_per_file * remaining_files
                    if eta_seconds < 60:
                        eta_str = f"ETA: {eta_seconds:.0f}s"
                    elif eta_seconds < 3600:
                        eta_str = f"ETA: {eta_seconds/60:.1f}m"
                    else:
                        eta_str = f"ETA: {eta_seconds/3600:.1f}h"

                progress_info = f"[{current_index}/{total_count}] ({progress_percent:.1f}%)"
                if eta_str:
                    progress_info += f" {eta_str}"
                print(f"{progress_info} Processing {file.name}...")

            result = self.process_mesh(file, args)
            sequential_results.append(result)

            if args.progress:
                label = self._format_progress_label(result)
                metrics = self._format_progress_metrics(result)
                suffix = f" | {metrics}" if metrics else ""
                print(f"  {label}{suffix} | TIME={result.get('processing_time', 0):.2f}s")

            if args.exit_on_first_failure and not result.get("success", False):
                halt_message = self._format_locale_string(
                    "Halting after first failure (--exit-on-first-failure)",
                    "最初の失敗で停止します (--exit-on-first-failure)",
                ) or "Halting after first failure"
                if args.progress:
                    print(halt_message)
                break

        return sequential_results

    def _compute_risk_score(self, result: Dict[str, Any]) -> float:
        issues = result.get("issues", [])
        if not issues:
            return 0.0
        severity_weights = {"error": 1.0, "warning": 0.3}
        return sum(severity_weights.get(issue.get("severity"), 0.1) for issue in issues)

    def _print_single_result_summary(self, result: Dict[str, Any]) -> None:
        """Emit a bilingual, human-readable summary for single-file runs."""

        summary_label = self._format_locale_string("Summary", "サマリー") or "Summary"
        print(f"\n{summary_label}")
        print("=" * 50)

        readiness = result.get("readiness")
        if readiness:
            status_label = self._format_locale_string("Status", "ステータス") or "Status"
            status_value = self._format_locale_string(
                readiness.get("status_en", "Unknown"),
                readiness.get("status_ja"),
            )
            if status_value:
                print(f"{status_label}: {status_value}")
            score = readiness.get("score")
            if isinstance(score, (int, float)):
                score_label = self._format_locale_string("Readiness score", "造形準備スコア") or "Readiness score"
                print(f"{score_label}: {score:.1f}")
            summary_en = readiness.get("summary_en")
            summary_ja = readiness.get("summary_ja")
            for line in self._format_locale_lines(
                f"Summary: {summary_en or 'n/a'}" if summary_en else None,
                f"概要: {summary_ja or 'n/a'}" if summary_ja else None,
            ):
                print(line)

            checklist = readiness.get("checklist", [])
            if checklist:
                checklist_label = self._format_locale_string("Checklist", "チェックリスト") or "Checklist"
                print(f"\n{checklist_label}:")
                for item in checklist[:5]:
                    status_value = self._format_locale_string(
                        item.get("status_en", ""),
                        item.get("status_ja", ""),
                    )
                    print(f"- {item.get('key', 'unknown')}: {status_value or 'n/a'}")
                    for line in self._format_locale_lines(
                        f"    EN: {item.get('detail_en') or 'n/a'}",
                        f"    詳細: {item.get('detail_ja') or 'n/a'}",
                    ):
                        print(line)

        issues = result.get("issues", [])
        if issues:
            issues_label = self._format_locale_string("Issues", "課題") or "Issues"
            print(f"\n{issues_label}:")
            for issue in issues[:5]:
                msg_en = issue.get("message")
                msg_ja = issue.get("message_ja")
                message = self._format_locale_string(msg_en, msg_ja)
                if not message:
                    message = msg_en or msg_ja or ""
                print(
                    f"- {issue.get('code', 'UNKNOWN')} [{issue.get('severity', 'warning')}]: {message}"
                )

        risk = result.get("risk_score")
        if isinstance(risk, (int, float)):
            risk_label = self._format_locale_string("Risk score", "リスクスコア") or "Risk score"
            print(f"\n{risk_label}: {risk:.2f}")

        minutes_saved = result.get("estimated_manual_minutes_saved")
        cost_saved = result.get("estimated_manual_cost_saved_usd")
        if isinstance(minutes_saved, (int, float)) or isinstance(cost_saved, (int, float)):
            roi_label = self._format_locale_string("ROI estimate", "ROI 推定") or "ROI estimate"
            print(f"\n{roi_label}:")
            if isinstance(minutes_saved, (int, float)):
                minutes_text = self._format_locale_string(
                    f"- Manual time saved: {minutes_saved:.1f} minutes",
                    f"- 手作業削減時間: {minutes_saved:.1f} 分",
                ) or f"- Manual time saved: {minutes_saved:.1f} minutes"
                print(minutes_text)
            if isinstance(cost_saved, (int, float)):
                cost_text = self._format_locale_string(
                    f"- Cost avoided: ${cost_saved:.2f}",
                    f"- 削減コスト: ${cost_saved:.2f}",
                ) or f"- Cost avoided: ${cost_saved:.2f}"
                print(cost_text)

        notes = result.get("notes", [])
        if notes:
            notes_label = self._format_locale_string("Notes", "注記") or "Notes"
            print(f"\n{notes_label}:")
            for note in notes:
                for line in self._format_locale_lines(
                    f"- EN: {note.get('note_en')}" if note.get("note_en") else None,
                    f"- JA: {note.get('note_ja')}" if note.get("note_ja") else None,
                ):
                    print(line)

    def _format_progress_label(self, result: Dict[str, Any]) -> str:
        success = bool(result.get("success"))
        readiness = result.get("readiness") or {}
        status_success = self._format_locale_string("SUCCESS", "成功") or "SUCCESS"
        status_failed = self._format_locale_string("FAILED", "失敗") or "FAILED"
        status_token = status_success if success else status_failed
        readiness_en = readiness.get("status_en")
        readiness_ja = readiness.get("status_ja")
        readiness_value = self._format_locale_string(readiness_en, readiness_ja)
        if readiness_value and success:
            readiness_label = self._format_locale_string("READINESS", "造形準備") or "READINESS"
            return f"STATUS={status_token} | {readiness_label}={readiness_value}"
        return f"STATUS={status_token}"

    def _format_progress_metrics(self, result: Dict[str, Any]) -> str:
        metrics: List[str] = []
        risk = result.get("risk_score")
        if isinstance(risk, (int, float)):
            metrics.append(f"RISK={risk:.2f}")
        readiness = result.get("readiness") or {}
        score = readiness.get("score") if isinstance(readiness, dict) else None
        if isinstance(score, (int, float)):
            metrics.append(f"READINESS_SCORE={score:.1f}")
        roi_minutes = result.get("estimated_manual_minutes_saved")
        if isinstance(roi_minutes, (int, float)):
            metrics.append(f"ROI_MINUTES={roi_minutes:.1f}")

        manifest_notes = result.get("issues") or []
        manifest_warning_present = any(
            issue.get("code") == "HASH_MANIFEST" and issue.get("severity") == "warning"
            for issue in manifest_notes
        )
        if manifest_warning_present:
            metrics.append("HASH_MANIFEST_WARN=1")
        return " | ".join(metrics)

    def generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate batch processing summary."""
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        total_time = sum(r.get("processing_time", 0) for r in results)
        risk_scores = [r.get("risk_score") for r in results if "risk_score" in r]
        aggregate_risk = sum(risk_scores) if risk_scores else 0.0
        highest_risk = max(risk_scores) if risk_scores else 0.0

        manual_minutes = [r.get("estimated_manual_minutes_saved", 0.0) for r in results]
        total_manual_minutes = sum(manual_minutes)
        average_manual_minutes = total_manual_minutes / len(results) if results else 0.0
        total_manual_cost = sum(r.get("estimated_manual_cost_saved_usd", 0.0) for r in results)

        issue_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {"error": 0, "warning": 0, "info": 0}
        rationale_counts: Dict[str, int] = {}
        readiness_counts: Dict[str, int] = {}
        readiness_scores: List[float] = []
        manifest_warning_count = 0

        for result in results:
            for issue in result.get("issues", []) or []:
                code = issue.get("code", "UNKNOWN")
                severity = issue.get("severity", "warning").lower()
                issue_counts[code] = issue_counts.get(code, 0) + 1
                if severity in severity_counts:
                    severity_counts[severity] += 1
                else:
                    severity_counts[severity] = 1

                if code.upper() == "HASH_MANIFEST" and severity == "warning":
                    manifest_warning_count += 1

            for rationale in result.get("rationales", []) or []:
                rationale_code = rationale.get("code", "unspecified")
                rationale_counts[rationale_code] = rationale_counts.get(rationale_code, 0) + 1

            readiness = result.get("readiness")
            if readiness:
                status = readiness.get("status_en")
                if status:
                    readiness_counts[status] = readiness_counts.get(status, 0) + 1
                score = readiness.get("score")
                if isinstance(score, (int, float)):
                    readiness_scores.append(float(score))

            result_warning_count = result.get("warning_count")
            if isinstance(result_warning_count, (int, float)):
                overall_warning_count += int(result_warning_count)
            else:
                warning_fallback = len([issue for issue in (result.get("issues") or []) if issue.get("severity") == "warning"])
                overall_warning_count += warning_fallback

        common_issues = sorted(issue_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
        common_rationales = sorted(rationale_counts.items(), key=lambda item: (-item[1], item[0]))[:5]

        compliance_metadata = self._compliance_metadata()

        total_cost_saved = round(total_manual_cost, 2)
        top_rationale_codes = ", ".join(f"{code} ({count})" for code, count in common_rationales) if common_rationales else "none"

        readiness_summary = {
            "counts": readiness_counts,
            "average_score": (sum(readiness_scores) / len(readiness_scores)) if readiness_scores else None,
        }

        insights = {
            "en": (
                f"Saved approximately {total_manual_minutes:.1f} minutes (≈ ${total_cost_saved:.2f}) of manual effort across {len(results)} files. "
                f"Top rationale codes: {top_rationale_codes}."
            ),
            "ja": (
                f"{len(results)} 件の処理で推定 {total_manual_minutes:.1f} 分 (約 ${total_cost_saved:.2f}) の手作業を削減しました。"
                f" 主な推奨理由コード: {top_rationale_codes}。"
            ),
        }

        return {
            "summary": {
                "total_files": len(results),
                "successful": successful,
                "failed": failed,
                "success_rate": successful / len(results) if results else 0,
                "total_processing_time": total_time,
                "average_processing_time": total_time / len(results) if results else 0,
                "aggregate_risk_score": aggregate_risk,
                "highest_risk_score": highest_risk,
                "total_manual_minutes_saved": total_manual_minutes,
                "average_manual_minutes_saved": average_manual_minutes,
                "total_manual_cost_saved_usd": round(total_manual_cost, 2),
                "severity_counts": severity_counts,
                "warning_count": overall_warning_count,
                "manifest_warning_count": manifest_warning_count,
                "top_issues": common_issues,
                "top_rationales": common_rationales,
                "readiness": readiness_summary,
                "insights": insights,
            },
            "compliance": compliance_metadata,
            "files": results
        }

    def print_summary(self, summary: Dict[str, Any]) -> None:
        """Print processing summary."""
        s = summary["summary"]
        print(f"\n{'='*50}")
        processed_label = self._format_locale_string("Processed", "処理件数") or "Processed"
        print(f"{processed_label}: {s['total_files']} files")
        success_label = self._format_locale_string("Success", "成功") or "Success"
        failed_label = self._format_locale_string("Failed", "失敗") or "Failed"
        print(f"{success_label}: {s['successful']} | {failed_label}: {s['failed']}")
        rate_label = self._format_locale_string("Success rate", "成功率") or "Success rate"
        print(f"{rate_label}: {s['success_rate']:.1%}")
        total_time_label = self._format_locale_string("Total time", "総処理時間") or "Total time"
        print(f"{total_time_label}: {s['total_processing_time']:.2f}s")
        avg_time_label = self._format_locale_string("Average per file", "平均処理時間") or "Average per file"
        print(f"{avg_time_label}: {s['average_processing_time']:.2f}s")

        # Enhanced success/failure breakdown
        if s['failed'] > 0:
            print(f"\n{'='*30}")
            failure_breakdown_label = self._format_locale_string("Failure Breakdown", "失敗内訳") or "Failure Breakdown"
            print(f"{failure_breakdown_label}")

            failed_files = [f for f in summary["files"] if not f["success"]]
            error_categories: Dict[str, List[str]] = {}

            for result in failed_files:
                error_msg = result.get("error", "Unknown error")
                if error_msg not in error_categories:
                    error_categories[error_msg] = []
                error_categories[error_msg].append(Path(result["file"]).name)

            for error_msg, files in sorted(error_categories.items(), key=lambda x: len(x[1]), reverse=True):
                print(f"  {error_msg}: {len(files)} files")
                if len(files) <= 3:  # Show file names if not too many
                    for file in files:
                        print(f"    - {file}")
                else:
                    print(f"    - {', '.join(files[:3])}...")

            print(f"{'='*30}")

        compliance = summary.get("compliance", {})
        if compliance:
            policy_label = self._format_locale_string("Compliance policy", "準拠ポリシー") or "Compliance policy"
            print(f"{policy_label}: {compliance.get('policy_reference', 'n/a')}")
            path_label = self._format_locale_string("Path safety enforced", "パス安全性の強制") or "Path safety enforced"
            print(f"{path_label}: {compliance.get('path_safety_enforced', False)}")
            symlink_label = self._format_locale_string("Symlink protection enforced", "シンボリックリンク防御") or "Symlink protection enforced"
            print(f"{symlink_label}: {compliance.get('symlink_protection_enforced', False)}")

        roi_label = self._format_locale_string("ROI estimate", "ROI 評価") or "ROI estimate"
        print(f"\n{roi_label}:")
        total_minutes_label = self._format_locale_string("Manual time saved (total)", "手作業削減時間(合計)") or "Manual time saved (total)"
        avg_minutes_label = self._format_locale_string("Manual time saved (avg)", "手作業削減時間(平均)") or "Manual time saved (avg)"
        cost_label = self._format_locale_string("Cost avoided", "削減コスト") or "Cost avoided"
        print(f"  {total_minutes_label}: {s['total_manual_minutes_saved']:.1f} min")
        print(f"  {avg_minutes_label}: {s['average_manual_minutes_saved']:.1f} min/file")
        print(f"  {cost_label}: ${s['total_manual_cost_saved_usd']:.2f}")

        severity_counts = s.get("severity_counts", {})
        if severity_counts:
            severity_label = self._format_locale_string("Issue severity totals", "重大度別件数") or "Issue severity totals"
            print(f"\n{severity_label}:")
            for severity, count in severity_counts.items():
                print(f"  {severity.title()}: {count}")

        manifest_warning_count = s.get("manifest_warning_count", 0)
        if manifest_warning_count:
            manifest_label = self._format_locale_string(
                "Hash manifest warnings",
                "ハッシュマニフェスト警告件数",
            ) or "Hash manifest warnings"
            print(f"{manifest_label}: {manifest_warning_count}")

        top_issues = s.get("top_issues", [])
        if top_issues:
            issues_label = self._format_locale_string("Top Issues", "主な課題") or "Top Issues"
            print(f"\n{issues_label}:")
            for code, count in top_issues:
                print(f"  {code}: {count}")

        top_rationales = s.get("top_rationales", [])
        if top_rationales:
            rationales_label = self._format_locale_string("Top Recommendations", "主な推奨事項") or "Top Recommendations"
            print(f"\n{rationales_label}:")
            for code, count in top_rationales:
                print(f"  {code}: {count}")

        readiness_summary = s.get("readiness", {})
        readiness_counts = readiness_summary.get("counts", {})
        readiness_avg = readiness_summary.get("average_score")
        readiness_label = self._format_locale_string("Print readiness status", "造形準備ステータス") or "Print readiness status"
        if readiness_counts:
            print(f"\n{readiness_label}:")
            for status, count in sorted(readiness_counts.items(), key=lambda item: (-item[1], item[0])):
                print(f"  {status}: {count}")
        if readiness_avg is not None:
            avg_readiness_label = self._format_locale_string("Average readiness score", "平均造形準備スコア") or "Average readiness score"
            print(f"{avg_readiness_label}: {readiness_avg:.1f}")

        top_issues = s.get("top_issues", [])
        if top_issues:
            top_issues_label = self._format_locale_string("Top recurring issues", "頻出課題") or "Top recurring issues"
            print(f"\n{top_issues_label}:")
            for code, count in top_issues:
                print(f"  {code}: {count}")

        top_rationales = s.get("top_rationales", [])
        if top_rationales:
            rationales_label = self._format_locale_string("Top rationales", "主な推奨理由") or "Top rationales"
            print(f"\n{rationales_label}:")
            for code, count in top_rationales:
                print(f"  {code}: {count}")

        insights = s.get("insights")
        if insights:
            insights_label = self._format_locale_string("Insights", "考察") or "Insights"
            print(f"\n{insights_label}:")
            for line in self._format_locale_lines(insights.get("en"), insights.get("ja")):
                print(f"  {line}")

        if s['failed'] > 0:
            failed_label = self._format_locale_string("Failed files", "失敗したファイル") or "Failed files"
            print(f"\n{failed_label}:")
            for r in summary["files"]:
                if not r["success"]:
                    print(f"  - {Path(r['file']).name}: {r.get('error', 'Unknown error')}")

    def _write_metrics_output(self, target: Optional[Path], records: List[Dict[str, Any]]) -> None:
        if not target:
            return

        minimal_records: List[Dict[str, Any]] = []
        for record in records:
            warnings = [issue for issue in (record.get("issues") or []) if issue.get("severity") == "warning"]
            manifest_warning_count = len([
                issue for issue in warnings if issue.get("code") == "HASH_MANIFEST"
            ])
            minimal_records.append(
                {
                    "file": record.get("file"),
                    "success": record.get("success"),
                    "risk_score": record.get("risk_score"),
                    "warning_count": record.get("warning_count", len(warnings)),
                    "manifest_warning_count": manifest_warning_count,
                    "warnings": warnings,
                    "errors": [issue for issue in (record.get("issues") or []) if issue.get("severity") == "error"],
                    "processing_time": record.get("processing_time"),
                    "estimated_manual_minutes_saved": record.get("estimated_manual_minutes_saved"),
                    "readiness": record.get("readiness"),
                }
            )

        target_path = target.expanduser()
        extension = target_path.suffix.lower()
        if extension == ".jsonl":
            lines = [json.dumps(entry, ensure_ascii=False) for entry in minimal_records]
            target_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            target_path.write_text(json.dumps(minimal_records, indent=2, ensure_ascii=False), encoding="utf-8")

    def _write_failure_output(self, target: Optional[Path], records: List[Dict[str, Any]]) -> None:
        if not target:
            return

        failures = [
            {
                "file": record.get("file"),
                "error": record.get("error"),
                "notes": record.get("notes"),
                "success": record.get("success"),
            }
            for record in records
            if not record.get("success")
        ]

        target_path = target.expanduser()
        target_path.write_text(json.dumps(failures, indent=2, ensure_ascii=False), encoding="utf-8")

    def run(self, argv: Optional[list[str]] = None) -> int:
        """Main entry point."""
        try:
            args = self.parse_args(argv)

            # Handle special commands
            if args.list_formats:
                for ext in sorted(MESH_EXTENSIONS):
                    print(ext)
                return 0

            if getattr(args, 'compare_config', None):
                self._compare_config_files(args.compare_config[0], args.compare_config[1])
                return 0

            if getattr(args, 'benchmark', None):
                if not files:
                    print("No files specified for benchmarking", file=sys.stderr)
                    return 1
                self._run_benchmark(files[0], args.benchmark, args)
                return 0

            # Setup logging
            log_level = getattr(args, 'log_level', None)
            if log_level:
                # Override config with command line argument
                level_map = {
                    "DEBUG": LogLevel.DEBUG,
                    "INFO": LogLevel.INFO,
                    "WARNING": LogLevel.WARNING,
                    "ERROR": LogLevel.ERROR
                }
                configured_level = level_map.get(log_level, LogLevel.INFO)
            else:
                configured_level = LogLevel.DEBUG if args.verbose else LogLevel.INFO

            configure_logging(
                level=configured_level,
                enable_file_logging=args.verbose,
                enable_json_logging=True
            )

            # Create session context with enhanced metadata
            context = create_context(
                session_id=self.session_id,
                operation="cli_processing",
                user_id=getattr(args, 'user_id', None),
                batch_mode=getattr(args, 'batch', False),
                parallel_mode=getattr(args, 'parallel', False),
                language_mode=self.language_mode
            )
            self.logger.set_context(context)

            # Log session start
            self.logger.info(
                "CLI session started",
                extra={
                    "session_id": self.session_id,
                    "operation": "cli_processing",
                    "batch_mode": getattr(args, 'batch', False),
                    "parallel_mode": getattr(args, 'parallel', False),
                    "verbose_mode": getattr(args, 'verbose', False)
                }
            )

            # Find files
            files, hints = self.find_mesh_files(args)

            if hints and args.progress:
                for hint in hints:
                    print(f"Hint: {hint}")

            if not files:
                if args.list_files:
                    print("No mesh files found.")
                    return 0
                if not (args.files or args.pattern or args.input_dir):
                    print("No input files specified. Use -h for help.")
                    return 1

        def process_batch(self, files: List[Path], args: argparse.Namespace) -> List[Dict[str, Any]]:
            """Process a batch of mesh files with optimized parallel processing.
            
            Args:
                files: List of file paths to process
                args: Command line arguments
                
            Returns:
                List of processing results
            """
            if not files:
                return []

            total_files = len(files)
            start_time = time.monotonic()
            results: List[Dict[str, Any]] = []
            
            # 並列処理が無効またはファイルが1つの場合は逐次処理
            if not args.parallel or total_files == 1:
                return self._process_files_sequential(files, args, 0, total_files, start_time)

            try:
                # システムリソースに基づいて並列数を動的に決定
                cpu_count = os.cpu_count() or 1
                available_memory = psutil.virtual_memory().available / (1024 ** 3)  # GB単位
                
                # メモリ制約を考慮した最大並列数の計算
                max_by_memory = max(1, int(available_memory / 2))  # 2GBあたり1プロセス
                max_workers = min(
                    self.max_worker_limit,
                    cpu_count,
                    max_by_memory,
                    total_files
                )
                
                # バッチサイズを動的に調整
                try:
                    avg_file_size = sum(f.stat().st_size for f in files) / total_files if total_files > 0 else 0
                    batch_size = self._calculate_optimal_batch_size(avg_file_size, max_workers)
                except (OSError, AttributeError):
                )
            return formatted_results if 'formatted_results' in locals() else []
            
    def _process_single_file(self, file_path: Path, args: argparse.Namespace, **kwargs) -> Dict[str, Any]:
        """Process a single file (wrapper for parallel processing)."""
        try:
            return self.process_mesh(file_path, args)
        except Exception as e:
            return {
                'file': str(file_path),
                'error': str(e),
                'success': False,
                'traceback': traceback.format_exc()
            }
                else:
                    # Sequential hash computation (original implementation)
                    for file in files:
                        hash_ok, hash_value = self._compute_file_hash(file)
                        if hash_ok:
                            hashes[str(file)] = hash_value

                            manifest_ok, manifest_error, expected_digest = self._verify_manifest_digest(file, hash_value)
                            if not manifest_ok:
                                manifest_failures.append({
                                    "file": str(file),
                                    "error": manifest_error,
                                    "expected": expected_digest,
                                    "observed": hash_value
                                })
                        else:
                            manifest_failures.append({
                                "file": str(file),
                                "error": hash_value,
                                "expected": None,
                                "observed": None
                            })

                ordered_hashes = {path: hashes[path] for path in sorted(hashes)}
                payload = {
                    "files": ordered_hashes,
                    "compliance": self._compliance_metadata()
                }

                if args.output:
                    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
                else:
                    print(json.dumps(payload, indent=2, ensure_ascii=False))

                if manifest_failures:
                    for failure in manifest_failures:
                        print(
                            json.dumps(
                                {
                                    "file": failure["file"],
                                    "error": failure["error"],
                                    "expected_sha256": failure["expected"],
                                    "observed_sha256": failure["observed"]
                                },
                                indent=2,
                                ensure_ascii=False
                            )
                        )
                    return 1
                return 0

            # Process files
            if len(files) == 1 and not args.batch:
                # Single file mode
                if args.progress:
                    self._write_metrics_output(args.metrics_output, [result])

                if getattr(args, "failure_output", None):
                    self._write_failure_output(args.failure_output, [result])

                if not args.quiet:
                    self._print_single_result_summary(result)

                return 0 if result["success"] else 1

            else:
                # Batch mode
                results = self.process_batch(files, args)

                # Generate summary
                summary = self.generate_summary(results)

                # Save results
                if args.output:
                    output_data = summary if args.summary else {"files": results}

                    # Validate output if requested
                    if getattr(args, 'validate_output', False):
                        validation_result = self._validate_json_output(output_data)
                        if not validation_result["valid"]:
                            print(f"Warning: JSON output validation failed: {validation_result['error']}", file=sys.stderr)
                            # Don't prevent output, just warn

                    args.output.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
                    if args.progress:
                        print(f"Report saved to: {args.output}")

                if getattr(args, "summary_output", None):
                    args.summary_output.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

                if getattr(args, "metrics_output", None):
                    self._write_metrics_output(args.metrics_output, results)

                if getattr(args, "failure_output", None):
                    self._write_failure_output(args.failure_output, results)

                # Print summary
                if args.summary and not args.quiet:
                    self.print_summary(summary)
                    # Enhanced batch statistics
                    batch_start_time = getattr(self, '_batch_start_time', time.time())
                    self._print_enhanced_batch_statistics(results, batch_start_time, args)

                return 0 if summary["summary"]["failed"] == 0 else 1

        except KeyboardInterrupt:
            self.logger.info("Operation interrupted by user")
            print("\nOperation interrupted by user", file=sys.stderr)
            return 130  # Standard exit code for SIGINT

        except FileNotFoundError as exc:
            self.logger.error("File not found: %s", exc)
            print(f"File not found: {exc}", file=sys.stderr)
            return 2  # No such file or directory

        except PermissionError as exc:
            self.logger.error("Permission denied: %s", exc)
            print(f"Permission denied: {exc}", file=sys.stderr)
            return 13  # Permission denied

        except MemoryError as exc:
            self.logger.error("Out of memory: %s", exc)
            print("Out of memory. Try processing fewer files or reducing memory usage.", file=sys.stderr)
            return 137  # Out of memory (SIGKILL)

        except (BrokenProcessPool, RuntimeError) as exc:
            self.logger.error("Processing runtime error: %s", exc)
            print(f"Processing error: {exc}", file=sys.stderr)
            return 70  # Software error

        except Exception as exc:
            self.logger.error("Unexpected error during CLI execution: %s", exc, exc_info=True)
            error_msg = self._format_locale_string(
                f"Unexpected error: {exc}",
                f"予期せぬエラー: {exc}"
            ) or f"Unexpected error: {exc}"
            print(error_msg, file=sys.stderr)

            # Print stack trace in verbose mode
            if getattr(args, 'verbose', False):
                import traceback
                print("\nTraceback:", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

            return 1  # General error


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point."""
    # Ensure proper encoding for CLI output
    import locale
    import io

    # Set stdout/stderr encoding to UTF-8 for consistent output
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass  # Fallback to default encoding if reconfigure fails

    processor = CLIProcessor()
    return processor.run(argv)


if __name__ == "__main__":
    sys.exit(main())