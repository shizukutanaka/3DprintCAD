"""REST API endpoints for 3D print validation and processing."""
from flask import Blueprint, request, jsonify, current_app, url_for, g
from werkzeug.utils import secure_filename
from pathlib import Path
import re
import uuid
import logging
import time

logger = logging.getLogger(__name__)

from ..adapters import load_mesh
from ..core.analysis import mesh_validator
from ..core.analysis.mesh_repair import repair_mesh
from ..core.recommendation import RecommendationEngine
from ..core.slicing import SlicingEngine, SliceSettings
from ..core.security import (
    sanitize_filename,
    validate_mesh_file,
    save_uploaded_file,
)
from ..core.analysis.topology_optimization import optimize_topology, TopologyOptimizationSettings, create_simple_load_case
from ..core.simulation_based_design import analyze_structure, get_design_recommendations
from ..core.input_validator import (
    input_validator,
    MESH_VALIDATION_RULES,
    SLICE_SETTINGS_RULES
)
from ..core.automation import (
    auto_validate_file,
    auto_repair_file,
    FileTypeDetector
)

api_bp = Blueprint('api', __name__)

ALLOWED_EXTENSIONS = {'.stl', '.obj', '.ply', '.3mf', '.amf'}
FILE_ID_PATTERN = re.compile(r"^[a-f0-9\-]{8,}$", re.IGNORECASE)


def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _mesh_size_limit_mb() -> int:
    try:
        return int(current_app.config.get('MAX_MESH_SIZE_MB', 100))
    except (TypeError, ValueError):
        return 100


def _max_batch_files() -> int:
    """Return configured maximum batch files with safe fallback."""
    try:
        limit = int(current_app.config.get('MAX_BATCH_FILES', 20))
    except (TypeError, ValueError):
        return 20

    return max(1, limit)


def _ensure_request_time_budget() -> None:
    """Abort if the request has exceeded its allotted time budget."""
    checker = getattr(current_app, 'check_request_timeout', None)
    if callable(checker):
        checker()


def _resolve_uploaded_file(file_id: str) -> Path:
    if not FILE_ID_PATTERN.match(file_id):
        raise ValueError("Invalid file identifier")

    upload_dir: Path = current_app.config['UPLOAD_FOLDER']
    matches = list(upload_dir.glob(f"{file_id}_*"))
    if len(matches) != 1:
        raise FileNotFoundError("File not found")

    stored = matches[0]
    resolved = stored.resolve(strict=True)
    if resolved.is_dir():
        raise FileNotFoundError("File not found")
    if resolved.is_symlink():
        raise ValueError("Symbolic links are not permitted")

    try:
        resolved.relative_to(upload_dir)
    except ValueError as exc:
        raise ValueError("Resolved path escapes upload directory") from exc

    return resolved


def _delete_if_exists(path: Path | None) -> None:
    if not path:
        return
    try:
        candidate = Path(path)
    except TypeError:
        return

    if not candidate.exists() or candidate.is_dir():
        return

    try:
        candidate.unlink()
    except OSError:
        return


@api_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'timestamp': time.time()})

@api_bp.route('/upload', methods=['POST'])
@rate_limit('/api/upload')
def upload_file():
    """Upload and validate a mesh file with auto-validation."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check for auto-validate flag
    auto_validate = request.form.get('auto_validate', 'true').lower() == 'true'

    # Client-side validation
    file_validation = input_validator.validate_file_upload(
        filename=file.filename,
        content_type=file.mimetype,
        file_size=request.content_length or 0,
        allowed_extensions=list(ALLOWED_EXTENSIONS),
        max_size_mb=_mesh_size_limit_mb()
    )

    if not file_validation['valid']:
        return jsonify({'error': 'Validation failed', 'details': file_validation['errors']}), 400

    _ensure_request_time_budget()

    if not allowed_file(file.filename):
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    allowed_mimetypes = current_app.config.get('ALLOWED_UPLOAD_MIMETYPES') or set()
    if allowed_mimetypes and file.mimetype not in allowed_mimetypes:
        return jsonify({
            'error': 'Unsupported MIME type',
            'received': file.mimetype,
            'allowed': sorted(list(allowed_mimetypes)),
        }), 400

    try:
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        stored_name = sanitize_filename(f"{file_id}_{filename}")
        upload_dir: Path = current_app.config['UPLOAD_FOLDER']
        file_path = upload_dir / stored_name

        max_bytes = _mesh_size_limit_mb() * 1024 * 1024
        try:
            bytes_written = save_uploaded_file(file, file_path, max_bytes)
        except ValueError as exc:
            _delete_if_exists(file_path)
            return jsonify({'error': 'Upload rejected', 'messages': [str(exc)]}), 400
        except OSError as exc:
            _delete_if_exists(file_path)
            logger.exception(
                "File storage error",
                extra={
                    "filename": filename,
                    "error_type": type(exc).__name__
                }
            )
            return jsonify({'error': 'Storage failure while saving file'}), 500

        _ensure_request_time_budget()

        validation = validate_mesh_file(
            file_path,
            max_size_mb=_mesh_size_limit_mb(),
        )

        if not validation.get('valid', False):
            _delete_if_exists(file_path)
            return jsonify({'error': 'Upload rejected', 'messages': validation.get('errors', [])}), 400

        # Auto-detect file format
        format_info = FileTypeDetector.detect_format(file_path)

        response_payload = {
            'file_id': file_id,
            'filename': filename,
            'size_bytes': bytes_written,
            'hash_sha256': validation.get('file_hash'),
            'download_url': url_for('uploaded_file', filename=stored_name, _external=False),
            'format': format_info
        }

        # Auto-validation if requested
        if auto_validate:
            try:
                _ensure_request_time_budget()
                auto_validation = auto_validate_file(file_path)
                response_payload['validation'] = auto_validation.get('validation')
                response_payload['recommendations'] = auto_validation.get('recommendations')
                response_payload['auto_repairable'] = auto_validation.get('auto_repairable', False)
            except Exception as e:
                logger.warning(f"Auto-validation failed for {file_id}: {e}")
                response_payload['validation_error'] = str(e)

        return jsonify(response_payload)

    except Exception as e:
        _delete_if_exists(locals().get('file_path', Path()))
        logger.exception(
            "File upload error",
            extra={
                "filename": filename if 'filename' in locals() else 'unknown',
                "error_type": type(e).__name__
            }
        )
        return jsonify({'error': str(e)}), 500

@api_bp.route('/validate/<file_id>', methods=['POST'])
@rate_limit('/api/validate')
def validate_mesh(file_id):
    """Validate an uploaded mesh."""
    try:
        # Get settings from request with size limit
        try:
            data = request.get_json(force=False, silent=False, cache=True)
            if data is None:
                data = {}
        except Exception:
            return jsonify({'error': 'Invalid JSON payload'}), 400

        # Validate input data
        validation_result = input_validator.validate_data(data, MESH_VALIDATION_RULES)
        if not validation_result['valid']:
            return jsonify({'error': 'Invalid input', 'details': validation_result['errors']}), 400

        sanitized_data = validation_result['sanitized_data']

        settings = mesh_validator.MeshValidationSettings(
            min_wall_thickness=sanitized_data.get('min_wall_thickness', 0.8),
            min_feature_size=sanitized_data.get('min_feature_size', 0.4),
            max_overhang_angle=sanitized_data.get('max_overhang_angle', 60)
        )

        # Find file
        try:
            file_path = _resolve_uploaded_file(file_id)
        except FileNotFoundError:
            return jsonify({'error': 'File not found'}), 404
        except ValueError:
            return jsonify({'error': 'Invalid file identifier'}), 400

        validation = validate_mesh_file(
            file_path,
            max_size_mb=_mesh_size_limit_mb(),
        )
        if not validation.get('valid', False):
            return jsonify({'error': 'Stored file no longer passes validation', 'messages': validation.get('errors', [])}), 400

        # Load and validate
        mesh = load_mesh(file_path)
        validation_result = mesh_validator.validate_mesh(mesh, settings=settings)

        # Generate recommendations
        recommender = RecommendationEngine()
        recommendations = recommender.generate_recommendations(validation_result)

        return jsonify({
            'validation': validation_result.to_dict(),
            'recommendations': recommendations.to_dict()
        })

    except Exception as e:
        logger.exception(
            "Mesh validation error",
            extra={
                "file_id": file_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        return jsonify({'error': str(e)}), 500

@api_bp.route('/repair/<file_id>', methods=['POST'])
@rate_limit('/api/repair')
def repair_mesh_api(file_id):
    """Repair mesh issues."""
    try:
        # Get settings from request with size limit
        try:
            data = request.get_json(force=False, silent=False, cache=True)
            if data is None:
                data = {}
        except Exception:
            return jsonify({'error': 'Invalid JSON payload'}), 400

        aggressive = bool(data.get('aggressive', False))

        # Find file
        try:
            file_path = _resolve_uploaded_file(file_id)
        except FileNotFoundError:
            return jsonify({'error': 'File not found'}), 404
        except ValueError:
            return jsonify({'error': 'Invalid file identifier'}), 400

        # Load and repair
        mesh = load_mesh(file_path)
        repaired_mesh = repair_mesh(mesh, aggressive=aggressive)

        if repaired_mesh:
            # Save repaired mesh
            repaired_id = str(uuid.uuid4())
            repaired_filename = sanitize_filename(f"{repaired_id}_repaired.stl")
            repaired_dir: Path = current_app.config['RESULTS_FOLDER']
            repaired_path = repaired_dir / repaired_filename

            # Save using trimesh
            repaired_mesh.export(str(repaired_path))

            validate_mesh_file(
                repaired_path,
                max_size_mb=_mesh_size_limit_mb(),
            )

            # Re-validate repaired mesh
            validation_result = mesh_validator.validate_mesh(repaired_mesh)

            return jsonify({
                'success': True,
                'repaired_id': repaired_id,
                'download_url': url_for('result_file', filename=repaired_filename, _external=False),
                'validation': validation_result.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Unable to repair mesh'
            })

    except Exception as e:
        logger.exception(
            "Mesh validation error",
            extra={
                "file_id": file_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        return jsonify({'error': str(e)}), 500

@api_bp.route('/slice/<file_id>', methods=['POST'])
@rate_limit('/api/slice')
def slice_mesh_api(file_id):
    """Generate slicing data for mesh."""
    try:
        # Get settings from request with size limit
        try:
            data = request.get_json(force=False, silent=False, cache=True)
            if data is None:
                data = {}
        except Exception:
            return jsonify({'error': 'Invalid JSON payload'}), 400

        # Validate input data
        validation_result = input_validator.validate_data(data, SLICE_SETTINGS_RULES)
        if not validation_result['valid']:
            return jsonify({'error': 'Invalid input', 'details': validation_result['errors']}), 400

        sanitized_data = validation_result['sanitized_data']

        # Create slice settings
        settings = SliceSettings(
            layer_height=sanitized_data.get('layer_height', 0.2),
            infill_density=sanitized_data.get('infill_density', 20),
            print_speed=sanitized_data.get('print_speed', 60),
            support_enabled=sanitized_data.get('support_enabled', True),
            support_angle=sanitized_data.get('support_angle', 45)
        )

        # Find file
        try:
            file_path = _resolve_uploaded_file(file_id)
        except FileNotFoundError:
            return jsonify({'error': 'File not found'}), 404
        except ValueError:
            return jsonify({'error': 'Invalid file identifier'}), 400

        # Load and slice
        mesh = load_mesh(file_path)
        slicer = SlicingEngine(settings)
        slicing_result = slicer.slice_mesh(mesh)

        return jsonify({
            'total_layers': slicing_result.total_layers,
            'print_time_hours': slicing_result.total_print_time_seconds / 3600,
            'material_grams': slicing_result.total_material_grams,
            'layer_data': [
                {
                    'z': layer.z_position,
                    'perimeters': len(layer.perimeters),
                    'infill_lines': len(layer.infill_lines)
                }
                for layer in slicing_result.layers[:10]  # First 10 layers as preview
            ]
        })

    except Exception as e:
        logger.exception(
            "Mesh validation error",
            extra={
                "file_id": file_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        return jsonify({'error': str(e)}), 500

@api_bp.route('/batch', methods=['POST'])
@rate_limit('/api/batch')
def batch_process():
    """Process multiple files in batch."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files selected'}), 400

    max_batch_files = _max_batch_files()
    if len(files) > max_batch_files:
        return jsonify({
            'error': 'Batch size exceeds limit',
            'max_batch_files': max_batch_files,
            'received_files': len(files),
        }), 400

    results = []
    for file in files:
        if file and allowed_file(file.filename):
            file_path = None
            try:
                filename = secure_filename(file.filename)
                file_id = str(uuid.uuid4())
                stored_name = sanitize_filename(f"{file_id}_{filename}")
                file_path = current_app.config['UPLOAD_FOLDER'] / stored_name

                max_bytes = _mesh_size_limit_mb() * 1024 * 1024
                try:
                    _ensure_request_time_budget()
                    save_uploaded_file(file, file_path, max_bytes)
                except ValueError as exc:
                    _delete_if_exists(file_path)
                    results.append({
                        'filename': filename,
                        'file_id': file_id,
                        'success': False,
                        'error': str(exc)
                    })
                    continue
                except OSError as exc:
                    _delete_if_exists(file_path)
                    logger.exception(
                        "File storage error during batch upload",
                        extra={
                            "filename": filename,
                            "error_type": type(exc).__name__
                        }
                    )
                    results.append({
                        'filename': filename,
                        'file_id': file_id,
                        'success': False,
                        'error': 'Storage failure while saving file'
                    })
                    continue

                _ensure_request_time_budget()

                validation = validate_mesh_file(
                    file_path,
                    max_size_mb=_mesh_size_limit_mb(),
                )
                if not validation.get('valid', False):
                    _delete_if_exists(file_path)
                    results.append({
                        'filename': filename,
                        'file_id': file_id,
                        'success': False,
                        'error': '; '.join(validation.get('errors', [])) or 'Validation failed'
                    })
                    continue

                # Process
                mesh = load_mesh(file_path)
                validation_result = mesh_validator.validate_mesh(mesh)

                results.append({
                    'filename': filename,
                    'file_id': file_id,
                    'success': True,
                    'issues_count': len(validation_result.issues),
                    'is_valid': validation_result.is_valid,
                    'download_url': url_for('uploaded_file', filename=stored_name, _external=False),
                })

            except Exception as e:
                _delete_if_exists(file_path)
                results.append({
                    'filename': filename if 'filename' in locals() else getattr(file, 'filename', 'unknown'),
                    'success': False,
                    'error': str(e)
                })
        else:
            results.append({
                'filename': getattr(file, 'filename', 'unknown'),
                'success': False,
                'error': 'Unsupported file type'
            })

    return jsonify({
        'processed': len(results),
        'results': results
    })

@api_bp.route('/auto-repair/<file_id>', methods=['POST'])
@rate_limit('/api/auto-repair')
def auto_repair_endpoint(file_id):
    """Automatically repair mesh if needed."""
    try:
        # Find file
        try:
            file_path = _resolve_uploaded_file(file_id)
        except FileNotFoundError:
            return jsonify({'error': 'File not found'}), 404
        except ValueError:
            return jsonify({'error': 'Invalid file identifier'}), 400

        # Auto-repair
        result = auto_repair_file(
            file_path,
            output_path=current_app.config['RESULTS_FOLDER'] / f"{file_id}_repaired.stl"
        )

        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.exception(
            "Auto-repair error",
            extra={
                "file_id": file_id,
                "error_type": type(e).__name__
            }
        )
        return jsonify({'error': str(e)}), 500

@api_bp.route('/formats', methods=['GET'])
def supported_formats():
    """Get list of supported file formats."""
    return jsonify({
        'formats': [
            {'extension': '.stl', 'name': 'Stereolithography', 'binary': True, 'ascii': True},
            {'extension': '.obj', 'name': 'Wavefront OBJ', 'binary': False, 'ascii': True},
            {'extension': '.ply', 'name': 'Polygon File Format', 'binary': True, 'ascii': True},
        ]
    })

@api_bp.route('/ai/generate-3d', methods=['POST'])
@rate_limit('ai_requests', 10, 60)  # 10 requests per minute
def generate_3d_from_text_api():
    """Generate 3D model from text description."""
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing prompt parameter'}), 400

        prompt = data['prompt'].strip()
        if not prompt:
            return jsonify({'error': 'Empty prompt'}), 400

        if len(prompt) > 500:
            return jsonify({'error': 'Prompt too long (max 500 characters)'}), 400

        # Generate 3D model
        result = generate_3d_from_text(prompt)

        if result.success:
            # Save generated model temporarily
            output_dir = Path(current_app.config.get('UPLOAD_DIR', './uploads'))
            output_dir.mkdir(exist_ok=True)

            model_id = str(uuid.uuid4())
            output_path = output_dir / f"ai_generated_{model_id}.stl"

            # Export as STL
            result.mesh.export(str(output_path))

            response_data = {
                'success': True,
                'id': model_id,
                'metadata': result.metadata,
                'confidence_score': result.confidence_score,
                'warnings': result.warnings,
                'download_url': url_for('api.download_generated_model', model_id=model_id, _external=True)
            }

            return jsonify(response_data)

        else:
            return jsonify({
                'success': False,
                'error': 'Generation failed',
                'warnings': result.warnings
            }), 400

    except Exception as e:
        logger.exception("AI 3D generation error")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/ai/chat', methods=['POST'])
@rate_limit('ai_chat_requests', 20, 60)  # 20 requests per minute
def ai_chat_api():
    """AI chat assistant for design help."""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Missing query parameter'}), 400

        query = data['query'].strip()
        if not query:
            return jsonify({'error': 'Empty query'}), 400

        if len(query) > 1000:
            return jsonify({'error': 'Query too long (max 1000 characters)'}), 400

        context = data.get('context', {})

        # Get AI response
        result = chat_with_ai_assistant(query, context)

        response_data = {
            'answer': result.get('answer', 'I\'m sorry, I couldn\'t process your question.'),
            'suggestions': result.get('suggestions', []),
            'confidence': result.get('confidence', 0.0)
        }

        # Add code snippets if available
        if 'code_snippets' in result and result['code_snippets']:
            response_data['code_snippets'] = result['code_snippets']

        return jsonify({
            'success': False,
            'error': 'Generation failed',
            'warnings': result.warnings
        }), 400

    except Exception as e:
        logger.exception("AI 3D generation error")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/ai/chat', methods=['POST'])
@rate_limit('ai_chat_requests', 20, 60)  # 20 requests per minute
def ai_chat_api():
    """AI chat assistant for design help."""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Missing query parameter'}), 400

        query = data['query'].strip()
        if not query:
            return jsonify({'error': 'Empty query'}), 400

        if len(query) > 1000:
            return jsonify({'error': 'Query too long (max 1000 characters)'}), 400

        context = data.get('context', {})

        # Get AI response
        result = chat_with_ai_assistant(query, context)

        response_data = {
            'answer': result.get('answer', 'I\'m sorry, I couldn\'t process your question.'),
            'suggestions': result.get('suggestions', []),
            'confidence': result.get('confidence', 0.0)
        }

        # Add code snippets if available
        if 'code_snippets' in result and result['code_snippets']:
            response_data['code_snippets'] = result['code_snippets']

        return jsonify(response_data)

    except Exception as e:
        logger.exception("AI chat error")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/topology/optimize', methods=['POST'])
@rate_limit('topology_requests', 5, 60)  # 5 requests per minute (computationally intensive)
def topology_optimization_api():
    """Perform topology optimization on a 3D model."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Parse parameters
        volume_fraction = float(request.form.get('volume_fraction', 0.3))
        max_iterations = int(request.form.get('max_iterations', 50))
        force_magnitude = float(request.form.get('force_magnitude', 1000.0))

        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = save_uploaded_file(file, filename)
        if not file_path:
            return jsonify({'error': 'File upload failed'}), 500

        try:
            # Load mesh
            mesh = load_mesh(file_path)

            # Create optimization settings
            settings = TopologyOptimizationSettings(
                volume_fraction=volume_fraction,
                max_iterations=max_iterations
            )

            # Create simple load case
            load_case = create_simple_load_case(mesh, force_magnitude)

            # Perform optimization
            result = optimize_topology(mesh, load_case, settings)

            if result.convergence_achieved:
                # Save optimized mesh
                output_dir = Path(current_app.config.get('UPLOAD_DIR', './uploads'))
                output_dir.mkdir(exist_ok=True)

                model_id = str(uuid.uuid4())
                output_path = output_dir / f"optimized_{model_id}.stl"

                result.optimized_mesh.export(str(output_path))

                response_data = {
                    'success': True,
                    'id': model_id,
                    'optimization_result': {
                        'final_objective': result.final_objective,
                        'final_volume_fraction': result.final_volume_fraction,
                        'iterations_used': result.iterations_used,
                        'convergence_achieved': result.convergence_achieved,
                        'optimization_time': result.optimization_time
                    },
                    'download_url': url_for('api.download_optimized_model', model_id=model_id, _external=True)
                }

                return jsonify(response_data)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Optimization did not converge',
                    'iterations_used': result.iterations_used
                }), 400

        finally:
            # Clean up uploaded file
            if file_path.exists():
                file_path.unlink()

    except Exception as e:
        logger.exception("Topology optimization error")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/simulation/analyze', methods=['POST'])
@rate_limit('simulation_requests', 10, 60)  # 10 requests per minute
def structural_analysis_api():
    """Perform structural analysis on a 3D model."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Parse parameters
        material_name = request.form.get('material', 'steel')
        force_magnitude = float(request.form.get('force_magnitude', 1000.0))

        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = save_uploaded_file(file, filename)
        if not file_path:
            return jsonify({'error': 'File upload failed'}), 500

        try:
            # Load mesh
            mesh = load_mesh(file_path)

            # Perform analysis
            result = analyze_structure(mesh, material_name)

            if result.converged:
                # Get recommendations
                recommendations = get_design_recommendations(result, material_name, mesh)

                # Convert recommendations to serializable format
                recs_data = []
                for rec in recommendations[:5]:  # Limit to top 5
                    recs_data.append({
                        'issue_type': rec.issue_type,
                        'severity': rec.severity,
                        'description': rec.description,
                        'suggested_fix': rec.suggested_fix,
                        'quantitative_impact': rec.quantitative_impact
                    })

                response_data = {
                    'success': True,
                    'analysis_result': {
                        'max_displacement': float(np.max(np.abs(result.displacements))) if len(result.displacements) > 0 else 0.0,
                        'max_stress': float(np.max(np.abs(result.stresses))) if len(result.stresses) > 0 else 0.0,
                        'max_strain': float(np.max(np.abs(result.strains))) if len(result.strains) > 0 else 0.0,
                        'converged': result.converged,
                        'iterations': result.iterations
                    },
                    'recommendations': recs_data,
                    'material_used': material_name
                }

                # Add natural frequencies if available
                if result.natural_frequencies is not None and len(result.natural_frequencies) > 0:
                    response_data['analysis_result']['fundamental_frequency'] = float(result.natural_frequencies[0])

                return jsonify(response_data)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Analysis did not converge',
                    'iterations': result.iterations
                }), 400

        finally:
            # Clean up uploaded file
            if file_path.exists():
                file_path.unlink()

    except Exception as e:
        logger.exception("Structural analysis error")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/download/optimized/<model_id>')
def download_optimized_model(model_id):
    """Download an optimized 3D model."""
    try:
        if not FILE_ID_PATTERN.match(model_id):
            return jsonify({'error': 'Invalid model ID'}), 400

        upload_dir = Path(current_app.config.get('UPLOAD_DIR', './uploads'))
        model_path = upload_dir / f"optimized_{model_id}.stl"

        if not model_path.exists():
            return jsonify({'error': 'Model not found'}), 404

        from flask import send_file
        return send_file(
            str(model_path),
            as_attachment=True,
            download_name=f"optimized_model_{model_id[:8]}.stl",
            mimetype='application/sla'
        )

    except Exception as e:
        logger.exception("Download error")
        return jsonify({'error': 'Download failed'}), 500

@api_bp.route('/download/generated/<model_id>')
def download_generated_model(model_id):
    """Download a generated 3D model."""
    try:
        if not FILE_ID_PATTERN.match(model_id):
            return jsonify({'error': 'Invalid model ID'}), 400

        upload_dir = Path(current_app.config.get('UPLOAD_DIR', './uploads'))
        model_path = upload_dir / f"ai_generated_{model_id}.stl"

        if not model_path.exists():
            return jsonify({'error': 'Model not found'}), 404

        from flask import send_file
        return send_file(
            str(model_path),
            as_attachment=True,
            download_name=f"ai_generated_model_{model_id[:8]}.stl",
            mimetype='application/sla'
        )

    except Exception as e:
        logger.exception("Download error")
        return jsonify({'error': 'Download failed'}), 500