"""Template helpers for CDN resource management."""
from flask import g
from ..core.cdn_manager import cdn_manager


def get_cdn_tag(resource_name: str) -> str:
    """
    Get HTML tag for CDN resource with CSP nonce support.

    Args:
        resource_name: Name of the CDN resource

    Returns:
        HTML tag with proper security attributes
    """
    nonce = getattr(g, 'csp_nonce', '')
    resource = cdn_manager.RESOURCES.get(resource_name)

    if not resource:
        return f"<!-- Unknown resource: {resource_name} -->"

    url = cdn_manager.get_resource_url(resource_name)

    # For local resources, no SRI needed but add nonce for CSP
    if cdn_manager.use_local and resource.local_path:
        if url.endswith('.css'):
            return f'<link rel="stylesheet" href="{url}" nonce="{nonce}">'
        else:
            return f'<script src="{url}" nonce="{nonce}"></script>'

    # For CDN resources, include SRI and nonce
    if url.endswith('.css'):
        return (
            f'<link rel="stylesheet" href="{url}" '
            f'integrity="{resource.integrity}" '
            f'crossorigin="{resource.crossorigin}" '
            f'nonce="{nonce}">'
        )
    else:
        return (
            f'<script src="{url}" '
            f'integrity="{resource.integrity}" '
            f'crossorigin="{resource.crossorigin}" '
            f'nonce="{nonce}"></script>'
        )


def init_cdn_helpers(app):
    """Initialize CDN helpers for Flask app."""
    app.jinja_env.globals['cdn_tag'] = get_cdn_tag
    app.jinja_env.globals['cdn_url'] = cdn_manager.get_resource_url
