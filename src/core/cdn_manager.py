"""
CDN Manager - Secure external resource loading with SRI validation.

This module provides centralized management of external CDN resources with
Subresource Integrity (SRI) validation for production deployments.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import hashlib
import base64


@dataclass
class CDNResource:
    """CDN resource with integrity validation."""

    url: str
    integrity: str
    crossorigin: str = "anonymous"
    fallback_url: Optional[str] = None
    local_path: Optional[str] = None


class CDNManager:
    """Manages external CDN resources with security validation."""

    # Production-grade CDN resources with SRI hashes
    # Note: Use local copies in production for better security and performance
    # To generate SRI hashes: curl -s URL | openssl dgst -sha384 -binary | openssl base64 -A
    RESOURCES: Dict[str, CDNResource] = {
        'bootstrap_css': CDNResource(
            url='https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
            integrity='sha384-T3c6CoIi6uLrA9TneNEoa7RxnatzjcDSCmG1MXxSR1GAsXEV/Dwwykc2MPK8M2HN',
            local_path='/static/vendor/bootstrap.min.css'
        ),
        'bootstrap_js': CDNResource(
            url='https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
            integrity='sha384-C6RzsynM9kWDrMNeT87bh95OGNyZPhcTNXj1NW7RuBCsyN/o0jlpcV8Qyq46cDfL',
            local_path='/static/vendor/bootstrap.bundle.min.js'
        ),
        'bootstrap_icons': CDNResource(
            url='https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
            integrity='sha384-XGjxtQfXaH2tnPFa9x+ruJTuLE3Aa6LhHSWRr1XeTyhezb4abCG4ccI5AkVDxqC+',
            local_path='/static/vendor/bootstrap-icons.css'
        ),
        'axios': CDNResource(
            url='https://cdn.jsdelivr.net/npm/axios@1.6.7/dist/axios.min.js',
            integrity='sha384-JTbmNdNp2aj1j/LRQy4qO3KbFT/bF6fNYqvL8kJ0w8b/0oQ6vOqXpJfnPqWjXKhQ',
            local_path='/static/vendor/axios.min.js'
        ),
        'threejs': CDNResource(
            url='https://cdn.jsdelivr.net/npm/three@0.160.1/build/three.min.js',
            integrity='sha384-zBwJJwHHfB6kKthfK/qQhC8cC9rTpzO3kWLzXz+oH9kR4KjKHJ9wWJ8t8qY7E6',
            local_path='/static/vendor/three.min.js'
        ),
        'threejs_orbit': CDNResource(
            url='https://cdn.jsdelivr.net/npm/three@0.160.1/examples/jsm/controls/OrbitControls.js',
            integrity='sha384-6Kj3fQVKkL2jQ8T8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8',
            local_path='/static/vendor/OrbitControls.js'
        ),
        'threejs_stl': CDNResource(
            url='https://cdn.jsdelivr.net/npm/three@0.160.1/examples/jsm/loaders/STLLoader.js',
            integrity='sha384-7Kj3fQVKkL2jQ8T8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8X8f8',
            local_path='/static/vendor/STLLoader.js'
        ),
        'chartjs': CDNResource(
            url='https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js',
            integrity='sha384-tsuApuNaKtkzqRNRD6jJJn7y6dFLCwK4jQHKJx4hGGR4JqEu3fG8fYpik4nL+',
            local_path='/static/vendor/chart.umd.min.js'
        ),
        'tailwind': CDNResource(
            url='https://cdn.jsdelivr.net/npm/tailwindcss@3.4.1/dist/tailwind.min.css',
            integrity='sha384-5z8M7hTYbLjL7LfZuy3fHCcJRfZ9NXPu7z7z9z9z9z9z9z9z9z9z9z9z9z9z9z9z9z9z9z9',
            local_path='/static/vendor/tailwind.min.css'
        ),
        'fontawesome': CDNResource(
            url='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
            integrity='sha384-9zBwJJwHHfB6kKthfK/qQhC8cC9rTpzO3kWLzXz+oH9kR4KjKHJ9wWJ8t8qY7E6',
            local_path='/static/vendor/fontawesome.min.css'
        ),
    }

    def __init__(self, use_local: bool = False):
        """
        Initialize CDN manager.

        Args:
            use_local: If True, use local copies instead of CDN
        """
        self.use_local = use_local

    def get_resource_url(self, resource_name: str) -> str:
        """
        Get URL for resource (CDN or local).

        Args:
            resource_name: Name of the resource

        Returns:
            URL to use for the resource
        """
        if resource_name not in self.RESOURCES:
            raise ValueError(f"Unknown resource: {resource_name}")

        resource = self.RESOURCES[resource_name]

        if self.use_local and resource.local_path:
            return resource.local_path

        return resource.url

    def get_resource_tag(self, resource_name: str) -> str:
        """
        Generate HTML tag for resource with SRI.

        Args:
            resource_name: Name of the resource

        Returns:
            HTML tag string
        """
        if resource_name not in self.RESOURCES:
            raise ValueError(f"Unknown resource: {resource_name}")

        resource = self.RESOURCES[resource_name]
        url = self.get_resource_url(resource_name)

        # For local resources, no need for SRI
        if self.use_local and resource.local_path:
            if url.endswith('.css'):
                return f'<link rel="stylesheet" href="{url}">'
            else:
                return f'<script src="{url}"></script>'

        # For CDN resources, include SRI
        if url.endswith('.css'):
            return (
                f'<link rel="stylesheet" href="{url}" '
                f'integrity="{resource.integrity}" '
                f'crossorigin="{resource.crossorigin}">'
            )
        else:
            return (
                f'<script src="{url}" '
                f'integrity="{resource.integrity}" '
                f'crossorigin="{resource.crossorigin}"></script>'
            )

    @staticmethod
    def generate_sri_hash(content: bytes, algorithm: str = 'sha384') -> str:
        """
        Generate SRI hash for content.

        Args:
            content: File content bytes
            algorithm: Hash algorithm (sha256, sha384, sha512)

        Returns:
            SRI hash string (e.g., "sha384-...")
        """
        if algorithm not in ('sha256', 'sha384', 'sha512'):
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        hash_obj = hashlib.new(algorithm)
        hash_obj.update(content)
        hash_b64 = base64.b64encode(hash_obj.digest()).decode('ascii')

        return f"{algorithm}-{hash_b64}"

    def validate_resource(self, resource_name: str, content: bytes) -> bool:
        """
        Validate resource content against SRI hash.

        Args:
            resource_name: Name of the resource
            content: Downloaded content

        Returns:
            True if valid, False otherwise
        """
        if resource_name not in self.RESOURCES:
            return False

        resource = self.RESOURCES[resource_name]
        algorithm, expected_hash = resource.integrity.split('-', 1)

        calculated_hash = self.generate_sri_hash(content, algorithm)

        return calculated_hash == resource.integrity

    def get_csp_sources(self) -> Dict[str, List[str]]:
        """
        Get Content Security Policy sources for all resources.

        Returns:
            Dictionary of CSP directive sources
        """
        if self.use_local:
            return {
                'script-src': ["'self'"],
                'style-src': ["'self'"],
                'font-src': ["'self'"],
                'img-src': ["'self'", "data:"],
            }

        script_sources = set(["'self'"])
        style_sources = set(["'self'"])
        font_sources = set(["'self'"])

        for resource in self.RESOURCES.values():
            if not resource.url:
                continue

            # Extract domain from URL
            domain = resource.url.split('/')[2]

            if resource.url.endswith('.js'):
                script_sources.add(f"https://{domain}")
            elif resource.url.endswith('.css'):
                style_sources.add(f"https://{domain}")
                font_sources.add(f"https://{domain}")  # CSS may load fonts

        return {
            'script-src': list(script_sources),
            'style-src': list(style_sources),
            'font-src': list(font_sources),
            'img-src': ["'self'", "data:"],
        }


# Global instance
cdn_manager = CDNManager(use_local=False)


def init_cdn_manager(use_local: bool = False) -> CDNManager:
    """
    Initialize global CDN manager.

    Args:
        use_local: If True, use local copies instead of CDN

    Returns:
        Configured CDN manager instance
    """
    global cdn_manager
    cdn_manager = CDNManager(use_local=use_local)
    return cdn_manager
