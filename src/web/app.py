"""Flask application factory and configuration."""
from flask import Flask, render_template, send_from_directory, abort, request, g, jsonify
from flask_cors import CORS
from pathlib import Path
import os
import logging
import secrets
import time
import uuid
from datetime import datetime, timezone
import stripe
from ..core.security import sanitize_filename, secure_path_resolution, generate_secure_token
from .security_enhanced import init_security, limiter

logger = logging.getLogger(__name__)

def create_app(config_name='development'):
    """Create and configure Flask application."""
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')

    # Configuration - Security Enhanced
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        if config_name == 'production':
            raise ValueError("SECRET_KEY environment variable is required for production")
        secret_key = generate_secure_token(64)  # Generate secure key for dev
        logger.warning("Using generated SECRET_KEY for development. Set SECRET_KEY env var for production.")

    app.config['SECRET_KEY'] = secret_key
    max_upload_mb_env = os.environ.get('MAX_UPLOAD_MB', '100')
    try:
        max_upload_mb = max(1, int(max_upload_mb_env))
    except ValueError:
        logger.warning("Invalid MAX_UPLOAD_MB value '%s'. Falling back to 100.", max_upload_mb_env)
        max_upload_mb = 100

    app.config['MAX_MESH_SIZE_MB'] = max_upload_mb
    app.config['MAX_CONTENT_LENGTH'] = max_upload_mb * 1024 * 1024

    # Request timeout configuration
    request_timeout_env = os.environ.get('REQUEST_TIMEOUT_SECONDS', '30')
    try:
        request_timeout = max(1, int(request_timeout_env))
    except ValueError:
        logger.warning("Invalid REQUEST_TIMEOUT_SECONDS value '%s'. Falling back to 30.", request_timeout_env)
        request_timeout = 30

    app.config['REQUEST_TIMEOUT_SECONDS'] = request_timeout

    batch_limit_env = os.environ.get('MAX_BATCH_FILES', '20')
    try:
        max_batch_files = max(1, int(batch_limit_env))
    except ValueError:
        logger.warning("Invalid MAX_BATCH_FILES value '%s'. Falling back to 20.", batch_limit_env)
        max_batch_files = 20

    app.config['MAX_BATCH_FILES'] = max_batch_files

    # Stripe configuration
    stripe_secret_key = os.environ.get('STRIPE_SECRET_KEY')
    stripe_price_monthly = os.environ.get('STRIPE_PRICE_ID')
    stripe_price_annual = os.environ.get('STRIPE_PRICE_ID_ANNUAL')

    if stripe_secret_key and stripe_price_monthly:
        stripe.api_key = stripe_secret_key
        app.config['STRIPE_ENABLED'] = True
        app.config['STRIPE_SECRET_KEY'] = stripe_secret_key
        app.config['STRIPE_WEBHOOK_SECRET'] = os.environ.get('STRIPE_WEBHOOK_SECRET')
        app.config['STRIPE_SUCCESS_URL'] = os.environ.get('STRIPE_SUCCESS_URL')
        app.config['STRIPE_CANCEL_URL'] = os.environ.get('STRIPE_CANCEL_URL')
        app.config['STRIPE_PLANS'] = {
            "professional_monthly": {
                "price_id": stripe_price_monthly,
                "mode": "subscription",
                "billing_interval": "monthly",
                "label_en": "Professional Subscription (Monthly)",
                "label_ja": "プロフェッショナルサブスクリプション（月額）",
                "features_en": [
                    "Unlimited mesh validation workflows",
                    "Automated repair and slicing queue",
                    "Collaboration API unlock"
                ],
                "features_ja": [
                    "無制限のメッシュ検証ワークフロー",
                    "自動修復とスライス処理キュー",
                    "コラボレーションAPIの利用"
                ]
            }
        }

        monthly_amount = None
        monthly_currency = None
        monthly_product_id = None
        try:
            price_obj = stripe.Price.retrieve(stripe_price_monthly)
            monthly_amount = price_obj.get('unit_amount')
            monthly_currency = price_obj.get('currency')
            monthly_product_id = price_obj.get('product')
        except stripe.error.StripeError as exc:
            logger.warning("Failed to retrieve Stripe price %s: %s", stripe_price_monthly, exc)

        if monthly_amount and monthly_currency:
            app.config['STRIPE_PLANS']["professional_monthly"].update({
                "amount": monthly_amount,
                "currency": monthly_currency,
                "product_id": monthly_product_id,
            })

            buyout_amount = monthly_amount * 3
            app.config['STRIPE_PLANS']["professional_buyout"] = {
                "mode": "payment",
                "billing_interval": None,
                "label_en": "Professional Lifetime License (3-Month Equivalent)",
                "label_ja": "プロフェッショナル買い切りライセンス（3ヶ月相当）",
                "features_en": [
                    "Perpetual access to all professional tools",
                    "Includes three-month support equivalency",
                    "No recurring billing"
                ],
                "features_ja": [
                    "プロフェッショナル機能へ恒久的にアクセス",
                    "3ヶ月相当のサポートを含む",
                    "継続課金なし"
                ],
                "custom_amount": buyout_amount,
                "currency": monthly_currency,
                "buyout_months": 3,
                "source_price_id": stripe_price_monthly,
                "product_id": monthly_product_id,
            }

        if stripe_price_annual:
            app.config['STRIPE_PLANS']["professional_annual"] = {
                "price_id": stripe_price_annual,
                "mode": "subscription",
                "billing_interval": "annual",
                "label_en": "Professional Subscription (Annual)",
                "label_ja": "プロフェッショナルサブスクリプション（年額）",
                "features_en": [
                    "All monthly benefits",
                    "Annual billing with cost savings",
                    "Priority roadmap access"
                ],
                "features_ja": [
                    "月額プランのすべての特典",
                    "年額請求によるコスト削減",
                    "優先的なロードマップアクセス"
                ]
            }
    else:
        app.config['STRIPE_ENABLED'] = False
        if config_name == 'production':
            logger.warning("Stripe integration disabled: STRIPE_SECRET_KEY and STRIPE_PRICE_ID must be set.")
        else:
            logger.info("Stripe integration disabled for development (missing STRIPE_SECRET_KEY or STRIPE_PRICE_ID).")

    default_mime_types = {
        "application/octet-stream",
        "application/sla",
        "application/vnd.ms-pki.stl",
        "model/stl",
        "model/obj",
        "model/gltf-binary",
        "model/3mf",
        "model/amf",
        "application/vnd.ms-pki.3mf",
    }
    mime_env = os.environ.get('ALLOWED_UPLOAD_MIMETYPES')
    if mime_env:
        allowed_mimetypes = {
            entry.strip()
            for entry in mime_env.split(',')
            if entry.strip()
        }
    else:
        allowed_mimetypes = default_mime_types

    app.config['ALLOWED_UPLOAD_MIMETYPES'] = allowed_mimetypes

    upload_root = Path(os.environ.get('UPLOAD_DIR', 'uploads')).expanduser().resolve()
    results_root = Path(os.environ.get('RESULTS_DIR', 'results')).expanduser().resolve()

    def _prepare_directory(directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        if directory.is_symlink():
            raise ValueError(f"Storage directory must not be a symbolic link: {directory}")
        try:
            if os.name != 'nt':
                directory.chmod(0o700)
        except OSError as exc:
            logger.debug("Could not adjust permissions for %s: %s", directory, exc)
        return directory

    app.config['UPLOAD_FOLDER'] = _prepare_directory(upload_root)
    app.config['RESULTS_FOLDER'] = _prepare_directory(results_root)

    # Security headers
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300  # 5 minutes cache

    # Enable CORS for API with security restrictions
    allowed_origins_env = os.environ.get('ALLOWED_ORIGINS')
    if allowed_origins_env:
        origin_candidates = [origin.strip() for origin in allowed_origins_env.split(',') if origin.strip()]
    else:
        origin_candidates = ['http://localhost:*', 'http://127.0.0.1:*']

    if config_name == 'production':
        allowed_origins = [origin for origin in origin_candidates if origin != '*' and origin.lower().startswith('https://')]
        if not allowed_origins:
            logger.warning("No HTTPS origins configured for production CORS; CORS will be disabled.")
    else:
        allowed_origins = [origin for origin in origin_candidates if origin != '*']

    CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    enforce_tls = os.environ.get('ENFORCE_TLS', '1').lower() not in {'0', 'false', 'no'}
    app.config['ENFORCE_TLS'] = enforce_tls

    if config_name == 'production' and enforce_tls:
        @app.before_request
        def _enforce_https():
            forwarded_proto = request.headers.get('X-Forwarded-Proto')
            scheme = forwarded_proto or request.scheme
            if scheme != 'https':
                abort(403)

    # Initialize enhanced security (CSRF, rate limiting, security headers)
    init_security(app, config_name)

    # Register blueprints
    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from .payments import payments_bp
    app.register_blueprint(payments_bp, url_prefix='/api/payments')

    # Initialize CDN helpers for templates
    from .cdn_helpers import init_cdn_helpers
    init_cdn_helpers(app)

    # Initialize i18n system for web application
    from ..core.i18n_optimized import I18nManager, Language

    # Create i18n manager instance
    i18n_manager = I18nManager()

    # Set default language based on configuration
    default_lang = os.environ.get('PRINTCAD_DEFAULT_LANGUAGE', 'bilingual')
    try:
        i18n_manager.set_language(default_lang)
    except ValueError:
        i18n_manager.set_language('bilingual')

    # Make i18n manager available to all templates
    app.i18n_manager = i18n_manager

    # Language switching routes
    @app.route('/api/language/<language>')
    def set_language(language):
        try:
            i18n_manager.set_language(language)
            return jsonify({
                'success': True,
                'language': language,
                'message': f'Language set to {language}'
            })
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Invalid language specified'
            }), 400

    @app.route('/api/language')
    def get_language():
    # Add i18n template filters
    @app.template_filter('t')
    def translate_filter(key, **kwargs):
        """Translate key with current language."""
        return i18n_manager.t(key, **kwargs)

    @app.template_filter('lang')
    def current_language():
        """Get current language."""
        return i18n_manager.get_language().value

    def _json_error(status_code: int, message: str, *, details: dict | list | None = None):
        payload = {
            "error": {
                "code": status_code,
                "message": message,
            },
            "request_id": getattr(g, 'request_id', None),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if details:
            payload["error"]["details"] = details
        response = jsonify(payload)
        response.status_code = status_code
        return response

    # Main routes
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/viewer')
    def viewer():
        return render_template('viewer.html')

    @app.route('/analysis')
    def analysis():
        return render_template('analysis.html')

    @app.route('/materials')
    def materials():
        return render_template('material_manager.html')

    @app.route('/workflow')
    def workflow():
        return render_template('workflow_dashboard.html')

    @app.route('/billing/success')
    def billing_success():
        session_id = request.args.get('session_id')
        return render_template('billing_success.html', session_id=session_id)

    @app.route('/billing/cancel')
    def billing_cancel():
        session_id = request.args.get('session_id')
        return render_template('billing_cancel.html', session_id=session_id)

    def _lookup_served_file(directory_key: str, filename: str):
        try:
            # Sanitize filename and validate path
            safe_filename = sanitize_filename(filename)
            base_directory = app.config[directory_key]
            file_candidate = base_directory / safe_filename
            file_path = secure_path_resolution(
                str(file_candidate),
                allowed_base=base_directory
            )

            if not file_path.exists():
                abort(404)

            return send_from_directory(
                base_directory,
                safe_filename,
                as_attachment=False,
                cache_timeout=300
            )
        except (ValueError, OSError) as exc:
            logger.warning("Invalid file access attempt: %s - %s", filename, exc)
            abort(400)

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return _lookup_served_file('UPLOAD_FOLDER', filename)

    @app.route('/results/<filename>')
    def result_file(filename):
        return _lookup_served_file('RESULTS_FOLDER', filename)

    @app.route('/health')
    def health_check():
        """Liveness probe compatible endpoint."""
        from ..core.health_monitor import get_health_monitor

        health_monitor = get_health_monitor()
        system_health = health_monitor.run_all_checks()

        response_data = {
            "status": system_health.status.value,
            "request_id": getattr(g, 'request_id', None),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": round(system_health.uptime_seconds, 2),
            "checks": {
                check.name: {
                    "status": check.status.value,
                    "message": check.message
                }
                for check in system_health.checks
            }
        }

        # Return 503 if unhealthy
        status_code = 200 if system_health.status != "unhealthy" else 503

        return jsonify(response_data), status_code

    def _directory_health(directory: Path) -> dict:
        resolved = directory.resolve()
        exists = resolved.exists() and resolved.is_dir()
        writable = exists and os.access(resolved, os.W_OK | os.X_OK)
        return {
            "path": str(resolved),
            "exists": exists,
            "writable": writable
        }

    @app.route('/ready')
    def readiness_check():
        """Readiness probe that verifies critical resources."""
        from ..core.health_monitor import get_health_monitor
        from pathlib import Path

        health_monitor = get_health_monitor()

        # Check storage directories
        storage_check = health_monitor.check_storage([
            app.config['UPLOAD_FOLDER'],
            app.config['RESULTS_FOLDER']
        ])

        # Basic directory health
        upload_status = _directory_health(app.config['UPLOAD_FOLDER'])
        results_status = _directory_health(app.config['RESULTS_FOLDER'])
        secret_key_present = bool(os.environ.get('SECRET_KEY')) or config_name != 'production'

        checks = {
            "upload_directory": upload_status,
            "results_directory": results_status,
            "secret_key_configured": secret_key_present,
            "storage_health": {
                "status": storage_check.status.value,
                "message": storage_check.message
            }
        }

        ready = all([
            upload_status["exists"],
            upload_status["writable"],
            results_status["exists"],
            results_status["writable"],
            secret_key_present,
            storage_check.status.value != "unhealthy"
        ])

        status_code = 200 if ready else 503
        response_data = {
            "status": "ready" if ready else "degraded",
            "checks": checks,
            "request_id": getattr(g, 'request_id', None),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return jsonify(response_data), status_code

    # CSP nonce generation for inline scripts
    @app.before_request
    def generate_csp_nonce():
        """Generate CSP nonce for each request."""
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.before_request
    def initialize_request_context():
        """Attach request identifiers and timing for observability."""
        g.request_id = uuid.uuid4().hex
        g.request_start_time = time.perf_counter()
        g.request_deadline = time.perf_counter() + app.config.get('REQUEST_TIMEOUT_SECONDS', 30)

    def check_request_timeout():
        """Check if request has exceeded timeout."""
        if hasattr(g, 'request_deadline') and time.perf_counter() > g.request_deadline:
            logger.warning(
                "Request timeout exceeded",
                extra={
                    "request_id": getattr(g, 'request_id', None),
                    "path": request.path,
                    "method": request.method
                }
            )
            abort(408)  # Request Timeout

    # Make timeout checker available to routes
    app.check_request_timeout = check_request_timeout

    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), ambient-light-sensor=(), "
            "magnetometer=(), gyroscope=(), accelerometer=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # Enhanced CSP with nonce support (removes unsafe-inline for production)
        nonce = getattr(g, 'csp_nonce', '')
        if config_name == 'production':
            # Production: strict CSP with nonce, no CDN
            csp_policy = (
                "default-src 'self'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "frame-ancestors 'none'; "
                "connect-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}'; "
                f"style-src 'self' 'nonce-{nonce}'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "object-src 'none'; "
                "upgrade-insecure-requests"
            )
        else:
            # Development: allow inline for easier debugging
            csp_policy = (
                "default-src 'self'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "frame-ancestors 'none'; "
                "connect-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'"
            )

        response.headers["Content-Security-Policy"] = csp_policy
        response.headers.pop("Server", None)
        response.headers["X-Request-ID"] = getattr(g, 'request_id', '')

        if hasattr(g, 'request_start_time'):
            duration_ms = (time.perf_counter() - g.request_start_time) * 1000
            if not request.path.startswith('/static'):
                logger.info(
                    "Request completed",
                    extra={
                        "request_id": g.request_id,
                        "method": request.method,
                        "path": request.path,
                        "status": response.status_code,
                        "duration_ms": round(duration_ms, 2)
                    }
                )

        return response

    # Error handlers
    @app.errorhandler(413)
    def file_too_large(error):
        max_size = app.config.get('MAX_MESH_SIZE_MB', 100)
        return _json_error(413, "File too large", details={"max_size_mb": max_size})

    @app.errorhandler(400)
    def bad_request(error):
        return _json_error(400, "Bad request")

    @app.errorhandler(404)
    def not_found(error):
        return _json_error(404, "Resource not found")

    @app.errorhandler(408)
    def request_timeout(error):
        return _json_error(408, "Request timeout exceeded")

    @app.errorhandler(500)
    def internal_error(error):
        logger.exception(
            "Internal server error",
            extra={
                "request_id": getattr(g, 'request_id', None),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr
            }
        )
        return _json_error(500, "Internal server error")

    return app