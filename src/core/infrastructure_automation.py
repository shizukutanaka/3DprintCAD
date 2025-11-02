"""Terraform/Ansible-inspired infrastructure automation for 3D CAD operations."""

from __future__ import annotations

import logging
import time
import json
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import subprocess
import tempfile
import os


class InfrastructureProvider(Enum):
    """Infrastructure providers."""
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    LOCAL = "local"


class ConfigurationState(Enum):
    """Configuration states."""
    PLANNED = "planned"
    APPLYING = "applying"
    APPLIED = "applied"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"
    FAILED = "failed"


@dataclass
class Resource:
    """Infrastructure resource."""
    resource_type: str
    resource_name: str
    provider: InfrastructureProvider
    configuration: Dict[str, Any]
    state: ConfigurationState = ConfigurationState.PLANNED
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.resource_name:
            self.resource_name = f"{self.resource_type}_{int(time.time() * 1000000)}"


@dataclass
class InfrastructurePlan:
    """Infrastructure plan."""
    plan_id: str
    resources: Dict[str, Resource] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    backend_config: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.plan_id:
            self.plan_id = f"plan_{int(time.time() * 1000000)}"


class TerraformStyleManager:
    """Terraform-inspired infrastructure manager."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.plans: Dict[str, InfrastructurePlan] = {}
        self.state_storage: Dict[str, Dict[str, Any]] = {}
        self.providers: Dict[InfrastructureProvider, Dict[str, Any]] = {}

    def create_infrastructure_plan(self, plan_id: str,
                                  resources: List[Resource],
                                  variables: Dict[str, Any] = None) -> InfrastructurePlan:
        """Create infrastructure plan."""
        plan = InfrastructurePlan(
            plan_id=plan_id,
            resources={resource.resource_name: resource for resource in resources},
            variables=variables or {}
        )

        self.plans[plan_id] = plan

        self.logger.info(f"Created infrastructure plan: {plan_id}")
        return plan

    def apply_plan(self, plan_id: str) -> Dict[str, Any]:
        """Apply infrastructure plan."""
        if plan_id not in self.plans:
            return {"error": f"Plan {plan_id} not found"}

        plan = self.plans[plan_id]
        apply_result = {
            "plan_id": plan_id,
            "resources_created": 0,
            "resources_updated": 0,
            "resources_destroyed": 0,
            "execution_time": 0.0,
            "success": True
        }

        start_time = time.time()

        try:
            # Resolve dependencies
            execution_order = self._resolve_dependency_order(plan.resources)

            # Apply resources in order
            for resource_name in execution_order:
                resource = plan.resources[resource_name]

                if self._apply_resource(resource):
                    resource.state = ConfigurationState.APPLIED
                    apply_result["resources_created"] += 1
                else:
                    resource.state = ConfigurationState.FAILED
                    apply_result["success"] = False

            apply_result["execution_time"] = time.time() - start_time

            # Store state
            self.state_storage[plan_id] = {
                "plan": plan.__dict__,
                "apply_result": apply_result,
                "applied_at": time.time()
            }

        except Exception as e:
            apply_result["success"] = False
            apply_result["error"] = str(e)

        return apply_result

    def _resolve_dependency_order(self, resources: Dict[str, Resource]) -> List[str]:
        """Resolve resource dependency order."""
        # Simple topological sort
        visited = set()
        temp_visited = set()
        order = []

        def visit(resource_name: str):
            if resource_name in temp_visited:
                raise ValueError(f"Circular dependency detected for {resource_name}")
            if resource_name in visited:
                return

            temp_visited.add(resource_name)

            # Visit dependencies
            if resource_name in resources:
                for dep in resources[resource_name].dependencies:
                    visit(dep)

            temp_visited.remove(resource_name)
            visited.add(resource_name)
            order.append(resource_name)

        # Visit all resources
        for resource_name in resources.keys():
            if resource_name not in visited:
                visit(resource_name)

        return order

    def _apply_resource(self, resource: Resource) -> bool:
        """Apply single resource."""
        try:
            if resource.provider == InfrastructureProvider.DOCKER:
                return self._apply_docker_resource(resource)
            elif resource.provider == InfrastructureProvider.KUBERNETES:
                return self._apply_kubernetes_resource(resource)
            elif resource.provider == InfrastructureProvider.LOCAL:
                return self._apply_local_resource(resource)
            else:
                self.logger.warning(f"Unsupported provider: {resource.provider}")
                return False

        except Exception as e:
            self.logger.error(f"Resource application failed: {e}")
            return False

    def _apply_docker_resource(self, resource: Resource) -> bool:
        """Apply Docker resource."""
        config = resource.configuration

        # Simulate Docker container creation
        container_name = config.get("name", resource.resource_name)
        image = config.get("image", "cad-service:latest")

        # In real implementation, would run docker commands
        self.logger.info(f"Created Docker container: {container_name} from image {image}")
        return True

    def _apply_kubernetes_resource(self, resource: Resource) -> bool:
        """Apply Kubernetes resource."""
        config = resource.configuration

        # Simulate Kubernetes deployment
        deployment_name = config.get("name", resource.resource_name)
        replicas = config.get("replicas", 1)

        self.logger.info(f"Created Kubernetes deployment: {deployment_name} with {replicas} replicas")
        return True

    def _apply_local_resource(self, resource: Resource) -> bool:
        """Apply local resource."""
        config = resource.configuration

        # Simulate local service setup
        service_name = config.get("name", resource.resource_name)
        port = config.get("port", 8080)

        self.logger.info(f"Started local service: {service_name} on port {port}")
        return True

    def destroy_plan(self, plan_id: str) -> Dict[str, Any]:
        """Destroy infrastructure plan."""
        if plan_id not in self.plans:
            return {"error": f"Plan {plan_id} not found"}

        plan = self.plans[plan_id]
        destroy_result = {
            "plan_id": plan_id,
            "resources_destroyed": 0,
            "execution_time": 0.0,
            "success": True
        }

        start_time = time.time()

        try:
            # Destroy in reverse dependency order
            execution_order = self._resolve_dependency_order(plan.resources)
            execution_order.reverse()

            for resource_name in execution_order:
                resource = plan.resources[resource_name]

                if self._destroy_resource(resource):
                    resource.state = ConfigurationState.DESTROYED
                    destroy_result["resources_destroyed"] += 1
                else:
                    resource.state = ConfigurationState.FAILED
                    destroy_result["success"] = False

            destroy_result["execution_time"] = time.time() - start_time

        except Exception as e:
            destroy_result["success"] = False
            destroy_result["error"] = str(e)

        return destroy_result

    def _destroy_resource(self, resource: Resource) -> bool:
        """Destroy single resource."""
        try:
            if resource.provider == InfrastructureProvider.DOCKER:
                return self._destroy_docker_resource(resource)
            elif resource.provider == InfrastructureProvider.KUBERNETES:
                return self._destroy_kubernetes_resource(resource)
            elif resource.provider == InfrastructureProvider.LOCAL:
                return self._destroy_local_resource(resource)
            else:
                return False

        except Exception as e:
            self.logger.error(f"Resource destruction failed: {e}")
            return False

    def _destroy_docker_resource(self, resource: Resource) -> bool:
        """Destroy Docker resource."""
        config = resource.configuration
        container_name = config.get("name", resource.resource_name)

        self.logger.info(f"Destroyed Docker container: {container_name}")
        return True

    def _destroy_kubernetes_resource(self, resource: Resource) -> bool:
        """Destroy Kubernetes resource."""
        config = resource.configuration
        deployment_name = config.get("name", resource.resource_name)

        self.logger.info(f"Destroyed Kubernetes deployment: {deployment_name}")
        return True

    def _destroy_local_resource(self, resource: Resource) -> bool:
        """Destroy local resource."""
        config = resource.configuration
        service_name = config.get("name", resource.resource_name)

        self.logger.info(f"Stopped local service: {service_name}")
        return True

    def get_plan_status(self, plan_id: str) -> Dict[str, Any]:
        """Get plan status."""
        if plan_id not in self.plans:
            return {"error": f"Plan {plan_id} not found"}

        plan = self.plans[plan_id]

        resource_status = {}
        for resource_name, resource in plan.resources.items():
            resource_status[resource_name] = {
                "state": resource.state.value,
                "provider": resource.provider.value,
                "dependencies": resource.dependencies
            }

        return {
            "plan_id": plan_id,
            "created_at": plan.created_at,
            "resource_count": len(plan.resources),
            "resource_status": resource_status,
            "variables": plan.variables
        }


class AnsibleStyleConfiguration:
    """Ansible-inspired configuration management."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.playbooks: Dict[str, Dict[str, Any]] = {}
        self.roles: Dict[str, Dict[str, Any]] = {}
        self.inventory: Dict[str, List[str]] = {}

    def create_playbook(self, playbook_name: str, playbook_def: Dict[str, Any]) -> bool:
        """Create Ansible playbook."""
        try:
            self.playbooks[playbook_name] = playbook_def

            self.logger.info(f"Created playbook: {playbook_name}")
            return True

        except Exception as e:
            self.logger.error(f"Playbook creation failed: {e}")
            return False

    def create_role(self, role_name: str, role_def: Dict[str, Any]) -> bool:
        """Create Ansible role."""
        try:
            self.roles[role_name] = role_def

            self.logger.info(f"Created role: {role_name}")
            return True

        except Exception as e:
            self.logger.error(f"Role creation failed: {e}")
            return False

    def setup_inventory(self, inventory_name: str, hosts: List[str]) -> bool:
        """Setup inventory."""
        try:
            self.inventory[inventory_name] = hosts

            self.logger.info(f"Setup inventory: {inventory_name} with {len(hosts)} hosts")
            return True

        except Exception as e:
            self.logger.error(f"Inventory setup failed: {e}")
            return False

    def execute_playbook(self, playbook_name: str, inventory_name: str = "default") -> Dict[str, Any]:
        """Execute Ansible playbook."""
        if playbook_name not in self.playbooks:
            return {"error": f"Playbook {playbook_name} not found"}

        if inventory_name not in self.inventory:
            return {"error": f"Inventory {inventory_name} not found"}

        playbook = self.playbooks[playbook_name]
        hosts = self.inventory[inventory_name]

        execution_result = {
            "playbook": playbook_name,
            "inventory": inventory_name,
            "hosts": hosts,
            "tasks_executed": 0,
            "hosts_affected": 0,
            "execution_time": 0.0,
            "success": True
        }

        start_time = time.time()

        try:
            # Simulate playbook execution
            for host in hosts:
                for task in playbook.get("tasks", []):
                    execution_result["tasks_executed"] += 1

                    # Simulate task execution
                    if self._execute_task(task, host):
                        execution_result["hosts_affected"] += 1

            execution_result["execution_time"] = time.time() - start_time

        except Exception as e:
            execution_result["success"] = False
            execution_result["error"] = str(e)

        return execution_result

    def _execute_task(self, task: Dict[str, Any], host: str) -> bool:
        """Execute single task."""
        try:
            task_name = task.get("name", "unnamed_task")
            module = task.get("module", "shell")
            args = task.get("args", "")

            # Simulate task execution
            self.logger.info(f"Executing task '{task_name}' on {host} using {module}")

            # In real implementation, would execute Ansible module
            return True

        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            return False

    def get_configuration_status(self) -> Dict[str, Any]:
        """Get configuration status."""
        return {
            "playbooks": len(self.playbooks),
            "roles": len(self.roles),
            "inventories": len(self.inventory),
            "playbook_names": list(self.playbooks.keys()),
            "role_names": list(self.roles.keys()),
            "inventory_names": list(self.inventory.keys())
        }


class CADInfrastructureManager:
    """CAD infrastructure automation manager."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.terraform_manager = TerraformStyleManager()
        self.ansible_manager = AnsibleStyleConfiguration()
        self.deployed_resources: Dict[str, Dict[str, Any]] = {}

    def setup_cad_infrastructure(self) -> bool:
        """Setup CAD infrastructure."""
        try:
            # Setup Terraform providers
            self.terraform_manager.providers[InfrastructureProvider.DOCKER] = {
                "api_version": "1.40",
                "registry_mirrors": []
            }

            self.terraform_manager.providers[InfrastructureProvider.KUBERNETES] = {
                "config_path": "~/.kube/config",
                "config_context": "default"
            }

            # Setup Ansible roles
            self.ansible_manager.create_role("cad_service", {
                "tasks": [
                    {
                        "name": "Install CAD dependencies",
                        "package": {"name": "cad-libs", "state": "present"},
                        "become": True
                    },
                    {
                        "name": "Configure CAD service",
                        "service": {"name": "cad-service", "state": "started", "enabled": True},
                        "become": True
                    }
                ]
            })

            self.ansible_manager.create_role("mesh_processor", {
                "tasks": [
                    {
                        "name": "Install mesh processing tools",
                        "package": {"name": "mesh-tools", "state": "present"},
                        "become": True
                    }
                ]
            })

            # Setup inventory
            self.ansible_manager.setup_inventory("cad_servers", [
                "cad-server-1",
                "cad-server-2",
                "mesh-processor-1"
            ])

            self.logger.info("CAD infrastructure setup completed")
            return True

        except Exception as e:
            self.logger.error(f"Infrastructure setup failed: {e}")
            return False

    def deploy_cad_services(self) -> Dict[str, Any]:
        """Deploy CAD services."""
        deployment_result = {
            "deployment_id": f"deploy_{int(time.time())}",
            "services_deployed": [],
            "deployment_time": 0.0,
            "success": True
        }

        start_time = time.time()

        try:
            # Create infrastructure plan
            resources = [
                Resource(
                    resource_type="container",
                    resource_name="cad_service",
                    provider=InfrastructureProvider.DOCKER,
                    configuration={
                        "name": "cad-service",
                        "image": "cad-service:latest",
                        "ports": ["8080:8080"],
                        "environment": {"CAD_ENV": "production"}
                    }
                ),
                Resource(
                    resource_type="deployment",
                    resource_name="mesh_processor",
                    provider=InfrastructureProvider.KUBERNETES,
                    configuration={
                        "name": "mesh-processor",
                        "image": "mesh-processor:latest",
                        "replicas": 3,
                        "resources": {"requests": {"cpu": "100m", "memory": "256Mi"}}
                    },
                    dependencies=["cad_service"]
                )
            ]

            plan = self.terraform_manager.create_infrastructure_plan("cad_deployment", resources)

            # Apply plan
            apply_result = self.terraform_manager.apply_plan("cad_deployment")
            deployment_result.update(apply_result)

            # Run Ansible playbooks
            ansible_result = self.ansible_manager.execute_playbook("cad_service")
            deployment_result["ansible_result"] = ansible_result

            deployment_result["deployment_time"] = time.time() - start_time

        except Exception as e:
            deployment_result["success"] = False
            deployment_result["error"] = str(e)

        return deployment_result

    def get_infrastructure_status(self) -> Dict[str, Any]:
        """Get infrastructure status."""
        return {
            "terraform": {
                "plans": len(self.terraform_manager.plans),
                "state_storage": len(self.terraform_manager.state_storage)
            },
            "ansible": self.ansible_manager.get_configuration_status(),
            "deployed_resources": len(self.deployed_resources),
            "infrastructure_health": "healthy"
        }

    def destroy_infrastructure(self) -> Dict[str, Any]:
        """Destroy infrastructure."""
        destroy_result = {
            "destruction_time": 0.0,
            "resources_destroyed": 0,
            "success": True
        }

        start_time = time.time()

        try:
            # Destroy Terraform plans
            for plan_id in list(self.terraform_manager.plans.keys()):
                destroy_result_tf = self.terraform_manager.destroy_plan(plan_id)
                destroy_result["resources_destroyed"] += destroy_result_tf.get("resources_destroyed", 0)

            destroy_result["destruction_time"] = time.time() - start_time

        except Exception as e:
            destroy_result["success"] = False
            destroy_result["error"] = str(e)

        return destroy_result


class InfrastructureAutomationSystem:
    """Complete infrastructure automation system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.infrastructure_manager = CADInfrastructureManager()
        self.deployment_history: List[Dict[str, Any]] = []

    def initialize_infrastructure(self) -> bool:
        """Initialize infrastructure system."""
        try:
            if not self.infrastructure_manager.setup_cad_infrastructure():
                return False

            self.logger.info("Infrastructure automation system initialized")
            return True

        except Exception as e:
            self.logger.error(f"Infrastructure initialization failed: {e}")
            return False

    def deploy_cad_environment(self, environment: str = "production") -> Dict[str, Any]:
        """Deploy CAD environment."""
        deployment_result = {
            "environment": environment,
            "deployment_timestamp": time.time(),
            "infrastructure_deployment": {},
            "configuration_deployment": {},
            "overall_success": True
        }

        try:
            # Deploy infrastructure
            infra_result = self.infrastructure_manager.deploy_cad_services()
            deployment_result["infrastructure_deployment"] = infra_result

            # Deploy configuration
            config_result = self.infrastructure_manager.ansible_manager.execute_playbook("cad_service")
            deployment_result["configuration_deployment"] = config_result

            # Overall success
            deployment_result["overall_success"] = (
                infra_result.get("success", False) and
                config_result.get("success", False)
            )

            # Record deployment
            self.deployment_history.append(deployment_result)

        except Exception as e:
            deployment_result["overall_success"] = False
            deployment_result["error"] = str(e)

        return deployment_result

    def get_deployment_status(self) -> Dict[str, Any]:
        """Get deployment status."""
        return {
            "infrastructure_status": self.infrastructure_manager.get_infrastructure_status(),
            "deployment_history": self.deployment_history[-5:],  # Last 5 deployments
            "total_deployments": len(self.deployment_history),
            "current_environment": "production"
        }

    def rollback_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Rollback deployment."""
        rollback_result = {
            "deployment_id": deployment_id,
            "rollback_timestamp": time.time(),
            "resources_rolled_back": 0,
            "success": False
        }

        try:
            # Find deployment to rollback
            deployment_to_rollback = None
            for deployment in self.deployment_history:
                if deployment.get("deployment_id") == deployment_id:
                    deployment_to_rollback = deployment
                    break

            if not deployment_to_rollback:
                rollback_result["error"] = f"Deployment {deployment_id} not found"
                return rollback_result

            # Rollback infrastructure
            rollback_result["infrastructure_rollback"] = self.infrastructure_manager.destroy_infrastructure()

            rollback_result["success"] = rollback_result["infrastructure_rollback"].get("success", False)

        except Exception as e:
            rollback_result["error"] = str(e)

        return rollback_result


class InfrastructureAsCode:
    """Infrastructure as Code system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.templates: Dict[str, str] = {}
        self.generated_configs: Dict[str, str] = {}

    def define_infrastructure_template(self, template_name: str, template_code: str) -> bool:
        """Define infrastructure template."""
        try:
            self.templates[template_name] = template_code

            self.logger.info(f"Defined infrastructure template: {template_name}")
            return True

        except Exception as e:
            self.logger.error(f"Template definition failed: {e}")
            return False

    def generate_infrastructure_code(self, template_name: str, parameters: Dict[str, Any]) -> str:
        """Generate infrastructure code from template."""
        if template_name not in self.templates:
            return f"Template {template_name} not found"

        template = self.templates[template_name]
        generated_code = template

        # Replace parameters
        for param_name, param_value in parameters.items():
            generated_code = generated_code.replace(f"{{{param_name}}}", str(param_value))

        # Store generated code
        self.generated_configs[f"{template_name}_{int(time.time())}"] = generated_code

        return generated_code

    def validate_infrastructure_code(self, code: str) -> Dict[str, Any]:
        """Validate infrastructure code."""
        validation_result = {
            "valid": True,
            "syntax_errors": [],
            "semantic_errors": [],
            "warnings": []
        }

        try:
            # Basic syntax validation
            try:
                # Try to parse as JSON (for Terraform/Ansible style)
                parsed = json.loads(code)
                validation_result["parsed_structure"] = parsed
            except json.JSONDecodeError:
                # Try to parse as YAML
                try:
                    import yaml
                    parsed = yaml.safe_load(code)
                    validation_result["parsed_structure"] = parsed
                except ImportError:
                    validation_result["warnings"].append("YAML parser not available")
                except Exception:
                    validation_result["syntax_errors"].append("Could not parse infrastructure code")

        except Exception as e:
            validation_result["valid"] = False
            validation_result["syntax_errors"].append(str(e))

        return validation_result

    def get_template_statistics(self) -> Dict[str, Any]:
        """Get template statistics."""
        return {
            "total_templates": len(self.templates),
            "generated_configs": len(self.generated_configs),
            "template_names": list(self.templates.keys())
        }


class CADInfrastructureSystem:
    """Complete CAD infrastructure automation system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.terraform_manager = TerraformStyleManager()
        self.ansible_manager = AnsibleStyleConfiguration()
        self.infrastructure_manager = CADInfrastructureManager()
        self.iac_system = InfrastructureAsCode()
        self.deployment_history: List[Dict[str, Any]] = []

    def initialize_infrastructure_system(self) -> bool:
        """Initialize infrastructure system."""
        try:
            # Initialize all components
            if not self.infrastructure_manager.setup_cad_infrastructure():
                return False

            # Setup infrastructure as code templates
            self._setup_iac_templates()

            self.logger.info("Infrastructure system initialized")
            return True

        except Exception as e:
            self.logger.error(f"Infrastructure system initialization failed: {e}")
            return False

    def _setup_iac_templates(self) -> None:
        """Setup Infrastructure as Code templates."""
        # Docker Compose template
        docker_template = """
        version: '3.8'
        services:
          cad-service:
            image: cad-service:{{version}}
            ports:
              - "{{port}}:8080"
            environment:
              - CAD_ENV={{environment}}
            deploy:
              replicas: {{replicas}}
        """

        self.iac_system.define_infrastructure_template("docker_compose", docker_template)

        # Kubernetes deployment template
        k8s_template = """
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: cad-service
        spec:
          replicas: {{replicas}}
          selector:
            matchLabels:
              app: cad-service
          template:
            metadata:
              labels:
                app: cad-service
            spec:
              containers:
              - name: cad-service
                image: cad-service:{{version}}
                ports:
                - containerPort: 8080
        """

        self.iac_system.define_infrastructure_template("kubernetes_deployment", k8s_template)

    def deploy_cad_infrastructure(self, target_environment: str = "production") -> Dict[str, Any]:
        """Deploy CAD infrastructure."""
        deployment_result = {
            "target_environment": target_environment,
            "deployment_timestamp": time.time(),
            "terraform_deployment": {},
            "ansible_deployment": {},
            "iac_generation": {},
            "overall_success": True
        }

        try:
            # Generate Infrastructure as Code
            docker_config = self.iac_system.generate_infrastructure_code(
                "docker_compose",
                {"version": "latest", "port": 8080, "environment": target_environment, "replicas": 2}
            )
            deployment_result["iac_generation"]["docker_compose"] = "generated"

            k8s_config = self.iac_system.generate_infrastructure_code(
                "kubernetes_deployment",
                {"version": "latest", "replicas": 3}
            )
            deployment_result["iac_generation"]["kubernetes_deployment"] = "generated"

            # Deploy infrastructure
            infra_result = self.infrastructure_manager.deploy_cad_services()
            deployment_result["terraform_deployment"] = infra_result

            # Deploy configuration
            config_result = self.ansible_manager.execute_playbook("cad_service")
            deployment_result["ansible_deployment"] = config_result

            # Overall success
            deployment_result["overall_success"] = (
                infra_result.get("success", False) and
                config_result.get("success", False)
            )

            # Record deployment
            self.deployment_history.append(deployment_result)

        except Exception as e:
            deployment_result["overall_success"] = False
            deployment_result["error"] = str(e)

        return deployment_result

    def get_infrastructure_overview(self) -> Dict[str, Any]:
        """Get infrastructure overview."""
        return {
            "terraform": {
                "plans": len(self.terraform_manager.plans),
                "providers": list(self.terraform_manager.providers.keys())
            },
            "ansible": self.ansible_manager.get_configuration_status(),
            "infrastructure_manager": self.infrastructure_manager.get_infrastructure_status(),
            "iac_system": self.iac_system.get_template_statistics(),
            "deployment_history": self.deployment_history[-3:],  # Last 3 deployments
            "system_health": "healthy"
        }

    def scale_infrastructure(self, service_name: str, scale_factor: int) -> Dict[str, Any]:
        """Scale infrastructure."""
        scale_result = {
            "service_name": service_name,
            "scale_factor": scale_factor,
            "scaling_timestamp": time.time(),
            "scaled_resources": 0,
            "success": True
        }

        try:
            # Find and scale resources
            for plan_id, plan in self.terraform_manager.plans.items():
                for resource_name, resource in plan.resources.items():
                    if service_name in resource_name:
                        # Scale resource
                        original_config = resource.configuration.copy()

                        if "replicas" in resource.configuration:
                            resource.configuration["replicas"] *= scale_factor
                            scale_result["scaled_resources"] += 1

                        self.logger.info(f"Scaled {resource_name} by factor {scale_factor}")

            if scale_result["scaled_resources"] == 0:
                scale_result["success"] = False
                scale_result["error"] = f"No resources found for service {service_name}"

        except Exception as e:
            scale_result["success"] = False
            scale_result["error"] = str(e)

        return scale_result


# Factory functions
def create_terraform_manager() -> TerraformStyleManager:
    """Create Terraform-style manager."""
    return TerraformStyleManager()


def create_ansible_manager() -> AnsibleStyleConfiguration:
    """Create Ansible-style configuration manager."""
    return AnsibleStyleConfiguration()


def create_infrastructure_manager() -> CADInfrastructureManager:
    """Create CAD infrastructure manager."""
    return CADInfrastructureManager()


def create_iac_system() -> InfrastructureAsCode:
    """Create Infrastructure as Code system."""
    return InfrastructureAsCode()


def create_infrastructure_system() -> CADInfrastructureSystem:
    """Create complete infrastructure automation system."""
    return CADInfrastructureSystem()
