"""
VPC Service Controls Configuration Module

This module implements Google Cloud VPC Service Controls for:
- Data exfiltration protection
- Network security boundaries
- Service perimeter enforcement
- Cross-tenant isolation
- Compliance controls
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from google.cloud import accesscontextmanager_v1
from google.cloud import resourcemanager_v3
import google.auth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerimeterType(Enum):
    """VPC Service Controls perimeter types"""
    REGULAR = "regular"
    BRIDGE = "bridge"


class ServiceRestriction(Enum):
    """Restricted services for VPC Service Controls"""
    BIGQUERY = "bigquery.googleapis.com"
    STORAGE = "storage.googleapis.com"
    CLOUDSQL = "sql-component.googleapis.com"
    DATAFLOW = "dataflow.googleapis.com"
    AI_PLATFORM = "ml.googleapis.com"
    VERTEX_AI = "aiplatform.googleapis.com"
    CLOUD_FUNCTIONS = "cloudfunctions.googleapis.com"
    CLOUD_RUN = "run.googleapis.com"
    PUBSUB = "pubsub.googleapis.com"
    LOGGING = "logging.googleapis.com"
    MONITORING = "monitoring.googleapis.com"


@dataclass
class AccessLevel:
    """Access level configuration for VPC Service Controls"""
    name: str
    title: str
    description: str
    ip_ranges: List[str]
    regions: List[str]
    required_access_levels: List[str] = None
    device_policy: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.required_access_levels is None:
            self.required_access_levels = []


@dataclass
class ServicePerimeter:
    """Service perimeter configuration"""
    name: str
    title: str
    description: str
    perimeter_type: PerimeterType
    projects: List[str]
    restricted_services: List[ServiceRestriction]
    access_levels: List[str]
    vpc_accessible_services: List[str] = None
    ingress_policies: List[Dict[str, Any]] = None
    egress_policies: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.vpc_accessible_services is None:
            self.vpc_accessible_services = []
        if self.ingress_policies is None:
            self.ingress_policies = []
        if self.egress_policies is None:
            self.egress_policies = []


class VPCServiceControlsManager:
    """Manager for VPC Service Controls configuration"""
    
    def __init__(self, organization_id: str, policy_id: str):
        self.organization_id = organization_id
        self.policy_id = policy_id
        self.client = accesscontextmanager_v1.AccessContextManagerClient()
        self.resource_manager = resourcemanager_v3.ProjectsClient()
        
        # Policy path
        self.policy_path = f"accessPolicies/{policy_id}"
    
    def create_access_level(self, access_level: AccessLevel) -> str:
        """Create an access level for VPC Service Controls"""
        try:
            # Build access level configuration
            basic_level = accesscontextmanager_v1.BasicLevel()
            
            # Configure conditions
            conditions = []
            
            # IP ranges condition
            if access_level.ip_ranges:
                condition = accesscontextmanager_v1.Condition()
                condition.ip_subnetworks = access_level.ip_ranges
                conditions.append(condition)
            
            # Regions condition
            if access_level.regions:
                condition = accesscontextmanager_v1.Condition()
                condition.regions = access_level.regions
                conditions.append(condition)
            
            # Device policy condition
            if access_level.device_policy:
                condition = accesscontextmanager_v1.Condition()
                condition.device_policy = accesscontextmanager_v1.DevicePolicy(**access_level.device_policy)
                conditions.append(condition)
            
            basic_level.conditions = conditions
            
            # Create access level request
            access_level_resource = accesscontextmanager_v1.AccessLevel()
            access_level_resource.name = f"{self.policy_path}/accessLevels/{access_level.name}"
            access_level_resource.title = access_level.title
            access_level_resource.description = access_level.description
            access_level_resource.basic = basic_level
            
            # Create the access level
            operation = self.client.create_access_level(
                parent=self.policy_path,
                access_level=access_level_resource
            )
            
            # Wait for operation to complete
            result = operation.result()
            
            logger.info(f"Created access level: {access_level.name}")
            return result.name
            
        except Exception as e:
            logger.error(f"Failed to create access level {access_level.name}: {e}")
            raise
    
    def create_service_perimeter(self, perimeter: ServicePerimeter) -> str:
        """Create a service perimeter for VPC Service Controls"""
        try:
            # Build service perimeter configuration
            perimeter_resource = accesscontextmanager_v1.ServicePerimeter()
            perimeter_resource.name = f"{self.policy_path}/servicePerimeters/{perimeter.name}"
            perimeter_resource.title = perimeter.title
            perimeter_resource.description = perimeter.description
            perimeter_resource.perimeter_type = (
                accesscontextmanager_v1.ServicePerimeter.PerimeterType.PERIMETER_TYPE_REGULAR
                if perimeter.perimeter_type == PerimeterType.REGULAR
                else accesscontextmanager_v1.ServicePerimeter.PerimeterType.PERIMETER_TYPE_BRIDGE
            )
            
            # Configure status
            status = accesscontextmanager_v1.ServicePerimeterConfig()
            status.resources = [f"projects/{project}" for project in perimeter.projects]
            status.restricted_services = [service.value for service in perimeter.restricted_services]
            status.access_levels = [f"{self.policy_path}/accessLevels/{level}" for level in perimeter.access_levels]
            
            # VPC accessible services
            if perimeter.vpc_accessible_services:
                vpc_config = accesscontextmanager_v1.VpcAccessibleServices()
                vpc_config.enable_restriction = True
                vpc_config.allowed_services = perimeter.vpc_accessible_services
                status.vpc_accessible_services = vpc_config
            
            # Ingress policies
            if perimeter.ingress_policies:
                ingress_policies = []
                for policy in perimeter.ingress_policies:
                    ingress_policy = accesscontextmanager_v1.IngressPolicy()
                    # Configure ingress policy details
                    ingress_policies.append(ingress_policy)
                status.ingress_policies = ingress_policies
            
            # Egress policies
            if perimeter.egress_policies:
                egress_policies = []
                for policy in perimeter.egress_policies:
                    egress_policy = accesscontextmanager_v1.EgressPolicy()
                    # Configure egress policy details
                    egress_policies.append(egress_policy)
                status.egress_policies = egress_policies
            
            perimeter_resource.status = status
            
            # Create the service perimeter
            operation = self.client.create_service_perimeter(
                parent=self.policy_path,
                service_perimeter=perimeter_resource
            )
            
            # Wait for operation to complete
            result = operation.result()
            
            logger.info(f"Created service perimeter: {perimeter.name}")
            return result.name
            
        except Exception as e:
            logger.error(f"Failed to create service perimeter {perimeter.name}: {e}")
            raise
    
    def create_tenant_perimeter(self, tenant_id: str, tenant_projects: List[str],
                              allowed_regions: List[str] = None) -> Dict[str, str]:
        """Create isolated service perimeter for a tenant"""
        if allowed_regions is None:
            allowed_regions = ["us-central1", "us-east1"]
        
        # Create access level for tenant
        access_level = AccessLevel(
            name=f"tenant_{tenant_id}_access",
            title=f"Tenant {tenant_id} Access Level",
            description=f"Access level for tenant {tenant_id} with regional restrictions",
            ip_ranges=[],  # Can be configured per tenant
            regions=allowed_regions,
            device_policy={
                "require_screen_lock": True,
                "require_admin_approval": False,
                "os_constraints": [
                    {
                        "os_type": "DESKTOP_WINDOWS",
                        "minimum_version": "10.0.0"
                    },
                    {
                        "os_type": "DESKTOP_MAC",
                        "minimum_version": "10.15.0"
                    }
                ]
            }
        )
        
        access_level_name = self.create_access_level(access_level)
        
        # Create service perimeter for tenant
        perimeter = ServicePerimeter(
            name=f"tenant_{tenant_id}_perimeter",
            title=f"Tenant {tenant_id} Service Perimeter",
            description=f"Service perimeter for tenant {tenant_id} with data exfiltration protection",
            perimeter_type=PerimeterType.REGULAR,
            projects=tenant_projects,
            restricted_services=[
                ServiceRestriction.BIGQUERY,
                ServiceRestriction.STORAGE,
                ServiceRestriction.VERTEX_AI,
                ServiceRestriction.CLOUD_FUNCTIONS,
                ServiceRestriction.CLOUD_RUN
            ],
            access_levels=[f"tenant_{tenant_id}_access"],
            vpc_accessible_services=[
                "bigquery.googleapis.com",
                "storage.googleapis.com",
                "aiplatform.googleapis.com",
                "logging.googleapis.com",
                "monitoring.googleapis.com"
            ],
            ingress_policies=[
                {
                    "ingress_from": {
                        "sources": [
                            {
                                "access_level": access_level_name
                            }
                        ]
                    },
                    "ingress_to": {
                        "operations": [
                            {
                                "service_name": "bigquery.googleapis.com",
                                "method_selectors": [
                                    {"method": "google.cloud.bigquery.v2.JobService.Query"},
                                    {"method": "google.cloud.bigquery.v2.TableService.GetTable"}
                                ]
                            }
                        ]
                    }
                }
            ],
            egress_policies=[
                {
                    "egress_from": {
                        "identity_type": "ANY_IDENTITY"
                    },
                    "egress_to": {
                        "operations": [
                            {
                                "service_name": "logging.googleapis.com"
                            },
                            {
                                "service_name": "monitoring.googleapis.com"
                            }
                        ]
                    }
                }
            ]
        )
        
        perimeter_name = self.create_service_perimeter(perimeter)
        
        return {
            "access_level": access_level_name,
            "service_perimeter": perimeter_name
        }
    
    def update_perimeter_projects(self, perimeter_name: str, projects: List[str]):
        """Update projects in a service perimeter"""
        try:
            # Get current perimeter
            perimeter_path = f"{self.policy_path}/servicePerimeters/{perimeter_name}"
            perimeter = self.client.get_service_perimeter(name=perimeter_path)
            
            # Update projects
            perimeter.status.resources = [f"projects/{project}" for project in projects]
            
            # Update the perimeter
            operation = self.client.update_service_perimeter(service_perimeter=perimeter)
            result = operation.result()
            
            logger.info(f"Updated perimeter projects: {perimeter_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update perimeter projects: {e}")
            raise
    
    def add_ingress_policy(self, perimeter_name: str, policy: Dict[str, Any]):
        """Add ingress policy to service perimeter"""
        try:
            # Get current perimeter
            perimeter_path = f"{self.policy_path}/servicePerimeters/{perimeter_name}"
            perimeter = self.client.get_service_perimeter(name=perimeter_path)
            
            # Add ingress policy
            ingress_policy = accesscontextmanager_v1.IngressPolicy()
            # Configure policy from dict
            
            if not perimeter.status.ingress_policies:
                perimeter.status.ingress_policies = []
            
            perimeter.status.ingress_policies.append(ingress_policy)
            
            # Update the perimeter
            operation = self.client.update_service_perimeter(service_perimeter=perimeter)
            result = operation.result()
            
            logger.info(f"Added ingress policy to perimeter: {perimeter_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to add ingress policy: {e}")
            raise
    
    def get_perimeter_status(self, perimeter_name: str) -> Dict[str, Any]:
        """Get status of a service perimeter"""
        try:
            perimeter_path = f"{self.policy_path}/servicePerimeters/{perimeter_name}"
            perimeter = self.client.get_service_perimeter(name=perimeter_path)
            
            return {
                "name": perimeter.name,
                "title": perimeter.title,
                "perimeter_type": perimeter.perimeter_type,
                "projects": perimeter.status.resources,
                "restricted_services": perimeter.status.restricted_services,
                "access_levels": perimeter.status.access_levels,
                "vpc_accessible_services": (
                    perimeter.status.vpc_accessible_services.allowed_services
                    if perimeter.status.vpc_accessible_services
                    else []
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to get perimeter status: {e}")
            raise
    
    def delete_service_perimeter(self, perimeter_name: str):
        """Delete a service perimeter"""
        try:
            perimeter_path = f"{self.policy_path}/servicePerimeters/{perimeter_name}"
            operation = self.client.delete_service_perimeter(name=perimeter_path)
            operation.result()
            
            logger.info(f"Deleted service perimeter: {perimeter_name}")
            
        except Exception as e:
            logger.error(f"Failed to delete service perimeter: {e}")
            raise
    
    def list_service_perimeters(self) -> List[Dict[str, Any]]:
        """List all service perimeters in the policy"""
        try:
            perimeters = []
            
            for perimeter in self.client.list_service_perimeters(parent=self.policy_path):
                perimeters.append({
                    "name": perimeter.name,
                    "title": perimeter.title,
                    "description": perimeter.description,
                    "perimeter_type": perimeter.perimeter_type,
                    "projects": perimeter.status.resources if perimeter.status else [],
                    "restricted_services": perimeter.status.restricted_services if perimeter.status else []
                })
            
            return perimeters
            
        except Exception as e:
            logger.error(f"Failed to list service perimeters: {e}")
            raise


class VPCControlsConfig:
    """Configuration helper for VPC Service Controls"""
    
    @staticmethod
    def get_ai_analyst_restricted_services() -> List[ServiceRestriction]:
        """Get recommended restricted services for AI Data Analyst platform"""
        return [
            ServiceRestriction.BIGQUERY,
            ServiceRestriction.STORAGE,
            ServiceRestriction.VERTEX_AI,
            ServiceRestriction.AI_PLATFORM,
            ServiceRestriction.CLOUD_FUNCTIONS,
            ServiceRestriction.CLOUD_RUN,
            ServiceRestriction.DATAFLOW
        ]
    
    @staticmethod
    def get_vpc_accessible_services() -> List[str]:
        """Get VPC accessible services for AI Data Analyst platform"""
        return [
            "bigquery.googleapis.com",
            "storage.googleapis.com",
            "aiplatform.googleapis.com",
            "ml.googleapis.com",
            "logging.googleapis.com",
            "monitoring.googleapis.com",
            "cloudfunctions.googleapis.com",
            "run.googleapis.com"
        ]
    
    @staticmethod
    def create_standard_access_level(name: str, allowed_regions: List[str],
                                   allowed_ip_ranges: List[str] = None) -> AccessLevel:
        """Create standard access level for AI Data Analyst platform"""
        return AccessLevel(
            name=name,
            title=f"AI Data Analyst {name}",
            description=f"Standard access level for {name}",
            ip_ranges=allowed_ip_ranges or [],
            regions=allowed_regions,
            device_policy={
                "require_screen_lock": True,
                "require_admin_approval": False,
                "os_constraints": [
                    {"os_type": "DESKTOP_WINDOWS", "minimum_version": "10.0.0"},
                    {"os_type": "DESKTOP_MAC", "minimum_version": "10.15.0"},
                    {"os_type": "DESKTOP_LINUX", "minimum_version": ""}
                ]
            }
        )
    
    @staticmethod
    def create_tenant_ingress_policies(tenant_id: str) -> List[Dict[str, Any]]:
        """Create standard ingress policies for tenant"""
        return [
            {
                "description": f"Allow BigQuery access for tenant {tenant_id}",
                "ingress_from": {
                    "sources": [
                        {
                            "access_level": f"tenant_{tenant_id}_access"
                        }
                    ]
                },
                "ingress_to": {
                    "operations": [
                        {
                            "service_name": "bigquery.googleapis.com",
                            "method_selectors": [
                                {"method": "*"}
                            ]
                        }
                    ]
                }
            },
            {
                "description": f"Allow Cloud Storage access for tenant {tenant_id}",
                "ingress_from": {
                    "sources": [
                        {
                            "access_level": f"tenant_{tenant_id}_access"
                        }
                    ]
                },
                "ingress_to": {
                    "operations": [
                        {
                            "service_name": "storage.googleapis.com",
                            "method_selectors": [
                                {"method": "google.storage.objects.get"},
                                {"method": "google.storage.objects.list"},
                                {"method": "google.storage.objects.create"}
                            ]
                        }
                    ]
                }
            }
        ]


# Example usage
if __name__ == "__main__":
    # Initialize VPC Service Controls manager
    vpc_manager = VPCServiceControlsManager(
        organization_id="123456789",
        policy_id="policy-id"
    )
    
    # Create tenant perimeter
    tenant_id = "tenant-123"
    tenant_projects = ["ai-analyst-tenant-123", "ai-analyst-shared"]
    
    perimeter_info = vpc_manager.create_tenant_perimeter(
        tenant_id=tenant_id,
        tenant_projects=tenant_projects,
        allowed_regions=["us-central1", "us-east1"]
    )
    
    print(f"Created perimeter: {perimeter_info}")
    
    # List all perimeters
    perimeters = vpc_manager.list_service_perimeters()
    print(f"Service perimeters: {perimeters}")