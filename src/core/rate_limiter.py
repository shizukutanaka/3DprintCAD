"""Rate limiting and DDoS protection for production deployment."""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from functools import wraps
from flask import request, jsonify
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RateLimitRule:
    """Rate limit rule configuration."""
    requests: int  # Number of requests allowed
    window: int    # Time window in seconds
    burst: int = 0  # Burst allowance (extra requests allowed in short bursts)


@dataclass
class ClientRecord:
    """Track client request history."""
    request_times: list[float] = field(default_factory=list)
    blocked_until: Optional[float] = None
    total_requests: int = 0
    total_blocked: int = 0


class RateLimiter:
    """
    Production-grade rate limiter with DDoS protection.

    Features:
    - Per-IP rate limiting
    - Per-endpoint rate limiting
    - Burst protection
    - Adaptive blocking
    - Request pattern analysis
    """

    def __init__(self):
        self.clients: Dict[str, ClientRecord] = defaultdict(ClientRecord)
        self.endpoint_rules: Dict[str, RateLimitRule] = {
            # API endpoints
            '/api/upload': RateLimitRule(requests=10, window=60, burst=2),
            '/api/validate': RateLimitRule(requests=20, window=60, burst=5),
            '/api/repair': RateLimitRule(requests=10, window=60, burst=2),
            '/api/slice': RateLimitRule(requests=10, window=60, burst=2),
            '/api/batch': RateLimitRule(requests=5, window=60, burst=1),

            # Material/Profile management
            '/api/materials': RateLimitRule(requests=30, window=60),
            '/api/profiles': RateLimitRule(requests=30, window=60),

            # General API
            '/api/*': RateLimitRule(requests=100, window=60, burst=20),
        }

        # Global rate limit (fallback)
        self.global_rule = RateLimitRule(requests=200, window=60, burst=50)

        # Cleanup old records periodically
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes

    def get_client_id(self) -> str:
        """Get unique client identifier from request."""
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Take first IP in chain (original client)
            client_ip = forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.remote_addr or 'unknown'

        # Include user agent for additional fingerprinting
        user_agent = request.headers.get('User-Agent', 'unknown')
        return f"{client_ip}:{hash(user_agent) % 10000}"

    def get_rule_for_endpoint(self, endpoint: str) -> RateLimitRule:
        """Get rate limit rule for specific endpoint."""
        # Exact match
        if endpoint in self.endpoint_rules:
            return self.endpoint_rules[endpoint]

        # Pattern match (e.g., /api/validate/xyz matches /api/validate)
        for pattern, rule in self.endpoint_rules.items():
            if pattern.endswith('*') and endpoint.startswith(pattern[:-1]):
                return rule
            if '/' in pattern and endpoint.startswith(pattern.split('/')[0]):
                return rule

        return self.global_rule

    def check_rate_limit(self, client_id: str, endpoint: str) -> Tuple[bool, Dict]:
        """
        Check if request is allowed under rate limit.

        Returns:
            Tuple of (is_allowed, metadata)
        """
        current_time = time.time()
        client = self.clients[client_id]

        # Check if client is currently blocked
        if client.blocked_until and current_time < client.blocked_until:
            remaining = int(client.blocked_until - current_time)
            return False, {
                'blocked': True,
                'retry_after': remaining,
                'reason': 'Rate limit exceeded - temporary block'
            }

        # Get rate limit rule
        rule = self.get_rule_for_endpoint(endpoint)

        # Clean old request times outside the window
        cutoff_time = current_time - rule.window
        client.request_times = [t for t in client.request_times if t > cutoff_time]

        # Count requests in current window
        requests_in_window = len(client.request_times)

        # Calculate limit with burst
        effective_limit = rule.requests + rule.burst

        # Check if limit exceeded
        if requests_in_window >= effective_limit:
            # Adaptive blocking: longer blocks for repeat offenders
            block_duration = min(60 * (client.total_blocked + 1), 3600)  # Max 1 hour
            client.blocked_until = current_time + block_duration
            client.total_blocked += 1

            logger.warning(
                f"Rate limit exceeded for {client_id} on {endpoint}: "
                f"{requests_in_window}/{effective_limit} requests. "
                f"Blocked for {block_duration}s"
            )

            return False, {
                'blocked': True,
                'retry_after': block_duration,
                'reason': 'Rate limit exceeded',
                'limit': rule.requests,
                'window': rule.window
            }

        # Allow request
        client.request_times.append(current_time)
        client.total_requests += 1

        # Periodic cleanup
        if current_time - self.last_cleanup > self.cleanup_interval:
            self.cleanup_old_records()
            self.last_cleanup = current_time

        return True, {
            'allowed': True,
            'remaining': effective_limit - requests_in_window - 1,
            'limit': rule.requests,
            'window': rule.window,
            'reset': int(current_time + rule.window)
        }

    def cleanup_old_records(self):
        """Remove old client records to prevent memory bloat."""
        current_time = time.time()
        cutoff_time = current_time - 3600  # 1 hour

        clients_to_remove = [
            client_id for client_id, record in self.clients.items()
            if (not record.request_times or max(record.request_times) < cutoff_time)
            and (not record.blocked_until or record.blocked_until < current_time)
        ]

        for client_id in clients_to_remove:
            del self.clients[client_id]

        if clients_to_remove:
            logger.info(f"Cleaned up {len(clients_to_remove)} old client records")

    def detect_suspicious_pattern(self, client_id: str) -> bool:
        """
        Detect suspicious request patterns (potential DDoS).

        Returns:
            True if suspicious pattern detected
        """
        client = self.clients[client_id]

        # Pattern 1: Too many requests in very short time (< 1 second)
        if len(client.request_times) > 2:
            recent_times = sorted(client.request_times[-10:])
            if len(recent_times) >= 5:
                time_span = recent_times[-1] - recent_times[0]
                if time_span < 1.0:  # 5+ requests in < 1 second
                    logger.warning(f"Suspicious rapid requests from {client_id}")
                    return True

        # Pattern 2: High block rate
        if client.total_requests > 100 and client.total_blocked > 10:
            block_rate = client.total_blocked / client.total_requests
            if block_rate > 0.5:  # > 50% blocked
                logger.warning(f"High block rate for {client_id}: {block_rate:.2%}")
                return True

        return False

    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        current_time = time.time()
        active_clients = len([
            c for c in self.clients.values()
            if c.request_times and max(c.request_times) > current_time - 300
        ])
        blocked_clients = len([
            c for c in self.clients.values()
            if c.blocked_until and c.blocked_until > current_time
        ])

        return {
            'total_clients': len(self.clients),
            'active_clients': active_clients,
            'blocked_clients': blocked_clients,
            'total_requests': sum(c.total_requests for c in self.clients.values()),
            'total_blocks': sum(c.total_blocked for c in self.clients.values())
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(endpoint_override: Optional[str] = None):
    """
    Decorator for rate limiting Flask routes.

    Args:
        endpoint_override: Optional endpoint name override
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            client_id = rate_limiter.get_client_id()
            endpoint = endpoint_override or request.endpoint or request.path

            # Check for suspicious patterns
            if rate_limiter.detect_suspicious_pattern(client_id):
                logger.error(f"Blocking suspicious client: {client_id}")
                return jsonify({
                    'error': 'Suspicious activity detected',
                    'blocked': True
                }), 429

            # Check rate limit
            allowed, metadata = rate_limiter.check_rate_limit(client_id, endpoint)

            if not allowed:
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': metadata.get('retry_after'),
                    'limit': metadata.get('limit'),
                    'window': metadata.get('window')
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(metadata.get('retry_after', 60))
                response.headers['X-RateLimit-Limit'] = str(metadata.get('limit', 0))
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(metadata.get('reset', 0))
                return response

            # Add rate limit headers
            response = f(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(metadata.get('limit', 0))
                response.headers['X-RateLimit-Remaining'] = str(metadata.get('remaining', 0))
                response.headers['X-RateLimit-Reset'] = str(metadata.get('reset', 0))

            return response

        return wrapped
    return decorator


def ip_whitelist(*allowed_ips):
    """
    Decorator to whitelist specific IPs (for admin endpoints).

    Args:
        allowed_ips: List of allowed IP addresses
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if client_ip:
                client_ip = client_ip.split(',')[0].strip()

            if client_ip not in allowed_ips:
                logger.warning(f"Unauthorized IP access attempt: {client_ip}")
                return jsonify({'error': 'Access denied'}), 403

            return f(*args, **kwargs)
        return wrapped
    return decorator


def require_https():
    """Decorator to enforce HTTPS on production endpoints."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not request.is_secure and not request.headers.get('X-Forwarded-Proto') == 'https':
                logger.warning(f"Non-HTTPS request to {request.path}")
                return jsonify({'error': 'HTTPS required'}), 403
            return f(*args, **kwargs)
        return wrapped
    return decorator
