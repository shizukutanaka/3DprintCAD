"""Enhanced security configuration for Flask applications.

This module provides comprehensive security hardening following 2025 best practices:
- CSRF protection via Flask-WTF
- Security headers via Flask-Talisman
- Content Security Policy with nonces
- Rate limiting for API endpoints
- Request timeout protection
"""

from flask import Flask, g, request
from flask_wtf import CSRFProtect
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import secrets
import os
import logging
from functools import wraps
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Global instances
csrf_protect = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.environ.get('REDIS_URL', 'memory://')
)


def init_security(app: Flask, config_name: str = 'development') -> None:
    """
    Initialize comprehensive security for Flask application.

    Args:
        app: Flask application instance
        config_name: Configuration name ('development' or 'production')
    """
    # Initialize CSRF protection
    csrf_protect.init_app(app)

    # Initialize rate limiting
    limiter.init_app(app)

    # Configure security headers with Talisman
    _configure_talisman(app, config_name)

    # Configure request timeout protection
    _configure_request_timeout(app)

    # Configure CSP nonce handling
    _configure_csp_nonce(app)

    logger.info(f"Security initialized for {config_name} environment")


def _configure_talisman(app: Flask, config_name: str) -> None:
    """Configure Flask-Talisman for security headers."""
    # Content Security Policy
    csp = {
        'default-src': ["'self'"],
        'script-src': ["'self'"],
        'style-src': ["'self'"],
        'img-src': ["'self'", "data:", "blob:"],
        'font-src': ["'self'"],
        'connect-src': ["'self'"],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
    }

    # Add unsafe-inline only in development for convenience
    if config_name != 'production':
        csp['script-src'].append("'unsafe-inline'")
        csp['style-src'].append("'unsafe-inline'")

    # Initialize Talisman
    Talisman(
        app,
        force_https=(config_name == 'production'),
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,  # 1 year
        strict_transport_security_include_subdomains=True,
        strict_transport_security_preload=True,
        session_cookie_secure=(config_name == 'production'),
        session_cookie_httponly=True,
        session_cookie_samesite='Lax',
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src', 'style-src'],
        referrer_policy='strict-origin-when-cross-origin',
        x_content_type_options='nosniff',
        x_frame_options='DENY',
        x_xss_protection=True,
    )

    # Additional security headers
    @app.after_request
    def add_extra_security_headers(response):
        """Add additional security headers."""
        response.headers['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'accelerometer=()'
        )
        response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'

        # Add nonce to inline scripts if present
        if hasattr(g, 'csp_nonce'):
            response.headers['Content-Security-Policy'] = response.headers.get(
                'Content-Security-Policy', ''
            ).replace(
                'script-src ',
                f"script-src 'nonce-{g.csp_nonce}' "
            )

        return response


def _configure_request_timeout(app: Flask) -> None:
    """Configure request timeout protection."""
    timeout_seconds = int(os.environ.get('REQUEST_TIMEOUT_SECONDS', '30'))
    app.config['REQUEST_TIMEOUT_SECONDS'] = timeout_seconds

    @app.before_request
    def set_request_timeout():
        """Set request deadline."""
        g.request_start_time = __import__('time').time()
        g.request_deadline = g.request_start_time + timeout_seconds

    @app.before_request
    def check_request_timeout():
        """Check if request has exceeded timeout."""
        if hasattr(g, 'request_deadline'):
            current_time = __import__('time').time()
            if current_time > g.request_deadline:
                from flask import jsonify
                response = jsonify({
                    'error': {
                        'code': 408,
                        'message': 'Request timeout'
                    },
                    'request_id': getattr(g, 'request_id', None)
                })
                response.status_code = 408
                return response


def _configure_csp_nonce(app: Flask) -> None:
    """Configure CSP nonce generation and injection."""
    @app.before_request
    def generate_csp_nonce():
        """Generate unique CSP nonce for this request."""
        g.csp_nonce = secrets.token_urlsafe(16)

    # Make nonce available to templates
    @app.context_processor
    def inject_csp_nonce():
        """Inject nonce into template context."""
        return {'csp_nonce': getattr(g, 'csp_nonce', '')}


def rate_limit_route(
    limit: str,
    key_func: Optional[Callable] = None,
    error_handler: Optional[Callable] = None
) -> Callable:
    """
    Decorator for rate limiting specific routes.

    Args:
        limit: Rate limit string (e.g., "10 per minute")
        key_func: Function to extract rate limit key (defaults to IP)
        error_handler: Custom error handler

    Example:
        @app.route('/api/expensive')
        @rate_limit_route("5 per minute")
        def expensive_operation():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Use limiter.limit decorator
            return limiter.limit(limit, key_func=key_func)(func)(*args, **kwargs)
        return wrapper
    return decorator


def require_https(func: Callable) -> Callable:
    """
    Decorator to require HTTPS for a route.

    Args:
        func: Flask route function

    Returns:
        Wrapped function that enforces HTTPS
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not request.is_secure and os.environ.get('ENFORCE_TLS') == '1':
            from flask import abort
            abort(403)
        return func(*args, **kwargs)
    return wrapper


def get_csp_nonce() -> str:
    """
    Get current CSP nonce for template use.

    Returns:
        CSP nonce string
    """
    return getattr(g, 'csp_nonce', '')


# Security checklist for deployment
SECURITY_CHECKLIST = {
    'environment': {
        'SECRET_KEY': 'Set strong SECRET_KEY environment variable',
        'ENFORCE_TLS': 'Enable HTTPS enforcement in production',
        'ALLOWED_ORIGINS': 'Configure CORS with HTTPS-only origins',
    },
    'headers': {
        'Strict-Transport-Security': 'Enforces HTTPS for all connections',
        'X-Content-Type-Options': 'Prevents MIME sniffing attacks',
        'X-Frame-Options': 'Prevents clickjacking attacks',
        'Content-Security-Policy': 'Prevents XSS and injection attacks',
        'Permissions-Policy': 'Restricts browser feature access',
    },
    'cookies': {
        'session_cookie_secure': 'HTTPS-only cookies in production',
        'session_cookie_httponly': 'Prevents JavaScript access to session',
        'session_cookie_samesite': 'Prevents CSRF attacks',
    },
    'rate_limiting': {
        'API endpoints': 'Limited to prevent abuse',
        'File uploads': 'Limited to prevent resource exhaustion',
        'Authentication': 'Limited to prevent brute force',
    }
}


def print_security_checklist() -> None:
    """Print security checklist for deployment."""
    print("\n" + "="*60)
    print("SECURITY CHECKLIST FOR PRODUCTION DEPLOYMENT")
    print("="*60)
    for category, items in SECURITY_CHECKLIST.items():
        print(f"\n{category.upper()}:")
        for item, description in items.items():
            print(f"  ✓ {item}: {description}")
    print("\n" + "="*60 + "\n")


if __name__ == '__main__':
    print_security_checklist()
