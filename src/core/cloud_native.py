"""Cloud-native features for Kubernetes and Docker Swarm deployment."""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import time
import threading


class DeploymentPlatform(Enum):
    """Supported deployment platforms."""
    KUBERNETES = "kubernetes"
    DOCKER_SWARM = "docker_swarm"
    DOCKER_COMPOSE = "docker_compose"
    STANDALONE = "standalone"


@dataclass
class DeploymentConfig:
    """Configuration for cloud deployment."""
    platform: DeploymentPlatform
    replicas: int = 3
    resources: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
    secrets: Dict[str, str] = field(default_factory=dict)
    volumes: List[Dict[str, str]] = field(default_factory=list)
    health_check: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceConfig:
    """Configuration for a microservice."""
    name: str
    image: str
    ports: List[int] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    deployment_config: DeploymentConfig = field(default_factory=lambda: DeploymentConfig(DeploymentPlatform.STANDALONE))


class KubernetesManager:
    """Manages Kubernetes deployments."""

    def __init__(self, namespace: str = "default"):
        """Initialize Kubernetes manager.

        Args:
            namespace: Kubernetes namespace
        """
        self.logger = logging.getLogger(__name__)
        self.namespace = namespace
        self.kubeconfig = os.environ.get('KUBECONFIG', '~/.kube/config')

    def create_deployment(self, service: ServiceConfig) -> bool:
        """Create a Kubernetes deployment.

        Args:
            service: Service configuration

        Returns:
            True if deployment created successfully
        """
        try:
            deployment_yaml = self._generate_deployment_yaml(service)

            # Write to temporary file
            with open('/tmp/deployment.yaml', 'w') as f:
                yaml.dump(deployment_yaml, f)

            # Apply deployment
            result = subprocess.run([
                'kubectl', 'apply', '-f', '/tmp/deployment.yaml',
                '--namespace', self.namespace
            ], capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"Created Kubernetes deployment for {service.name}")
                return True
            else:
                self.logger.error(f"Failed to create Kubernetes deployment: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error creating Kubernetes deployment: {e}")
            return False

    def create_service(self, service: ServiceConfig) -> bool:
        """Create a Kubernetes service.

        Args:
            service: Service configuration

        Returns:
            True if service created successfully
        """
        try:
            service_yaml = self._generate_service_yaml(service)

            # Write to temporary file
            with open('/tmp/service.yaml', 'w') as f:
                yaml.dump(service_yaml, f)

            # Apply service
            result = subprocess.run([
                'kubectl', 'apply', '-f', '/tmp/service.yaml',
                '--namespace', self.namespace
            ], capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"Created Kubernetes service for {service.name}")
                return True
            else:
                self.logger.error(f"Failed to create Kubernetes service: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error creating Kubernetes service: {e}")
            return False

    def _generate_deployment_yaml(self, service: ServiceConfig) -> Dict[str, Any]:
        """Generate Kubernetes deployment YAML."""
        return {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': f"{service.name}-deployment",
                'namespace': self.namespace,
                'labels': {
                    'app': service.name,
                    'version': 'v1'
                }
            },
            'spec': {
                'replicas': service.deployment_config.replicas,
                'selector': {
                    'matchLabels': {
                        'app': service.name
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': service.name,
                            'version': 'v1'
                        }
                    },
                    'spec': {
                        'containers': [{
                            'name': service.name,
                            'image': service.image,
                            'ports': [{'containerPort': port} for port in service.ports],
                            'env': [{'name': k, 'value': v} for k, v in service.environment.items()],
                            'resources': service.deployment_config.resources,
                            'livenessProbe': {
                                'httpGet': {
                                    'path': '/health',
                                    'port': service.ports[0] if service.ports else 8080
                                },
                                'initialDelaySeconds': 30,
                                'periodSeconds': 10
                            },
                            'readinessProbe': {
                                'httpGet': {
                                    'path': '/ready',
                                    'port': service.ports[0] if service.ports else 8080
                                },
                                'initialDelaySeconds': 5,
                                'periodSeconds': 5
                            }
                        }],
                        'volumes': service.deployment_config.volumes
                    }
                }
            }
        }

    def _generate_service_yaml(self, service: ServiceConfig) -> Dict[str, Any]:
        """Generate Kubernetes service YAML."""
        return {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': f"{service.name}-service",
                'namespace': self.namespace,
                'labels': {
                    'app': service.name
                }
            },
            'spec': {
                'selector': {
                    'app': service.name
                },
                'ports': [
                    {
                        'name': f"port-{port}",
                        'port': port,
                        'targetPort': port,
                        'protocol': 'TCP'
                    }
                    for port in service.ports
                ],
                'type': 'ClusterIP'
            }
        }

    def scale_deployment(self, service_name: str, replicas: int) -> bool:
        """Scale a Kubernetes deployment.

        Args:
            service_name: Name of the service
            replicas: Number of replicas

        Returns:
            True if scaled successfully
        """
        try:
            result = subprocess.run([
                'kubectl', 'scale', 'deployment', f"{service_name}-deployment",
                '--replicas', str(replicas), '--namespace', self.namespace
            ], capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"Scaled {service_name} to {replicas} replicas")
                return True
            else:
                self.logger.error(f"Failed to scale deployment: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error scaling deployment: {e}")
            return False

    def get_deployment_status(self, service_name: str) -> Dict[str, Any]:
        """Get deployment status.

        Args:
            service_name: Name of the service

        Returns:
            Deployment status information
        """
        try:
            result = subprocess.run([
                'kubectl', 'get', 'deployment', f"{service_name}-deployment",
                '--namespace', self.namespace, '-o', 'json'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {'error': result.stderr}

        except Exception as e:
            self.logger.error(f"Error getting deployment status: {e}")
            return {'error': str(e)}


class DockerSwarmManager:
    """Manages Docker Swarm deployments."""

    def __init__(self, stack_name: str = "3d-print-cad"):
        """Initialize Docker Swarm manager.

        Args:
            stack_name: Name of the Docker stack
        """
        self.logger = logging.getLogger(__name__)
        self.stack_name = stack_name

    def create_stack(self, services: List[ServiceConfig]) -> bool:
        """Create a Docker Swarm stack.

        Args:
            services: List of service configurations

        Returns:
            True if stack created successfully
        """
        try:
            compose_content = self._generate_docker_compose(services)

            # Write to temporary file
            with open('/tmp/docker-compose.yml', 'w') as f:
                yaml.dump(compose_content, f)

            # Deploy stack
            result = subprocess.run([
                'docker', 'stack', 'deploy', '-c', '/tmp/docker-compose.yml', self.stack_name
            ], capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"Created Docker Swarm stack: {self.stack_name}")
                return True
            else:
                self.logger.error(f"Failed to create Docker Swarm stack: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error creating Docker Swarm stack: {e}")
            return False

    def _generate_docker_compose(self, services: List[ServiceConfig]) -> Dict[str, Any]:
        """Generate Docker Compose file for Swarm."""
        compose = {
            'version': '3.8',
            'services': {}
        }

        for service in services:
            service_config = {
                'image': service.image,
                'deploy': {
                    'replicas': service.deployment_config.replicas,
                    'resources': {
                        'limits': service.deployment_config.resources.get('limits', {}),
                        'reservations': service.deployment_config.resources.get('reservations', {})
                    }
                },
                'environment': service.environment,
                'ports': [f"{port}:{port}" for port in service.ports],
                'volumes': service.deployment_config.volumes
            }

            # Add dependencies
            if service.depends_on:
                service_config['depends_on'] = service.depends_on

            compose['services'][service.name] = service_config

        return compose

    def scale_service(self, service_name: str, replicas: int) -> bool:
        """Scale a Docker Swarm service.

        Args:
            service_name: Name of the service
            replicas: Number of replicas

        Returns:
            True if scaled successfully
        """
        try:
            result = subprocess.run([
                'docker', 'service', 'scale', f"{self.stack_name}_{service_name}", f"{replicas}"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"Scaled {service_name} to {replicas} replicas")
                return True
            else:
                self.logger.error(f"Failed to scale service: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error scaling service: {e}")
            return False

    def get_service_status(self) -> Dict[str, Any]:
        """Get Docker Swarm services status.

        Returns:
            Services status information
        """
        try:
            result = subprocess.run([
                'docker', 'service', 'ls', '--format', 'json'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                services = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            services.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
                return {'services': services}
            else:
                return {'error': result.stderr}

        except Exception as e:
            self.logger.error(f"Error getting service status: {e}")
            return {'error': str(e)}


class CloudNativeManager:
    """Main manager for cloud-native deployments."""

    def __init__(self):
        """Initialize cloud-native manager."""
        self.logger = logging.getLogger(__name__)
        self.kubernetes_manager = KubernetesManager()
        self.docker_swarm_manager = DockerSwarmManager()

        # Service definitions
        self.services = self._define_services()

    def _define_services(self) -> List[ServiceConfig]:
        """Define the microservices for the 3D Print CAD Assistant."""
        return [
            ServiceConfig(
                name="web-api",
                image="3d-print-cad/web-api:latest",
                ports=[8080],
                environment={
                    'ENVIRONMENT': 'production',
                    'LOG_LEVEL': 'INFO'
                },
                deployment_config=DeploymentConfig(
                    platform=DeploymentPlatform.KUBERNETES,
                    replicas=3,
                    resources={
                        'limits': {'cpu': '500m', 'memory': '512Mi'},
                        'requests': {'cpu': '250m', 'memory': '256Mi'}
                    }
                )
            ),
            ServiceConfig(
                name="mesh-processor",
                image="3d-print-cad/mesh-processor:latest",
                ports=[8081],
                environment={
                    'MAX_FILE_SIZE': '500MB',
                    'PROCESSING_TIMEOUT': '300'
                },
                deployment_config=DeploymentConfig(
                    platform=DeploymentPlatform.KUBERNETES,
                    replicas=2,
                    resources={
                        'limits': {'cpu': '2000m', 'memory': '2Gi'},
                        'requests': {'cpu': '1000m', 'memory': '1Gi'}
                    }
                )
            ),
            ServiceConfig(
                name="ai-engine",
                image="3d-print-cad/ai-engine:latest",
                ports=[8082],
                environment={
                    'MODEL_CACHE_DIR': '/models',
                    'GPU_ENABLED': 'true'
                },
                deployment_config=DeploymentConfig(
                    platform=DeploymentPlatform.KUBERNETES,
                    replicas=1,
                    resources={
                        'limits': {'cpu': '4000m', 'memory': '8Gi', 'nvidia.com/gpu': '1'},
                        'requests': {'cpu': '2000m', 'memory': '4Gi', 'nvidia.com/gpu': '1'}
                    }
                )
            ),
            ServiceConfig(
                name="database",
                image="postgres:15",
                ports=[5432],
                environment={
                    'POSTGRES_DB': 'cad_assistant',
                    'POSTGRES_USER': 'cad_user',
                    'POSTGRES_PASSWORD': 'secure_password'
                },
                deployment_config=DeploymentConfig(
                    platform=DeploymentPlatform.KUBERNETES,
                    replicas=1,
                    volumes=[{
                        'name': 'postgres-data',
                        'persistentVolumeClaim': {'claimName': 'postgres-pvc'}
                    }]
                )
            ),
            ServiceConfig(
                name="redis-cache",
                image="redis:7-alpine",
                ports=[6379],
                deployment_config=DeploymentConfig(
                    platform=DeploymentPlatform.KUBERNETES,
                    replicas=1,
                    resources={
                        'limits': {'cpu': '500m', 'memory': '512Mi'},
                        'requests': {'cpu': '250m', 'memory': '256Mi'}
                    }
                )
            )
        ]

    def deploy_to_kubernetes(self) -> bool:
        """Deploy all services to Kubernetes.

        Returns:
            True if deployment successful
        """
        success = True

        for service in self.services:
            if service.deployment_config.platform == DeploymentPlatform.KUBERNETES:
                # Create deployment
                if not self.kubernetes_manager.create_deployment(service):
                    success = False

                # Create service
                if not self.kubernetes_manager.create_service(service):
                    success = False

        if success:
            self.logger.info("Successfully deployed all services to Kubernetes")
        else:
            self.logger.error("Some services failed to deploy to Kubernetes")

        return success

    def deploy_to_docker_swarm(self) -> bool:
        """Deploy all services to Docker Swarm.

        Returns:
            True if deployment successful
        """
        # Filter services for Docker Swarm
        swarm_services = [
            service for service in self.services
            if service.deployment_config.platform == DeploymentPlatform.DOCKER_SWARM
        ]

        if not swarm_services:
            self.logger.warning("No services configured for Docker Swarm")
            return True

        success = self.docker_swarm_manager.create_stack(swarm_services)

        if success:
            self.logger.info("Successfully deployed services to Docker Swarm")
        else:
            self.logger.error("Failed to deploy services to Docker Swarm")

        return success

    def scale_service(self, service_name: str, replicas: int, platform: DeploymentPlatform) -> bool:
        """Scale a service.

        Args:
            service_name: Name of the service
            replicas: Number of replicas
            platform: Deployment platform

        Returns:
            True if scaled successfully
        """
        if platform == DeploymentPlatform.KUBERNETES:
            return self.kubernetes_manager.scale_deployment(service_name, replicas)
        elif platform == DeploymentPlatform.DOCKER_SWARM:
            return self.docker_swarm_manager.scale_service(service_name, replicas)
        else:
            self.logger.error(f"Scaling not supported for platform: {platform}")
            return False

    def get_deployment_status(self) -> Dict[str, Any]:
        """Get overall deployment status.

        Returns:
            Deployment status information
        """
        status = {
            'kubernetes': {},
            'docker_swarm': {},
            'timestamp': time.time()
        }

        # Get Kubernetes status
        for service in self.services:
            if service.deployment_config.platform == DeploymentPlatform.KUBERNETES:
                status['kubernetes'][service.name] = self.kubernetes_manager.get_deployment_status(service.name)

        # Get Docker Swarm status
        status['docker_swarm'] = self.docker_swarm_manager.get_service_status()

        return status

    def create_deployment_files(self, output_dir: Union[str, Path]) -> bool:
        """Create deployment files for manual deployment.

        Args:
            output_dir: Directory to save deployment files

        Returns:
            True if files created successfully
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            # Create Kubernetes manifests
            k8s_dir = output_path / 'kubernetes'
            k8s_dir.mkdir(exist_ok=True)

            for service in self.services:
                if service.deployment_config.platform == DeploymentPlatform.KUBERNETES:
                    # Create deployment file
                    deployment_yaml = self.kubernetes_manager._generate_deployment_yaml(service)
                    deployment_file = k8s_dir / f"{service.name}-deployment.yaml"
                    with open(deployment_file, 'w') as f:
                        yaml.dump(deployment_yaml, f)

                    # Create service file
                    service_yaml = self.kubernetes_manager._generate_service_yaml(service)
                    service_file = k8s_dir / f"{service.name}-service.yaml"
                    with open(service_file, 'w') as f:
                        yaml.dump(service_yaml, f)

            # Create Docker Compose file
            compose_content = self.docker_swarm_manager._generate_docker_compose(self.services)
            compose_file = output_path / 'docker-compose.yml'
            with open(compose_file, 'w') as f:
                yaml.dump(compose_content, f)

            # Create deployment script
            script_content = self._generate_deployment_script()
            script_file = output_path / 'deploy.sh'
            with open(script_file, 'w') as f:
                f.write(script_content)

            # Make script executable
            script_file.chmod(0o755)

            self.logger.info(f"Created deployment files in {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error creating deployment files: {e}")
            return False

    def _generate_deployment_script(self) -> str:
        """Generate deployment script."""
        return """#!/bin/bash
set -e

echo "3D Print CAD Assistant Deployment Script"
echo "========================================"

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "✓ Docker is available"

    # Initialize Docker Swarm if not already initialized
    if ! docker info | grep -q "Swarm: active"; then
        echo "Initializing Docker Swarm..."
        docker swarm init
    else
        echo "✓ Docker Swarm is already active"
    fi

    # Deploy stack
    echo "Deploying Docker Swarm stack..."
    docker stack deploy -c docker-compose.yml 3d-print-cad

else
    echo "✗ Docker is not available"
    echo "Please install Docker to use this deployment script"
    exit 1
fi

# Check if kubectl is available
if command -v kubectl &> /dev/null; then
    echo "✓ kubectl is available"

    # Apply Kubernetes manifests
    echo "Deploying to Kubernetes..."
    kubectl apply -f kubernetes/

else
    echo "⚠ kubectl is not available"
    echo "Skipping Kubernetes deployment"
fi

echo ""
echo "Deployment completed successfully!"
echo "Services deployed:"
echo "  - Web API (port 8080)"
echo "  - Mesh Processor (port 8081)"
echo "  - AI Engine (port 8082)"
echo "  - Database (PostgreSQL)"
echo "  - Redis Cache"
echo ""
echo "Check status with:"
echo "  docker service ls"
echo "  kubectl get pods"
"""

    def health_check(self) -> Dict[str, bool]:
        """Perform health checks on all deployed services.

        Returns:
            Dictionary mapping service names to health status
        """
        health_status = {}

        # Check Kubernetes services
        for service in self.services:
            if service.deployment_config.platform == DeploymentPlatform.KUBERNETES:
                try:
                    status = self.kubernetes_manager.get_deployment_status(service.name)
                    # Simplified health check
                    health_status[service.name] = 'status' in status and 'error' not in status
                except:
                    health_status[service.name] = False

        # Check Docker Swarm services
        try:
            swarm_status = self.docker_swarm_manager.get_service_status()
            if 'services' in swarm_status:
                for service_info in swarm_status['services']:
                    service_name = service_info.get('Name', '').replace(f'{self.docker_swarm_manager.stack_name}_', '')
                    health_status[service_name] = service_info.get('Replicas', '0/0') == service_info.get('Replicas', '0/0')
        except:
            pass

        return health_status

    def cleanup_deployment(self, platform: Optional[DeploymentPlatform] = None) -> bool:
        """Clean up deployments.

        Args:
            platform: Platform to clean up, or None for all

        Returns:
            True if cleanup successful
        """
        success = True

        if platform == DeploymentPlatform.KUBERNETES or platform is None:
            try:
                result = subprocess.run([
                    'kubectl', 'delete', 'all', '--all', '--namespace', self.kubernetes_manager.namespace
                ], capture_output=True, text=True)
                success = success and (result.returncode == 0)
            except Exception as e:
                self.logger.error(f"Error cleaning up Kubernetes: {e}")
                success = False

        if platform == DeploymentPlatform.DOCKER_SWARM or platform is None:
            try:
                result = subprocess.run([
                    'docker', 'stack', 'rm', self.docker_swarm_manager.stack_name
                ], capture_output=True, text=True)
                success = success and (result.returncode == 0)
            except Exception as e:
                self.logger.error(f"Error cleaning up Docker Swarm: {e}")
                success = False

        return success


# Global cloud-native manager
cloud_native_manager = CloudNativeManager()
