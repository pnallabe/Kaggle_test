"""
Infrastructure as Code (Terraform) Module

This module provides comprehensive Terraform infrastructure automation including:
- Multi-tenant infrastructure provisioning
- Secure, repeatable deployments
- Environment management (dev, staging, prod)
- Resource tagging and organization
- State management and backend configuration
- Security best practices enforcement
"""

import json
import logging
import os
import subprocess
import tempfile
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Environment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"


class ResourceType(Enum):
    """Types of infrastructure resources"""
    PROJECT = "project"
    VPC = "vpc"
    SUBNET = "subnet"
    FIREWALL = "firewall"
    COMPUTE = "compute"
    STORAGE = "storage"
    DATABASE = "database"
    BIGQUERY = "bigquery"
    CLOUD_RUN = "cloud_run"
    CLOUD_FUNCTIONS = "cloud_functions"
    LOAD_BALANCER = "load_balancer"
    DNS = "dns"
    SSL_CERTIFICATE = "ssl_certificate"
    IAM = "iam"
    SECRETS = "secrets"
    MONITORING = "monitoring"
    LOGGING = "logging"


class DeploymentStatus(Enum):
    """Deployment status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class TerraformResource:
    """Terraform resource definition"""
    resource_type: str
    resource_name: str
    provider: str
    configuration: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class TerraformModule:
    """Terraform module definition"""
    name: str
    source: str
    version: Optional[str]
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)


@dataclass
class InfrastructureTemplate:
    """Infrastructure template definition"""
    name: str
    description: str
    environment: Environment
    tenant_id: Optional[str]
    modules: List[TerraformModule] = field(default_factory=list)
    resources: List[TerraformResource] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)


@dataclass
class Deployment:
    """Deployment instance"""
    id: str
    template_name: str
    environment: Environment
    tenant_id: Optional[str]
    status: DeploymentStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    terraform_version: str
    state_location: str
    plan_output: Optional[str] = None
    apply_output: Optional[str] = None
    error_message: Optional[str] = None


class TerraformManager:
    """Terraform infrastructure management"""
    
    def __init__(self, project_id: str, state_bucket: str, templates_dir: str = "./terraform"):
        self.project_id = project_id
        self.state_bucket = state_bucket
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(exist_ok=True)
        
        # Terraform configuration
        self.terraform_version = "1.6.0"
        
        # Initialize templates
        self._create_base_templates()
        
        # Active deployments tracking
        self.deployments: Dict[str, Deployment] = {}
    
    def _create_base_templates(self):
        """Create base Terraform templates"""
        try:
            # Create base template structure
            base_templates = {
                "ai_analyst_platform": self._create_platform_template(),
                "tenant_infrastructure": self._create_tenant_template(),
                "monitoring_stack": self._create_monitoring_template(),
                "security_controls": self._create_security_template()
            }
            
            for template_name, template in base_templates.items():
                self._write_template_files(template_name, template)
            
            logger.info("Created base Terraform templates")
            
        except Exception as e:
            logger.error(f"Failed to create base templates: {e}")
            raise
    
    def _create_platform_template(self) -> InfrastructureTemplate:
        """Create AI Data Analyst platform template"""
        return InfrastructureTemplate(
            name="ai_analyst_platform",
            description="Core AI Data Analyst platform infrastructure",
            environment=Environment.PRODUCTION,
            tenant_id=None,
            modules=[
                TerraformModule(
                    name="vpc",
                    source="terraform-google-modules/network/google",
                    version="~> 7.0",
                    inputs={
                        "project_id": "${var.project_id}",
                        "network_name": "ai-analyst-vpc",
                        "subnets": [
                            {
                                "subnet_name": "ai-analyst-subnet",
                                "subnet_ip": "10.0.0.0/24",
                                "subnet_region": "${var.region}"
                            }
                        ]
                    }
                ),
                TerraformModule(
                    name="cloud_run",
                    source="terraform-google-modules/cloud-run/google",
                    version="~> 0.9",
                    inputs={
                        "service_name": "ai-analyst-api",
                        "project_id": "${var.project_id}",
                        "location": "${var.region}",
                        "image": "${var.api_image}",
                        "env_vars": [
                            {
                                "name": "PROJECT_ID",
                                "value": "${var.project_id}"
                            }
                        ]
                    }
                )
            ],
            resources=[
                TerraformResource(
                    resource_type="google_bigquery_dataset",
                    resource_name="main_dataset",
                    provider="google",
                    configuration={
                        "dataset_id": "ai_analyst_data",
                        "project": "${var.project_id}",
                        "location": "${var.region}",
                        "description": "Main dataset for AI Data Analyst platform",
                        "delete_contents_on_destroy": False,
                        "access": [
                            {
                                "role": "OWNER",
                                "user_by_email": "${var.admin_email}"
                            }
                        ]
                    },
                    tags={
                        "environment": "production",
                        "component": "data"
                    }
                ),
                TerraformResource(
                    resource_type="google_storage_bucket",
                    resource_name="data_storage",
                    provider="google",
                    configuration={
                        "name": "${var.project_id}-ai-analyst-data",
                        "project": "${var.project_id}",
                        "location": "${var.region}",
                        "force_destroy": False,
                        "uniform_bucket_level_access": True,
                        "versioning": {
                            "enabled": True
                        },
                        "lifecycle_rule": [
                            {
                                "condition": {
                                    "age": 90
                                },
                                "action": {
                                    "type": "SetStorageClass",
                                    "storage_class": "NEARLINE"
                                }
                            }
                        ]
                    },
                    tags={
                        "environment": "production",
                        "component": "storage"
                    }
                )
            ],
            variables={
                "project_id": {
                    "description": "Google Cloud Project ID",
                    "type": "string"
                },
                "region": {
                    "description": "Google Cloud Region",
                    "type": "string",
                    "default": "us-central1"
                },
                "admin_email": {
                    "description": "Administrator email address",
                    "type": "string"
                },
                "api_image": {
                    "description": "Docker image for API service",
                    "type": "string"
                }
            },
            outputs={
                "vpc_network": "module.vpc.network_name",
                "cloud_run_url": "module.cloud_run.service_url",
                "bigquery_dataset": "google_bigquery_dataset.main_dataset.dataset_id",
                "storage_bucket": "google_storage_bucket.data_storage.name"
            }
        )
    
    def _create_tenant_template(self) -> InfrastructureTemplate:
        """Create tenant-specific infrastructure template"""
        return InfrastructureTemplate(
            name="tenant_infrastructure",
            description="Tenant-specific infrastructure with isolation",
            environment=Environment.PRODUCTION,
            tenant_id="${var.tenant_id}",
            resources=[
                TerraformResource(
                    resource_type="google_project",
                    resource_name="tenant_project",
                    provider="google",
                    configuration={
                        "name": "AI Analyst - Tenant ${var.tenant_id}",
                        "project_id": "${var.project_id}-tenant-${var.tenant_id}",
                        "org_id": "${var.organization_id}",
                        "billing_account": "${var.billing_account}",
                        "auto_create_network": False
                    },
                    tags={
                        "tenant_id": "${var.tenant_id}",
                        "environment": "production"
                    }
                ),
                TerraformResource(
                    resource_type="google_bigquery_dataset",
                    resource_name="tenant_dataset",
                    provider="google",
                    configuration={
                        "dataset_id": "tenant_${replace(var.tenant_id, \"-\", \"_\")}_data",
                        "project": "${google_project.tenant_project.project_id}",
                        "location": "${var.region}",
                        "description": "Dataset for tenant ${var.tenant_id}",
                        "delete_contents_on_destroy": False,
                        "access": [
                            {
                                "role": "OWNER",
                                "user_by_email": "${var.tenant_admin_email}"
                            },
                            {
                                "role": "READER",
                                "special_group": "projectReaders"
                            }
                        ]
                    },
                    depends_on=["google_project.tenant_project"],
                    tags={
                        "tenant_id": "${var.tenant_id}",
                        "component": "data"
                    }
                ),
                TerraformResource(
                    resource_type="google_storage_bucket",
                    resource_name="tenant_storage",
                    provider="google",
                    configuration={
                        "name": "${var.project_id}-tenant-${var.tenant_id}-data",
                        "project": "${google_project.tenant_project.project_id}",
                        "location": "${var.region}",
                        "force_destroy": False,
                        "uniform_bucket_level_access": True,
                        "versioning": {
                            "enabled": True
                        }
                    },
                    depends_on=["google_project.tenant_project"],
                    tags={
                        "tenant_id": "${var.tenant_id}",
                        "component": "storage"
                    }
                ),
                TerraformResource(
                    resource_type="google_project_iam_member",
                    resource_name="tenant_admin_iam",
                    provider="google",
                    configuration={
                        "project": "${google_project.tenant_project.project_id}",
                        "role": "roles/editor",
                        "member": "user:${var.tenant_admin_email}"
                    },
                    depends_on=["google_project.tenant_project"]
                )
            ],
            variables={
                "tenant_id": {
                    "description": "Unique tenant identifier",
                    "type": "string"
                },
                "project_id": {
                    "description": "Base project ID",
                    "type": "string"
                },
                "organization_id": {
                    "description": "Google Cloud Organization ID",
                    "type": "string"
                },
                "billing_account": {
                    "description": "Billing account ID",
                    "type": "string"
                },
                "tenant_admin_email": {
                    "description": "Tenant administrator email",
                    "type": "string"
                },
                "region": {
                    "description": "Google Cloud Region",
                    "type": "string",
                    "default": "us-central1"
                }
            },
            outputs={
                "tenant_project_id": "google_project.tenant_project.project_id",
                "tenant_dataset": "google_bigquery_dataset.tenant_dataset.dataset_id",
                "tenant_storage_bucket": "google_storage_bucket.tenant_storage.name"
            }
        )
    
    def _create_monitoring_template(self) -> InfrastructureTemplate:
        """Create monitoring and observability template"""
        return InfrastructureTemplate(
            name="monitoring_stack",
            description="Monitoring and observability infrastructure",
            environment=Environment.PRODUCTION,
            tenant_id=None,
            resources=[
                TerraformResource(
                    resource_type="google_monitoring_notification_channel",
                    resource_name="email_alerts",
                    provider="google",
                    configuration={
                        "display_name": "Email Alerts",
                        "type": "email",
                        "project": "${var.project_id}",
                        "labels": {
                            "email_address": "${var.alert_email}"
                        }
                    }
                ),
                TerraformResource(
                    resource_type="google_monitoring_alert_policy",
                    resource_name="high_error_rate",
                    provider="google",
                    configuration={
                        "display_name": "High Error Rate Alert",
                        "project": "${var.project_id}",
                        "enabled": True,
                        "conditions": [
                            {
                                "display_name": "Error rate > 5%",
                                "condition_threshold": {
                                    "filter": "resource.type=\"cloud_run_revision\"",
                                    "comparison": "COMPARISON_GREATER_THAN",
                                    "threshold_value": 0.05,
                                    "duration": "300s",
                                    "aggregations": [
                                        {
                                            "alignment_period": "300s",
                                            "per_series_aligner": "ALIGN_RATE",
                                            "cross_series_reducer": "REDUCE_MEAN",
                                            "group_by_fields": ["resource.label.service_name"]
                                        }
                                    ]
                                }
                            }
                        ],
                        "notification_channels": ["${google_monitoring_notification_channel.email_alerts.name}"]
                    },
                    depends_on=["google_monitoring_notification_channel.email_alerts"]
                ),
                TerraformResource(
                    resource_type="google_bigquery_dataset",
                    resource_name="monitoring_dataset",
                    provider="google",
                    configuration={
                        "dataset_id": "monitoring_data",
                        "project": "${var.project_id}",
                        "location": "${var.region}",
                        "description": "Monitoring and audit data",
                        "delete_contents_on_destroy": False
                    }
                )
            ],
            variables={
                "project_id": {
                    "description": "Google Cloud Project ID",
                    "type": "string"
                },
                "region": {
                    "description": "Google Cloud Region",
                    "type": "string",
                    "default": "us-central1"
                },
                "alert_email": {
                    "description": "Email for monitoring alerts",
                    "type": "string"
                }
            },
            outputs={
                "notification_channel": "google_monitoring_notification_channel.email_alerts.name",
                "monitoring_dataset": "google_bigquery_dataset.monitoring_dataset.dataset_id"
            }
        )
    
    def _create_security_template(self) -> InfrastructureTemplate:
        """Create security controls template"""
        return InfrastructureTemplate(
            name="security_controls",
            description="Security controls and compliance infrastructure",
            environment=Environment.PRODUCTION,
            tenant_id=None,
            resources=[
                TerraformResource(
                    resource_type="google_kms_key_ring",
                    resource_name="main_keyring",
                    provider="google",
                    configuration={
                        "name": "ai-analyst-keys",
                        "project": "${var.project_id}",
                        "location": "${var.region}"
                    }
                ),
                TerraformResource(
                    resource_type="google_kms_crypto_key",
                    resource_name="data_encryption_key",
                    provider="google",
                    configuration={
                        "name": "data-encryption",
                        "key_ring": "${google_kms_key_ring.main_keyring.id}",
                        "purpose": "ENCRYPT_DECRYPT",
                        "rotation_period": "7776000s"  # 90 days
                    },
                    depends_on=["google_kms_key_ring.main_keyring"]
                ),
                TerraformResource(
                    resource_type="google_secret_manager_secret",
                    resource_name="jwt_secret",
                    provider="google",
                    configuration={
                        "secret_id": "jwt-signing-key",
                        "project": "${var.project_id}",
                        "labels": {
                            "component": "authentication"
                        },
                        "replication": {
                            "automatic": True
                        }
                    }
                ),
                TerraformResource(
                    resource_type="google_logging_project_sink",
                    resource_name="audit_sink",
                    provider="google",
                    configuration={
                        "name": "audit-logs-sink",
                        "project": "${var.project_id}",
                        "destination": "bigquery.googleapis.com/projects/${var.project_id}/datasets/audit_logs",
                        "filter": "protoPayload.@type=\"type.googleapis.com/google.cloud.audit.AuditLog\"",
                        "unique_writer_identity": True
                    }
                )
            ],
            variables={
                "project_id": {
                    "description": "Google Cloud Project ID",
                    "type": "string"
                },
                "region": {
                    "description": "Google Cloud Region",
                    "type": "string",
                    "default": "us-central1"
                }
            },
            outputs={
                "kms_key_ring": "google_kms_key_ring.main_keyring.name",
                "encryption_key": "google_kms_crypto_key.data_encryption_key.name",
                "audit_sink": "google_logging_project_sink.audit_sink.name"
            }
        )
    
    def _write_template_files(self, template_name: str, template: InfrastructureTemplate):
        """Write Terraform template files to disk"""
        try:
            template_dir = self.templates_dir / template_name
            template_dir.mkdir(exist_ok=True)
            
            # Write main.tf
            main_tf = self._generate_main_tf(template)
            with open(template_dir / "main.tf", "w") as f:
                f.write(main_tf)
            
            # Write variables.tf
            variables_tf = self._generate_variables_tf(template)
            with open(template_dir / "variables.tf", "w") as f:
                f.write(variables_tf)
            
            # Write outputs.tf
            outputs_tf = self._generate_outputs_tf(template)
            with open(template_dir / "outputs.tf", "w") as f:
                f.write(outputs_tf)
            
            # Write terraform.tf (backend configuration)
            backend_tf = self._generate_backend_tf()
            with open(template_dir / "terraform.tf", "w") as f:
                f.write(backend_tf)
            
            # Write terraform.tfvars.example
            tfvars_example = self._generate_tfvars_example(template)
            with open(template_dir / "terraform.tfvars.example", "w") as f:
                f.write(tfvars_example)
            
            logger.debug(f"Generated Terraform files for template: {template_name}")
            
        except Exception as e:
            logger.error(f"Failed to write template files for {template_name}: {e}")
            raise
    
    def _generate_main_tf(self, template: InfrastructureTemplate) -> str:
        """Generate main.tf content"""
        content = []
        
        # Add provider configuration
        content.append("""
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}
""")
        
        # Add modules
        for module in template.modules:
            module_block = f"""
module "{module.name}" {{
  source = "{module.source}"
"""
            if module.version:
                module_block += f'  version = "{module.version}"\n'
            
            for key, value in module.inputs.items():
                if isinstance(value, str):
                    module_block += f'  {key} = "{value}"\n'
                elif isinstance(value, (int, float, bool)):
                    module_block += f'  {key} = {str(value).lower()}\n'
                else:
                    # Handle complex types (lists, maps)
                    module_block += f'  {key} = {json.dumps(value, indent=2)}\n'
            
            module_block += "}\n"
            content.append(module_block)
        
        # Add resources
        for resource in template.resources:
            resource_block = f"""
resource "{resource.resource_type}" "{resource.resource_name}" {{
"""
            for key, value in resource.configuration.items():
                if isinstance(value, str):
                    resource_block += f'  {key} = "{value}"\n'
                elif isinstance(value, (int, float, bool)):
                    resource_block += f'  {key} = {str(value).lower()}\n'
                elif isinstance(value, list):
                    if key == "depends_on":
                        deps = ", ".join([f'"{dep}"' for dep in value])
                        resource_block += f'  depends_on = [{deps}]\n'
                    else:
                        resource_block += f'  {key} = {json.dumps(value, indent=2)}\n'
                elif isinstance(value, dict):
                    resource_block += f'  {key} {{\n'
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, str):
                            resource_block += f'    {sub_key} = "{sub_value}"\n'
                        else:
                            resource_block += f'    {sub_key} = {json.dumps(sub_value)}\n'
                    resource_block += '  }\n'
            
            # Add tags as labels
            if resource.tags:
                resource_block += '  labels = {\n'
                for tag_key, tag_value in resource.tags.items():
                    resource_block += f'    {tag_key} = "{tag_value}"\n'
                resource_block += '  }\n'
            
            # Add depends_on if specified
            if resource.depends_on:
                deps = ", ".join(resource.depends_on)
                resource_block += f'  depends_on = [{deps}]\n'
            
            resource_block += "}\n"
            content.append(resource_block)
        
        return "\n".join(content)
    
    def _generate_variables_tf(self, template: InfrastructureTemplate) -> str:
        """Generate variables.tf content"""
        content = []
        
        for var_name, var_config in template.variables.items():
            var_block = f"""
variable "{var_name}" {{
  description = "{var_config.get('description', '')}"
  type        = {var_config.get('type', 'string')}
"""
            if 'default' in var_config:
                if isinstance(var_config['default'], str):
                    var_block += f'  default     = "{var_config["default"]}"\n'
                else:
                    var_block += f'  default     = {json.dumps(var_config["default"])}\n'
            
            var_block += "}\n"
            content.append(var_block)
        
        return "\n".join(content)
    
    def _generate_outputs_tf(self, template: InfrastructureTemplate) -> str:
        """Generate outputs.tf content"""
        content = []
        
        for output_name, output_value in template.outputs.items():
            output_block = f"""
output "{output_name}" {{
  description = "Output for {output_name}"
  value       = {output_value}
}}
"""
            content.append(output_block)
        
        return "\n".join(content)
    
    def _generate_backend_tf(self) -> str:
        """Generate backend configuration"""
        return f"""
terraform {{
  backend "gcs" {{
    bucket = "{self.state_bucket}"
    prefix = "terraform/state"
  }}
}}
"""
    
    def _generate_tfvars_example(self, template: InfrastructureTemplate) -> str:
        """Generate terraform.tfvars.example"""
        content = []
        
        for var_name, var_config in template.variables.items():
            comment = f"# {var_config.get('description', '')}"
            content.append(comment)
            
            if 'default' in var_config:
                value = var_config['default']
            else:
                # Generate example values based on type
                var_type = var_config.get('type', 'string')
                if var_type == 'string':
                    value = f"example_{var_name}"
                elif var_type == 'number':
                    value = 1
                elif var_type == 'bool':
                    value = True
                else:
                    value = "example_value"
            
            if isinstance(value, str):
                content.append(f'{var_name} = "{value}"')
            else:
                content.append(f'{var_name} = {json.dumps(value)}')
            
            content.append("")  # Empty line
        
        return "\n".join(content)
    
    def plan_deployment(self, template_name: str, environment: Environment,
                       variables: Dict[str, Any], tenant_id: Optional[str] = None) -> str:
        """Plan Terraform deployment"""
        try:
            deployment_id = str(uuid.uuid4())
            
            # Create deployment record
            deployment = Deployment(
                id=deployment_id,
                template_name=template_name,
                environment=environment,
                tenant_id=tenant_id,
                status=DeploymentStatus.PENDING,
                created_at=datetime.utcnow(),
                started_at=None,
                completed_at=None,
                terraform_version=self.terraform_version,
                state_location=f"gs://{self.state_bucket}/terraform/state/{template_name}-{environment.value}"
            )
            
            if tenant_id:
                deployment.state_location += f"-{tenant_id}"
            
            self.deployments[deployment_id] = deployment
            
            # Run terraform plan
            plan_output = self._run_terraform_plan(template_name, variables, deployment)
            deployment.plan_output = plan_output
            
            logger.info(f"Generated deployment plan: {deployment_id}")
            return deployment_id
            
        except Exception as e:
            logger.error(f"Failed to plan deployment: {e}")
            if deployment_id in self.deployments:
                self.deployments[deployment_id].status = DeploymentStatus.FAILED
                self.deployments[deployment_id].error_message = str(e)
            raise
    
    def apply_deployment(self, deployment_id: str) -> bool:
        """Apply Terraform deployment"""
        try:
            if deployment_id not in self.deployments:
                raise ValueError(f"Deployment not found: {deployment_id}")
            
            deployment = self.deployments[deployment_id]
            deployment.status = DeploymentStatus.RUNNING
            deployment.started_at = datetime.utcnow()
            
            # Run terraform apply
            apply_output = self._run_terraform_apply(deployment)
            deployment.apply_output = apply_output
            deployment.status = DeploymentStatus.COMPLETED
            deployment.completed_at = datetime.utcnow()
            
            logger.info(f"Completed deployment: {deployment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply deployment {deployment_id}: {e}")
            if deployment_id in self.deployments:
                self.deployments[deployment_id].status = DeploymentStatus.FAILED
                self.deployments[deployment_id].error_message = str(e)
            return False
    
    def _run_terraform_plan(self, template_name: str, variables: Dict[str, Any],
                           deployment: Deployment) -> str:
        """Run terraform plan command"""
        try:
            template_dir = self.templates_dir / template_name
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.tfvars', delete=False) as f:
                for key, value in variables.items():
                    if isinstance(value, str):
                        f.write(f'{key} = "{value}"\n')
                    else:
                        f.write(f'{key} = {json.dumps(value)}\n')
                
                tfvars_file = f.name
            
            # Run terraform init
            init_cmd = ["terraform", "init", "-upgrade"]
            subprocess.run(init_cmd, cwd=template_dir, check=True, 
                         capture_output=True, text=True)
            
            # Run terraform plan
            plan_cmd = [
                "terraform", "plan",
                f"-var-file={tfvars_file}",
                "-detailed-exitcode",
                "-out=tfplan"
            ]
            
            result = subprocess.run(plan_cmd, cwd=template_dir, 
                                  capture_output=True, text=True)
            
            # Clean up tfvars file
            os.unlink(tfvars_file)
            
            return result.stdout + result.stderr
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Terraform plan failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to run terraform plan: {e}")
            raise
    
    def _run_terraform_apply(self, deployment: Deployment) -> str:
        """Run terraform apply command"""
        try:
            template_dir = self.templates_dir / deployment.template_name
            
            # Run terraform apply
            apply_cmd = ["terraform", "apply", "-auto-approve", "tfplan"]
            
            result = subprocess.run(apply_cmd, cwd=template_dir,
                                  capture_output=True, text=True, check=True)
            
            return result.stdout + result.stderr
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Terraform apply failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to run terraform apply: {e}")
            raise
    
    def destroy_deployment(self, deployment_id: str) -> bool:
        """Destroy Terraform deployment"""
        try:
            if deployment_id not in self.deployments:
                raise ValueError(f"Deployment not found: {deployment_id}")
            
            deployment = self.deployments[deployment_id]
            template_dir = self.templates_dir / deployment.template_name
            
            # Run terraform destroy
            destroy_cmd = ["terraform", "destroy", "-auto-approve"]
            
            result = subprocess.run(destroy_cmd, cwd=template_dir,
                                  capture_output=True, text=True, check=True)
            
            logger.info(f"Destroyed deployment: {deployment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to destroy deployment {deployment_id}: {e}")
            return False
    
    def get_deployment_status(self, deployment_id: str) -> Optional[Deployment]:
        """Get deployment status"""
        return self.deployments.get(deployment_id)
    
    def list_deployments(self, environment: Optional[Environment] = None,
                        tenant_id: Optional[str] = None) -> List[Deployment]:
        """List deployments with optional filtering"""
        deployments = list(self.deployments.values())
        
        if environment:
            deployments = [d for d in deployments if d.environment == environment]
        
        if tenant_id:
            deployments = [d for d in deployments if d.tenant_id == tenant_id]
        
        return deployments


class TenantInfrastructureManager:
    """Tenant-specific infrastructure management"""
    
    def __init__(self, terraform_manager: TerraformManager, tenant_id: str):
        self.terraform_manager = terraform_manager
        self.tenant_id = tenant_id
    
    def provision_tenant_infrastructure(self, tenant_config: Dict[str, Any]) -> str:
        """Provision complete infrastructure for tenant"""
        try:
            # Prepare variables for tenant infrastructure
            variables = {
                "tenant_id": self.tenant_id,
                "project_id": self.terraform_manager.project_id,
                "organization_id": tenant_config.get("organization_id"),
                "billing_account": tenant_config.get("billing_account"),
                "tenant_admin_email": tenant_config.get("admin_email"),
                "region": tenant_config.get("region", "us-central1")
            }
            
            # Plan deployment
            deployment_id = self.terraform_manager.plan_deployment(
                template_name="tenant_infrastructure",
                environment=Environment.PRODUCTION,
                variables=variables,
                tenant_id=self.tenant_id
            )
            
            # Apply deployment
            success = self.terraform_manager.apply_deployment(deployment_id)
            
            if success:
                logger.info(f"Provisioned infrastructure for tenant: {self.tenant_id}")
            else:
                logger.error(f"Failed to provision infrastructure for tenant: {self.tenant_id}")
            
            return deployment_id
            
        except Exception as e:
            logger.error(f"Failed to provision tenant infrastructure: {e}")
            raise
    
    def setup_tenant_monitoring(self) -> str:
        """Setup monitoring for tenant"""
        try:
            variables = {
                "project_id": f"{self.terraform_manager.project_id}-tenant-{self.tenant_id}",
                "region": "us-central1",
                "alert_email": f"admin@tenant-{self.tenant_id}.com"
            }
            
            deployment_id = self.terraform_manager.plan_deployment(
                template_name="monitoring_stack",
                environment=Environment.PRODUCTION,
                variables=variables,
                tenant_id=self.tenant_id
            )
            
            self.terraform_manager.apply_deployment(deployment_id)
            
            logger.info(f"Setup monitoring for tenant: {self.tenant_id}")
            return deployment_id
            
        except Exception as e:
            logger.error(f"Failed to setup tenant monitoring: {e}")
            raise
    
    def deprovision_tenant_infrastructure(self) -> bool:
        """Deprovision tenant infrastructure"""
        try:
            # Find tenant deployments
            tenant_deployments = self.terraform_manager.list_deployments(
                tenant_id=self.tenant_id
            )
            
            success = True
            for deployment in tenant_deployments:
                if not self.terraform_manager.destroy_deployment(deployment.id):
                    success = False
            
            if success:
                logger.info(f"Deprovisioned infrastructure for tenant: {self.tenant_id}")
            else:
                logger.error(f"Failed to fully deprovision tenant: {self.tenant_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to deprovision tenant infrastructure: {e}")
            return False


# Example usage
if __name__ == "__main__":
    # Initialize Terraform manager
    terraform_manager = TerraformManager(
        project_id="ai-data-analyst-project",
        state_bucket="ai-analyst-terraform-state",
        templates_dir="./terraform"
    )
    
    # Initialize tenant infrastructure manager
    tenant_manager = TenantInfrastructureManager(terraform_manager, "tenant-123")
    
    # Provision tenant infrastructure
    deployment_id = tenant_manager.provision_tenant_infrastructure({
        "organization_id": "123456789",
        "billing_account": "billing-account-123",
        "admin_email": "admin@tenant-123.com",
        "region": "us-central1"
    })
    
    # Setup monitoring
    monitoring_deployment = tenant_manager.setup_tenant_monitoring()
    
    # Check deployment status
    deployment = terraform_manager.get_deployment_status(deployment_id)
    print(f"Deployment status: {deployment.status if deployment else 'Not found'}")
    
    # List all deployments
    deployments = terraform_manager.list_deployments()
    print(f"Total deployments: {len(deployments)}")
    
    for deployment in deployments:
        print(f"- {deployment.template_name} ({deployment.environment.value}): {deployment.status.value}")