"""Comprehensive API integration layer for external services."""

import requests
import json
import time
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass
from enum import Enum
import threading
from urllib.parse import urljoin, urlparse


class HttpMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class ServiceStatus(Enum):
    """Service status states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceEndpoint:
    """Definition of a service endpoint."""
    name: str
    url: str
    method: HttpMethod
    headers: Dict[str, str] = None
    timeout: float = 30.0
    retries: int = 3
    retry_delay: float = 1.0
    health_check: Optional[Callable] = None


@dataclass
class ServiceResponse:
    """Response from a service call."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    status_code: int = 0
    response_time: float = 0.0
    headers: Dict[str, str] = None


class ServiceClient:
    """Client for making requests to external services."""

    def __init__(self, base_url: str, default_headers: Optional[Dict[str, str]] = None):
        """Initialize service client.

        Args:
            base_url: Base URL for the service
            default_headers: Default headers to include in requests
        """
        self.base_url = base_url.rstrip('/')
        self.default_headers = default_headers or {}
        self.session = requests.Session()

        # Update session headers
        self.session.headers.update(self.default_headers)

    def request(self,
               endpoint: str,
               method: HttpMethod = HttpMethod.GET,
               params: Optional[Dict[str, Any]] = None,
               data: Any = None,
               json_data: Any = None,
               headers: Optional[Dict[str, str]] = None,
               timeout: Optional[float] = None) -> ServiceResponse:
        """Make a request to the service.

        Args:
            endpoint: API endpoint (relative to base_url)
            method: HTTP method
            params: Query parameters
            data: Request data (form data)
            json_data: JSON data
            headers: Additional headers
            timeout: Request timeout

        Returns:
            ServiceResponse object
        """
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        request_headers = {**self.default_headers}
        if headers:
            request_headers.update(headers)

        start_time = time.time()

        try:
            response = self.session.request(
                method=method.value,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=request_headers,
                timeout=timeout
            )

            response_time = time.time() - start_time

            # Handle response
            if response.status_code < 400:
                try:
                    response_data = response.json()
                except json.JSONDecodeError:
                    response_data = response.text

                return ServiceResponse(
                    success=True,
                    data=response_data,
                    status_code=response.status_code,
                    response_time=response_time,
                    headers=dict(response.headers)
                )
            else:
                return ServiceResponse(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text}",
                    status_code=response.status_code,
                    response_time=response_time,
                    headers=dict(response.headers)
                )

        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            return ServiceResponse(
                success=False,
                error=str(e),
                response_time=response_time
            )


class ServiceRegistry:
    """Registry for managing external service connections."""

    def __init__(self):
        """Initialize service registry."""
        self.logger = logging.getLogger(__name__)
        self.services: Dict[str, ServiceClient] = {}
        self.endpoints: Dict[str, ServiceEndpoint] = {}
        self.status: Dict[str, ServiceStatus] = {}
        self._lock = threading.RLock()

    def register_service(self, name: str, base_url: str,
                        default_headers: Optional[Dict[str, str]] = None):
        """Register an external service.

        Args:
            name: Service name
            base_url: Service base URL
            default_headers: Default headers for the service
        """
        with self._lock:
            self.services[name] = ServiceClient(base_url, default_headers)
            self.status[name] = ServiceStatus.UNKNOWN
            self.logger.info(f"Registered service: {name} at {base_url}")

    def register_endpoint(self, service_name: str, endpoint: ServiceEndpoint):
        """Register an endpoint for a service.

        Args:
            service_name: Name of the service
            endpoint: Endpoint definition
        """
        with self._lock:
            endpoint_key = f"{service_name}:{endpoint.name}"
            self.endpoints[endpoint_key] = endpoint
            self.logger.info(f"Registered endpoint: {endpoint_key}")

    def call_endpoint(self, service_name: str, endpoint_name: str,
                     **kwargs) -> ServiceResponse:
        """Call a registered endpoint.

        Args:
            service_name: Service name
            endpoint_name: Endpoint name
            **kwargs: Arguments passed to the request

        Returns:
            ServiceResponse object
        """
        with self._lock:
            endpoint_key = f"{service_name}:{endpoint_name}"

            if endpoint_key not in self.endpoints:
                return ServiceResponse(
                    success=False,
                    error=f"Endpoint {endpoint_key} not found"
                )

            endpoint = self.endpoints[endpoint_key]

            if service_name not in self.services:
                return ServiceResponse(
                    success=False,
                    error=f"Service {service_name} not registered"
                )

            service = self.services[service_name]

            # Merge endpoint defaults with provided arguments
            request_kwargs = {
                'method': endpoint.method,
                'timeout': endpoint.timeout
            }

            # Override with provided arguments
            for key, value in kwargs.items():
                if key in ['params', 'data', 'json_data', 'headers']:
                    request_kwargs[key] = value

            return service.request(endpoint.url, **request_kwargs)

    def check_service_health(self, service_name: str) -> ServiceStatus:
        """Check health of a service.

        Args:
            service_name: Service name

        Returns:
            Service status
        """
        with self._lock:
            if service_name not in self.services:
                return ServiceStatus.UNKNOWN

            service = self.services[service_name]

            # Find health check endpoint for this service
            health_endpoints = [
                endpoint for key, endpoint in self.endpoints.items()
                if key.startswith(f"{service_name}:") and endpoint.health_check
            ]

            if not health_endpoints:
                # Basic connectivity check
                try:
                    response = service.request("", method=HttpMethod.GET, timeout=5.0)
                    self.status[service_name] = ServiceStatus.HEALTHY if response.success else ServiceStatus.UNHEALTHY
                except:
                    self.status[service_name] = ServiceStatus.UNHEALTHY
            else:
                # Use registered health check
                for endpoint in health_endpoints:
                    try:
                        if endpoint.health_check:
                            status = endpoint.health_check(service)
                            self.status[service_name] = status
                            break
                    except Exception as e:
                        self.logger.error(f"Health check failed for {service_name}: {e}")
                        self.status[service_name] = ServiceStatus.UNHEALTHY

            return self.status[service_name]

    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get detailed status of a service.

        Args:
            service_name: Service name

        Returns:
            Service status information
        """
        with self._lock:
            endpoints = [
                key for key in self.endpoints.keys()
                if key.startswith(f"{service_name}:")
            ]

            return {
                'name': service_name,
                'status': self.status.get(service_name, ServiceStatus.UNKNOWN).value,
                'endpoints': endpoints,
                'last_checked': time.time()
            }


class APIIntegrationManager:
    """Manager for integrating with various external APIs."""

    def __init__(self):
        """Initialize API integration manager."""
        self.logger = logging.getLogger(__name__)
        self.registry = ServiceRegistry()
        self._initialize_common_services()

    def _initialize_common_services(self):
        """Initialize commonly used external services."""
        # These would be configured based on actual API keys and endpoints
        # For demonstration, we'll show the structure

        # Example: CAD model repositories
        # self.registry.register_service(
        #     "thingiverse",
        #     "https://api.thingiverse.com/v1",
        #     {"Authorization": "Bearer YOUR_API_KEY"}
        # )

        # Example: 3D printing services
        # self.registry.register_service(
        #     "print_service",
        #     "https://api.printservice.com/v2"
        # )

        # Example: Material databases
        # self.registry.register_service(
        #     "material_db",
        #     "https://api.materialdb.com/v1"
        # )

    def search_cad_models(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for CAD models in external repositories.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of CAD model information
        """
        results = []

        # This would integrate with actual CAD model APIs
        # For now, return empty results
        self.logger.info(f"Searching CAD models for: {query}")

        return results

    def get_material_properties(self, material_name: str) -> Optional[Dict[str, Any]]:
        """Get material properties from external database.

        Args:
            material_name: Name of the material

        Returns:
            Material properties or None if not found
        """
        # This would query actual material databases
        self.logger.info(f"Looking up material properties for: {material_name}")

        return None

    def submit_print_job(self, job_data: Dict[str, Any]) -> Optional[str]:
        """Submit a print job to external printing service.

        Args:
            job_data: Print job information

        Returns:
            Job ID if successful, None otherwise
        """
        # This would integrate with actual printing services
        self.logger.info(f"Submitting print job: {job_data.get('name', 'Unnamed')}")

        return None

    def get_print_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a print job.

        Args:
            job_id: Print job ID

        Returns:
            Print job status or None if not found
        """
        # This would query actual printing services
        self.logger.info(f"Checking print status for job: {job_id}")

        return None

    def register_webhook(self, service_name: str, webhook_url: str,
                        events: List[str]) -> bool:
        """Register webhook for service events.

        Args:
            service_name: Service name
            webhook_url: Webhook URL to register
            events: List of events to subscribe to

        Returns:
            True if registration successful
        """
        # This would register webhooks with external services
        self.logger.info(f"Registering webhook for {service_name}: {webhook_url}")

        return False

    def get_service_health_report(self) -> Dict[str, Any]:
        """Get health report for all registered services.

        Returns:
            Health report dictionary
        """
        report = {
            'timestamp': time.time(),
            'services': {},
            'overall_status': ServiceStatus.HEALTHY.value
        }

        for service_name in self.registry.services.keys():
            status = self.registry.check_service_health(service_name)
            service_info = self.registry.get_service_status(service_name)

            report['services'][service_name] = service_info

            # Determine overall status
            if status == ServiceStatus.UNHEALTHY:
                report['overall_status'] = ServiceStatus.UNHEALTHY.value
            elif (status == ServiceStatus.DEGRADED and
                  report['overall_status'] == ServiceStatus.HEALTHY.value):
                report['overall_status'] = ServiceStatus.DEGRADED.value

        return report


class WebhookManager:
    """Manager for handling incoming webhooks."""

    def __init__(self):
        """Initialize webhook manager."""
        self.logger = logging.getLogger(__name__)
        self.handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def register_handler(self, event_type: str, handler: Callable):
        """Register a webhook handler.

        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        with self._lock:
            if event_type not in self.handlers:
                self.handlers[event_type] = []
            self.handlers[event_type].append(handler)
            self.logger.info(f"Registered webhook handler for event: {event_type}")

    def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Handle an incoming webhook.

        Args:
            event_type: Type of webhook event
            payload: Webhook payload

        Returns:
            True if handled successfully
        """
        with self._lock:
            if event_type not in self.handlers:
                self.logger.warning(f"No handlers registered for event: {event_type}")
                return False

            success = True
            for handler in self.handlers[event_type]:
                try:
                    handler(payload)
                except Exception as e:
                    self.logger.error(f"Webhook handler failed for {event_type}: {e}")
                    success = False

            return success

    def list_handlers(self) -> Dict[str, int]:
        """List registered webhook handlers.

        Returns:
            Dictionary mapping event types to handler counts
        """
        with self._lock:
            return {event: len(handlers) for event, handlers in self.handlers.items()}


# Global instances
api_manager = APIIntegrationManager()
webhook_manager = WebhookManager()


# Convenience functions
def register_api_service(name: str, base_url: str, headers: Optional[Dict[str, str]] = None):
    """Register an external API service."""
    api_manager.registry.register_service(name, base_url, headers)


def call_api_endpoint(service: str, endpoint: str, **kwargs) -> ServiceResponse:
    """Call an API endpoint."""
    return api_manager.registry.call_endpoint(service, endpoint, **kwargs)


def register_webhook_handler(event: str, handler: Callable):
    """Register a webhook event handler."""
    webhook_manager.register_handler(event, handler)
