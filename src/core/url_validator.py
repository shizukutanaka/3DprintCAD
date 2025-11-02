"""URL validation and cleanup utility for production security."""
from __future__ import annotations

import re
from typing import Set, Dict, Any, Optional
from urllib.parse import urlparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Allowed URL patterns for the application
ALLOWED_URL_PATTERNS = {
    # API endpoints
    r'^/api/health$',
    r'^/api/upload$',
    r'^/api/validate/[a-f0-9\-]{8,}$',
    r'^/api/repair/[a-f0-9\-]{8,}$',
    r'^/api/slice/[a-f0-9\-]{8,}$',
    r'^/api/batch$',
    r'^/api/formats$',
    r'^/api/materials$',
    r'^/api/materials/[a-f0-9\-]+$',
    r'^/api/profiles$',
    r'^/api/profiles/[a-f0-9\-]+$',
    r'^/api/printers$',
    r'^/api/translations/[a-z]{2}$',

    # Static pages
    r'^/$',
    r'^/viewer$',
    r'^/analysis$',
    r'^/dashboard$',
    r'^/slicer$',
    r'^/materials$',
    r'^/workflow$',

    # File endpoints
    r'^/uploads/[a-f0-9\-_]+\.(stl|obj|ply|3mf|amf)$',
    r'^/results/[a-f0-9\-_]+\.(stl|obj|ply|3mf|amf|gcode)$',

    # Static assets
    r'^/static/.*$',
}

# External URLs that must be validated (CDN, APIs, etc.)
EXTERNAL_URL_WHITELIST: Set[str] = set()

# Blocked URL patterns (known vulnerabilities, deprecated endpoints)
BLOCKED_URL_PATTERNS = {
    r'.*\.\./.*',  # Directory traversal
    r'.*%00.*',    # Null byte injection
    r'.*<script.*',  # XSS attempt
    r'.*javascript:.*',  # XSS attempt
    r'.*data:.*',  # Data URI XSS
}


class URLValidator:
    """Validates and sanitizes URLs for security."""

    def __init__(self, custom_patterns: Optional[Set[str]] = None):
        self.allowed_patterns = ALLOWED_URL_PATTERNS.copy()
        if custom_patterns:
            self.allowed_patterns.update(custom_patterns)

        self.compiled_allowed = [re.compile(pattern, re.IGNORECASE)
                                for pattern in self.allowed_patterns]
        self.compiled_blocked = [re.compile(pattern, re.IGNORECASE)
                                for pattern in BLOCKED_URL_PATTERNS]

    def validate_url(self, url: str) -> Dict[str, Any]:
        """
        Validate URL against security rules.

        Args:
            url: URL string to validate

        Returns:
            Dict with validation results
        """
        result = {
            "valid": False,
            "url": url,
            "errors": [],
            "warnings": []
        }

        # Check for blocked patterns first
        for pattern in self.compiled_blocked:
            if pattern.match(url):
                result["errors"].append(f"URL contains blocked pattern: {url}")
                return result

        # Validate against allowed patterns
        is_allowed = any(pattern.match(url) for pattern in self.compiled_allowed)

        if not is_allowed:
            result["errors"].append(f"URL not in allowed patterns: {url}")
            return result

        # Additional security checks
        parsed = urlparse(url)

        # Check for suspicious query parameters
        if parsed.query and any(param in parsed.query.lower()
                               for param in ['script', 'eval', 'exec', 'import']):
            result["warnings"].append("Suspicious query parameters detected")

        # Check for excessive length
        if len(url) > 2048:
            result["errors"].append("URL exceeds maximum length")
            return result

        result["valid"] = True
        return result

    def validate_external_url(self, url: str) -> Dict[str, Any]:
        """
        Validate external URLs (CDN, APIs, etc.).

        Args:
            url: External URL to validate

        Returns:
            Dict with validation results
        """
        result = {
            "valid": False,
            "url": url,
            "errors": [],
            "warnings": []
        }

        parsed = urlparse(url)

        # Must be HTTPS for external URLs
        if parsed.scheme != 'https':
            result["errors"].append("External URLs must use HTTPS")
            return result

        # Check against whitelist
        if url not in EXTERNAL_URL_WHITELIST:
            result["errors"].append(f"External URL not in whitelist: {url}")
            result["warnings"].append("Add URL to EXTERNAL_URL_WHITELIST if trusted")
            return result

        result["valid"] = True
        return result

    def sanitize_url(self, url: str) -> str:
        """
        Sanitize URL by removing dangerous characters.

        Args:
            url: URL to sanitize

        Returns:
            Sanitized URL string
        """
        # Remove null bytes
        url = url.replace('\x00', '')

        # Remove control characters
        url = ''.join(char for char in url if ord(char) >= 32 or char in ['\t', '\n'])

        # Remove leading/trailing whitespace
        url = url.strip()

        return url

    def audit_codebase_urls(self, base_path: Path) -> Dict[str, Any]:
        """
        Audit all URLs in codebase files.

        Args:
            base_path: Root directory to scan

        Returns:
            Audit report with all URLs found
        """
        url_pattern = re.compile(
            r'https?://[^\s<>"{}|\\^`\[\]]+|'  # HTTP(S) URLs
            r'/api/[^\s<>"{}|\\^`\[\]]+|'      # API endpoints
            r'/[a-z]+/[^\s<>"{}|\\^`\[\]]+'    # Relative URLs
        )

        report = {
            "total_files_scanned": 0,
            "urls_found": [],
            "invalid_urls": [],
            "external_urls": [],
            "issues": []
        }

        # Scan Python files
        for py_file in base_path.rglob("*.py"):
            if '.venv' in str(py_file) or 'node_modules' in str(py_file):
                continue

            report["total_files_scanned"] += 1

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    urls = url_pattern.findall(content)

                    for url in urls:
                        if url.startswith('http'):
                            report["external_urls"].append({
                                "url": url,
                                "file": str(py_file),
                                "valid": self.validate_external_url(url)["valid"]
                            })
                        else:
                            validation = self.validate_url(url)
                            report["urls_found"].append({
                                "url": url,
                                "file": str(py_file),
                                "valid": validation["valid"]
                            })
                            if not validation["valid"]:
                                report["invalid_urls"].append({
                                    "url": url,
                                    "file": str(py_file),
                                    "errors": validation["errors"]
                                })
            except Exception as e:
                logger.error(f"Error scanning {py_file}: {e}")

        # Scan HTML/JS files
        for template_file in base_path.rglob("*.html"):
            report["total_files_scanned"] += 1

            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    urls = url_pattern.findall(content)

                    for url in urls:
                        if url.startswith('http'):
                            report["external_urls"].append({
                                "url": url,
                                "file": str(template_file),
                                "valid": self.validate_external_url(url)["valid"]
                            })
            except Exception as e:
                logger.error(f"Error scanning {template_file}: {e}")

        return report

    def remove_invalid_urls(self, file_path: Path, dry_run: bool = True) -> Dict[str, Any]:
        """
        Remove or comment out invalid URLs in a file.

        Args:
            file_path: File to process
            dry_run: If True, only report changes without modifying

        Returns:
            Report of changes made
        """
        result = {
            "file": str(file_path),
            "changes": [],
            "dry_run": dry_run
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
            modified_lines = []

            for i, line in enumerate(lines):
                urls = url_pattern.findall(line)
                modified_line = line

                for url in urls:
                    validation = self.validate_external_url(url)
                    if not validation["valid"]:
                        # Comment out the line
                        if not line.strip().startswith('#'):
                            modified_line = f"# REMOVED_INVALID_URL: {line}"
                            result["changes"].append({
                                "line": i + 1,
                                "url": url,
                                "reason": validation["errors"],
                                "original": line.strip(),
                                "modified": modified_line.strip()
                            })

                modified_lines.append(modified_line)

            if not dry_run and result["changes"]:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(modified_lines)
                logger.info(f"Modified {file_path}: {len(result['changes'])} changes")

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            result["error"] = str(e)

        return result


def create_url_audit_report(base_path: Path, output_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    Create comprehensive URL audit report.

    Args:
        base_path: Root directory to audit
        output_file: Optional file path to save report

    Returns:
        Audit report dictionary
    """
    validator = URLValidator()
    report = validator.audit_codebase_urls(base_path)

    # Add summary
    report["summary"] = {
        "total_urls": len(report["urls_found"]) + len(report["external_urls"]),
        "valid_urls": len([u for u in report["urls_found"] if u["valid"]]),
        "invalid_urls": len(report["invalid_urls"]),
        "external_urls": len(report["external_urls"]),
        "external_invalid": len([u for u in report["external_urls"] if not u["valid"]])
    }

    if output_file:
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Audit report saved to {output_file}")

    return report


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1:
        base = Path(sys.argv[1])
        report = create_url_audit_report(base, base / "url_audit_report.json")
        print(f"Audit complete: {report['summary']}")
    else:
        print("Usage: python url_validator.py <base_directory>")
