#!/usr/bin/env python3
"""
CDN SRI Hash Generator Script

This script downloads CDN resources and generates SRI (Subresource Integrity) hashes
for enhanced security in production deployments.
"""

import argparse
import asyncio
import hashlib
import base64
import json
import os
import sys
from pathlib import Path
import aiohttp

# CDN resource defaults (used if CDNManager import fails)
DEFAULT_CDN_RESOURCES = {
    'bootstrap_css': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    'bootstrap_js': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
    'bootstrap_icons': 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
    'axios': 'https://cdn.jsdelivr.net/npm/axios@1.6.7/dist/axios.min.js',
    'threejs': 'https://cdn.jsdelivr.net/npm/three@0.160.1/build/three.min.js',
    'threejs_orbit': 'https://cdn.jsdelivr.net/npm/three@0.160.1/examples/jsm/controls/OrbitControls.js',
    'threejs_stl': 'https://cdn.jsdelivr.net/npm/three@0.160.1/examples/jsm/loaders/STLLoader.js',
    'chartjs': 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js',
    'tailwind': 'https://cdn.jsdelivr.net/npm/tailwindcss@3.4.1/dist/tailwind.min.css',
    'fontawesome': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
}


def _resolve_project_paths() -> None:
    project_root = Path(__file__).resolve().parent
    src_path = project_root / 'src'
    if src_path.exists():
        src_str = str(src_path)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)


_resolve_project_paths()


def _load_cdn_resources() -> dict:
    try:
        from core.cdn_manager import CDNManager  # type: ignore

        resources = {
            name: resource.url
            for name, resource in CDNManager.RESOURCES.items()
            if getattr(resource, 'url', None)
        }
        return resources or DEFAULT_CDN_RESOURCES
    except Exception:
        return DEFAULT_CDN_RESOURCES


# Load resource objects if available for integrity comparison
def _load_cdn_definitions():
    try:
        from core.cdn_manager import CDNManager  # type: ignore

        return CDNManager.RESOURCES
    except Exception:
        return {}


# CDN resources to process
CDN_RESOURCES = _load_cdn_resources()
CDN_RESOURCE_DEFINITIONS = _load_cdn_definitions()


def _load_positive_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        parsed = int(value)
        if parsed > 0:
            return parsed
    except ValueError:
        pass
    return default


def _load_positive_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        parsed = float(value)
        if parsed > 0:
            return parsed
    except ValueError:
        pass
    return default


def _load_non_empty_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


def _load_optional_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    return Path(value).expanduser()


DEFAULT_REQUEST_TIMEOUT = _load_positive_int('CDN_REQUEST_TIMEOUT', 30)
DEFAULT_MAX_CONCURRENCY = _load_positive_int('CDN_MAX_CONCURRENCY', 4)
DEFAULT_OUTPUT_PATH = Path(os.environ.get('CDN_HASH_OUTPUT', 'cdn_hashes.json'))
DEFAULT_ALGORITHMS = ['sha256', 'sha384', 'sha512']
ALLOWED_SRI_ALGORITHMS = {'sha256', 'sha384', 'sha512'}
DEFAULT_MAX_RETRIES = _load_positive_int('CDN_MAX_RETRIES', 3)
DEFAULT_RETRY_BASE_DELAY = _load_positive_float('CDN_RETRY_BASE_DELAY', 0.5)
DEFAULT_USER_AGENT = _load_non_empty_str('CDN_USER_AGENT', '3DprintCAD-CDNHashGenerator')
DEFAULT_RESOURCES_FILE = _load_optional_path('CDN_RESOURCES_FILE')


def _load_resources_file(file_path: Path) -> dict:
    if not file_path.exists():
        raise ValueError(f"Resources file not found: {file_path}")

    try:
        with file_path.open('r', encoding='utf-8') as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in resources file: {file_path}") from exc

    if not isinstance(data, dict):
        raise ValueError("Resources file must contain an object mapping names to URLs or objects with a 'url' field")

    resolved = {}
    for name, entry in data.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Resource names must be non-empty strings")

        if isinstance(entry, str):
            url = entry.strip()
        elif isinstance(entry, dict) and 'url' in entry:
            url = str(entry['url']).strip()
        else:
            raise ValueError(f"Resource '{name}' must be a string URL or an object containing a 'url' field")

        if not url:
            raise ValueError(f"Resource '{name}' has an empty URL")

        resolved[name] = url

    if not resolved:
        raise ValueError("Resources file did not contain any entries")

    return resolved


def _positive_int_arg(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Expected integer but received '{value}'") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"Value must be positive but received '{value}'")
    return parsed


def _positive_float_arg(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Expected number but received '{value}'") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"Value must be positive but received '{value}'")
    return parsed


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SRI hashes for CDN resources.")
    parser.add_argument(
        '--max-concurrency',
        type=_positive_int_arg,
        help="Maximum number of concurrent downloads. Overrides CDN_MAX_CONCURRENCY."
    )
    parser.add_argument(
        '--request-timeout',
        type=_positive_int_arg,
        help="Per-request timeout in seconds. Overrides CDN_REQUEST_TIMEOUT."
    )
    parser.add_argument(
        '--output',
        type=Path,
        help="Path to write generated hashes JSON. Overrides CDN_HASH_OUTPUT."
    )
    parser.add_argument(
        '--resource',
        dest='resources',
        action='append',
        help="Specify resource name(s) to process. Can be provided multiple times."
    )
    parser.add_argument(
        '--algorithm',
        dest='algorithms',
        action='append',
        help="Specify hash algorithm(s) to compute. Supported: sha256, sha384, sha512. Can be repeated."
    )
    parser.add_argument(
        '--set-url',
        dest='url_overrides',
        action='append',
        help="Override resource URL using name=URL format. Can be provided multiple times."
    )
    parser.add_argument(
        '--print-config',
        action='store_true',
        help="Print resolved configuration (resources, algorithms, output path) and exit without downloading."
    )
    parser.add_argument(
        '--max-retries',
        type=_positive_int_arg,
        help="Maximum retry attempts per resource download. Overrides CDN_MAX_RETRIES."
    )
    parser.add_argument(
        '--retry-base-delay',
        type=_positive_float_arg,
        help="Base delay in seconds for exponential backoff. Overrides CDN_RETRY_BASE_DELAY."
    )
    parser.add_argument(
        '--json-logs',
        action='store_true',
        help="Emit machine-readable JSON log lines instead of plain text."
    )
    parser.add_argument(
        '--compare-integrity',
        action='store_true',
        help="Compare generated hashes against existing CDNManager integrities."
    )
    parser.add_argument(
        '--list-resources',
        action='store_true',
        help="List known CDN resources and exit."
    )
    parser.add_argument(
        '--resources-file',
        type=Path,
        default=DEFAULT_RESOURCES_FILE,
        help="Load additional or overriding CDN resources from a JSON file. Defaults to CDN_RESOURCES_FILE."
    )
    parser.add_argument(
        '--user-agent',
        help="Override User-Agent header for CDN requests. Overrides CDN_USER_AGENT."
    )
    return parser.parse_args()


def _select_resources(requested: list | None, available: dict | None = None) -> dict:
    resources = available or CDN_RESOURCES
    if not requested:
        return resources

    missing = [name for name in requested if name not in resources]
    if missing:
        raise ValueError(f"Unknown resource(s): {', '.join(missing)}")

    return {name: resources[name] for name in requested}


def _apply_url_overrides(resources: dict, overrides: list | None) -> dict:
    if not overrides:
        return resources

    updated = dict(resources)
    for override in overrides:
        if '=' not in override:
            raise ValueError(f"Invalid override '{override}'. Expected format name=URL.")
        name, url = override.split('=', 1)
        name = name.strip()
        url = url.strip()
        if not name or not url:
            raise ValueError(f"Invalid override '{override}'. Resource name and URL must be non-empty.")
        if name not in updated:
            raise ValueError(f"Cannot override unknown resource '{name}'.")
        updated[name] = url
    return updated


def _resolve_algorithms(requested: list | None) -> list:
    if not requested:
        return DEFAULT_ALGORITHMS

    normalized = [algo.lower() for algo in requested]
    unsupported = [algo for algo in normalized if algo not in ALLOWED_SRI_ALGORITHMS]
    if unsupported:
        raise ValueError(f"Unsupported algorithm(s): {', '.join(sorted(set(unsupported)))}")
    selected_set = set(normalized)
    ordered = [algo for algo in DEFAULT_ALGORITHMS if algo in selected_set]
    return ordered


def _emit_log(json_logs: bool, event: str, message: str | None = None, **data) -> None:
    if json_logs:
        payload = {'event': event}
        if message is not None:
            payload['message'] = message
        if data:
            payload['data'] = data
        print(json.dumps(payload, ensure_ascii=False))
    else:
        if message is not None:
            print(message)
        elif data:
            details = ', '.join(f"{key}={value}" for key, value in data.items())
            print(f"{event}: {details}")
        else:
            print(event)


async def download_resource(session: aiohttp.ClientSession, url: str, max_retries: int, retry_base_delay: float) -> bytes:
    """Download resource from CDN URL with retry handling."""
    attempt = 0
    while True:
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.read()
        except Exception as e:
            attempt += 1
            if attempt > max_retries:
                raise RuntimeError(f"Failed to download {url}: {e}")
            delay = retry_base_delay * (2 ** (attempt - 1))
            await asyncio.sleep(delay)


def generate_sri_hash(content: bytes, algorithm: str = 'sha384') -> str:
    """Generate SRI hash for content."""
    if algorithm not in ('sha256', 'sha384', 'sha512'):
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    hash_obj = hashlib.new(algorithm)
    hash_obj.update(content)
    hash_b64 = base64.b64encode(hash_obj.digest()).decode('ascii')

    return f"{algorithm}-{hash_b64}"


async def process_resource(
    name: str,
    url: str,
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    algorithms: list,
    max_retries: int,
    retry_base_delay: float,
    json_logs: bool,
) -> dict:
    """Process single CDN resource."""
    _emit_log(json_logs, 'resource_start', message=f"Processing {name}: {url}", resource=name, url=url)
    try:
        async with semaphore:
            content = await download_resource(session, url, max_retries, retry_base_delay)
        hashes = {algo: generate_sri_hash(content, algo) for algo in algorithms}
        _emit_log(json_logs, 'resource_downloaded', message=f"  Downloaded {len(content)} bytes", resource=name, bytes=len(content))
        for algo, hash_value in hashes.items():
            _emit_log(
                json_logs,
                'resource_hash',
                message=f"  {algo}: {hash_value}",
                resource=name,
                algorithm=algo,
                hash=hash_value,
            )
        return hashes
    except Exception as e:
        _emit_log(json_logs, 'resource_error', message=f"Error processing {name}: {e}", resource=name, error=str(e))
        return {"error": str(e)}


async def main(
    resources: dict,
    algorithms: list,
    max_concurrency: int,
    request_timeout: int,
    output_path: Path,
    max_retries: int,
    retry_base_delay: float,
    json_logs: bool,
    compare_integrity: bool,
    user_agent: str,
) -> int:
    """Main function to process all CDN resources."""
    results = {}
    semaphore = asyncio.Semaphore(max_concurrency)
    timeout = aiohttp.ClientTimeout(total=request_timeout)
    async with aiohttp.ClientSession(timeout=timeout, headers={'User-Agent': user_agent}) as session:
        tasks = []
        for name in sorted(resources):
            url = resources[name]
            task = asyncio.create_task(
                process_resource(name, url, session, semaphore, algorithms, max_retries, retry_base_delay, json_logs)
            )
            tasks.append((name, task))

        for name, task in tasks:
            result = await task
            results[name] = result

    # Save results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, sort_keys=True)
    error_count = sum(1 for item in results.values() if 'error' in item)
    success_count = len(results) - error_count
    _emit_log(json_logs, 'summary', message=f"Results saved to: {output_path}", output=str(output_path))
    _emit_log(
        json_logs,
        'summary_counts',
        message=f"Summary: {success_count} succeeded, {error_count} failed",
        succeeded=success_count,
        failed=error_count,
    )

    integrity_mismatches = []
    if compare_integrity and CDN_RESOURCE_DEFINITIONS:
        integrity_mismatches = _compare_integrities(results, algorithms, json_logs)

    if integrity_mismatches:
        mismatch_resources = ', '.join(sorted(integrity_mismatches))
        _emit_log(
            json_logs,
            'integrity_mismatch_summary',
            message=f"Integrity mismatches detected for: {mismatch_resources}",
            mismatches=sorted(integrity_mismatches),
        )
    elif compare_integrity:
        _emit_log(json_logs, 'integrity_match', message="All integrities match existing definitions")

    # Exit code precedence: download errors (2) take priority over mismatches (3)
    if error_count > 0:
        return 2
    if integrity_mismatches:
        return 3
    return error_count


def _compare_integrities(results: dict, algorithms: list, json_logs: bool) -> list:
    mismatches = []
    for name, outcome in results.items():
        if 'error' in outcome:
            continue

        definition = CDN_RESOURCE_DEFINITIONS.get(name)
        if definition is None or not getattr(definition, 'integrity', None):
            _emit_log(json_logs, 'integrity_skip', message=f"No integrity reference for {name}", resource=name)
            continue

        expected_algo, expected_hash = definition.integrity.split('-', 1)
        generated_hash = outcome.get(expected_algo)
        if generated_hash is None:
            _emit_log(
                json_logs,
                'integrity_missing_algorithm',
                message=f"Generated hashes missing algorithm {expected_algo} for {name}",
                resource=name,
                algorithm=expected_algo,
            )
            mismatches.append(name)
            continue

        if generated_hash != definition.integrity:
            _emit_log(
                json_logs,
                'integrity_mismatch',
                message=f"Integrity mismatch for {name}",
                resource=name,
                expected=definition.integrity,
                actual=generated_hash,
            )
            mismatches.append(name)
        else:
            _emit_log(
                json_logs,
                'integrity_match_resource',
                message=f"Integrity matches for {name}",
                resource=name,
                algorithm=expected_algo,
            )

    return mismatches


if __name__ == '__main__':
    args = _parse_args()
    max_concurrency = args.max_concurrency or DEFAULT_MAX_CONCURRENCY
    request_timeout = args.request_timeout or DEFAULT_REQUEST_TIMEOUT
    output_path = args.output or DEFAULT_OUTPUT_PATH
    max_retries = args.max_retries or DEFAULT_MAX_RETRIES
    retry_base_delay = args.retry_base_delay or DEFAULT_RETRY_BASE_DELAY
    json_logs = args.json_logs
    compare_integrity = args.compare_integrity
    list_resources = args.list_resources
    user_agent = args.user_agent or DEFAULT_USER_AGENT

    resources_catalog = dict(CDN_RESOURCES)
    if args.resources_file is not None:
        try:
            file_resources = _load_resources_file(args.resources_file)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        resources_catalog.update(file_resources)

    try:
        resources_to_process = _select_resources(args.resources, resources_catalog)
        resources_to_process = _apply_url_overrides(resources_to_process, args.url_overrides)
        algorithms = _resolve_algorithms(args.algorithms)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.print_config:
        config = {
            'resources': resources_to_process,
            'algorithms': algorithms,
            'max_concurrency': max_concurrency,
            'request_timeout': request_timeout,
            'max_retries': max_retries,
            'retry_base_delay': retry_base_delay,
            'output_path': str(Path(output_path)),
            'user_agent': user_agent,
            'resources_file': str(args.resources_file.resolve()) if args.resources_file else None,
        }
        print(json.dumps(config, indent=2))
        sys.exit(0)

    if list_resources:
        for name in sorted(resources_catalog):
            info = {'url': resources_catalog[name]}
            definition = CDN_RESOURCE_DEFINITIONS.get(name)
            if definition is not None and getattr(definition, 'integrity', None):
                info['integrity'] = definition.integrity
            _emit_log(json_logs, 'resource_listing', message=f"{name}: {info['url']}", resource=name, **info)
        sys.exit(0)

    exit_status = asyncio.run(
        main(
            resources_to_process,
            algorithms,
            max_concurrency,
            request_timeout,
            Path(output_path),
            max_retries,
            retry_base_delay,
            json_logs,
            compare_integrity,
            user_agent,
        )
    )
    sys.exit(exit_status)
