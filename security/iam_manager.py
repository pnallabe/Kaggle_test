"""
Multi-Tenant Identity and Access Management (IAM) Module

This module implements comprehensive multi-tenant IAM with:
- Role-based access control (RBAC)
- Tenant isolation and data segregation
- Dataset-level permissions
- Dynamic resource provisioning
- Google Cloud IAM integration
- JWT token management
- Audit logging for all access events
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
import jwt
import logging
from functools import wraps

from google.cloud import iam_admin_v1
from google.cloud import resourcemanager_v3
from google.cloud import bigquery
from google.cloud import storage
from google.oauth2 import service_account
import google.auth
from google.auth.transport.requests import Request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Permission(Enum):
    """Granular permissions for different operations"""
    # Dataset permissions
    DATASET_READ = "dataset.read"
    DATASET_WRITE = "dataset.write"
    DATASET_DELETE = "dataset.delete"
    DATASET_CREATE = "dataset.create"
    DATASET_ADMIN = "dataset.admin"
    
    # Query permissions
    QUERY_EXECUTE = "query.execute"
    QUERY_CREATE = "query.create"
    QUERY_HISTORY = "query.history"
    QUERY_ADMIN = "query.admin"
    
    # Visualization permissions
    VISUALIZATION_VIEW = "visualization.view"
    VISUALIZATION_CREATE = "visualization.create"
    VISUALIZATION_EDIT = "visualization.edit"
    VISUALIZATION_DELETE = "visualization.delete"
    VISUALIZATION_SHARE = "visualization.share"
    
    # Analytics permissions
    ANALYTICS_VIEW = "analytics.view"
    ANALYTICS_CREATE = "analytics.create"
    ANALYTICS_EXPORT = "analytics.export"
    
    # System permissions
    SYSTEM_ADMIN = "system.admin"
    TENANT_ADMIN = "tenant.admin"
    USER_MANAGE = "user.manage"
    BILLING_VIEW = "billing.view"
    BILLING_MANAGE = "billing.manage"
    
    # Compliance permissions
    AUDIT_VIEW = "audit.view"
    COMPLIANCE_MANAGE = "compliance.manage"


class Role(Enum):
    """Predefined roles with permission sets"""
    # End-user roles
    VIEWER = "viewer"
    ANALYST = "analyst"
    DATA_SCIENTIST = "data_scientist"
    
    # Administrative roles
    TENANT_ADMIN = "tenant_admin"
    SYSTEM_ADMIN = "system_admin"
    
    # Specialized roles
    COMPLIANCE_OFFICER = "compliance_officer"
    BILLING_ADMIN = "billing_admin"
    SECURITY_ADMIN = "security_admin"


@dataclass
class Tenant:
    """Tenant entity with isolation configuration"""
    id: str
    name: str
    domain: str
    created_at: datetime
    status: str
    max_users: int
    max_datasets: int
    max_queries_per_day: int
    storage_quota_gb: int
    compute_quota_hours: int
    compliance_requirements: List[str]
    data_residency: str
    encryption_key: Optional[str] = None
    vpc_network: Optional[str] = None
    project_ids: List[str] = None
    
    def __post_init__(self):
        if self.project_ids is None:
            self.project_ids = []


@dataclass
class User:
    """User entity with role assignments"""
    id: str
    email: str
    tenant_id: str
    roles: List[Role]
    permissions: Set[Permission]
    created_at: datetime
    last_login: Optional[datetime]
    status: str
    mfa_enabled: bool
    dataset_access: Dict[str, List[str]]  # dataset_id -> permissions
    session_timeout: int = 3600  # seconds
    
    def __post_init__(self):
        if isinstance(self.permissions, list):
            self.permissions = set(self.permissions)


@dataclass
class AccessToken:
    """JWT access token with tenant context"""
    user_id: str
    tenant_id: str
    roles: List[str]
    permissions: List[str]
    iat: int
    exp: int
    aud: str
    iss: str
    dataset_access: Dict[str, List[str]]


class IAMManager:
    """Multi-tenant IAM manager with Google Cloud integration"""
    
    def __init__(self, project_id: str, secret_key: str):
        self.project_id = project_id
        self.secret_key = secret_key
        self.iam_client = iam_admin_v1.IAMClient()
        self.resource_manager = resourcemanager_v3.ProjectsClient()
        self.bigquery_client = bigquery.Client()
        self.storage_client = storage.Client()
        
        # Role to permissions mapping
        self.role_permissions = {
            Role.VIEWER: {
                Permission.DATASET_READ,
                Permission.QUERY_EXECUTE,
                Permission.VISUALIZATION_VIEW,
                Permission.ANALYTICS_VIEW
            },
            Role.ANALYST: {
                Permission.DATASET_READ,
                Permission.QUERY_EXECUTE,
                Permission.QUERY_CREATE,
                Permission.QUERY_HISTORY,
                Permission.VISUALIZATION_VIEW,
                Permission.VISUALIZATION_CREATE,
                Permission.VISUALIZATION_EDIT,
                Permission.ANALYTICS_VIEW,
                Permission.ANALYTICS_CREATE
            },
            Role.DATA_SCIENTIST: {
                Permission.DATASET_READ,
                Permission.DATASET_WRITE,
                Permission.QUERY_EXECUTE,
                Permission.QUERY_CREATE,
                Permission.QUERY_HISTORY,
                Permission.VISUALIZATION_VIEW,
                Permission.VISUALIZATION_CREATE,
                Permission.VISUALIZATION_EDIT,
                Permission.VISUALIZATION_SHARE,
                Permission.ANALYTICS_VIEW,
                Permission.ANALYTICS_CREATE,
                Permission.ANALYTICS_EXPORT
            },
            Role.TENANT_ADMIN: {
                Permission.DATASET_READ,
                Permission.DATASET_WRITE,
                Permission.DATASET_CREATE,
                Permission.DATASET_DELETE,
                Permission.QUERY_ADMIN,
                Permission.VISUALIZATION_VIEW,
                Permission.VISUALIZATION_CREATE,
                Permission.VISUALIZATION_EDIT,
                Permission.VISUALIZATION_DELETE,
                Permission.VISUALIZATION_SHARE,
                Permission.ANALYTICS_VIEW,
                Permission.ANALYTICS_CREATE,
                Permission.ANALYTICS_EXPORT,
                Permission.USER_MANAGE,
                Permission.BILLING_VIEW,
                Permission.AUDIT_VIEW
            },
            Role.SYSTEM_ADMIN: set(Permission),  # All permissions
            Role.COMPLIANCE_OFFICER: {
                Permission.AUDIT_VIEW,
                Permission.COMPLIANCE_MANAGE,
                Permission.DATASET_READ,
                Permission.QUERY_HISTORY
            },
            Role.BILLING_ADMIN: {
                Permission.BILLING_VIEW,
                Permission.BILLING_MANAGE,
                Permission.AUDIT_VIEW
            },
            Role.SECURITY_ADMIN: {
                Permission.USER_MANAGE,
                Permission.AUDIT_VIEW,
                Permission.COMPLIANCE_MANAGE,
                Permission.SYSTEM_ADMIN
            }
        }
    
    def create_tenant(self, tenant_data: Dict[str, Any]) -> Tenant:
        """Create a new tenant with isolated resources"""
        tenant_id = str(uuid.uuid4())
        
        tenant = Tenant(
            id=tenant_id,
            name=tenant_data["name"],
            domain=tenant_data["domain"],
            created_at=datetime.utcnow(),
            status="active",
            max_users=tenant_data.get("max_users", 100),
            max_datasets=tenant_data.get("max_datasets", 50),
            max_queries_per_day=tenant_data.get("max_queries_per_day", 10000),
            storage_quota_gb=tenant_data.get("storage_quota_gb", 1000),
            compute_quota_hours=tenant_data.get("compute_quota_hours", 100),
            compliance_requirements=tenant_data.get("compliance_requirements", []),
            data_residency=tenant_data.get("data_residency", "us-central1")
        )
        
        # Create isolated GCP resources
        self._create_tenant_resources(tenant)
        
        logger.info(f"Created tenant: {tenant.name} ({tenant.id})")
        return tenant
    
    def _create_tenant_resources(self, tenant: Tenant):
        """Create isolated GCP resources for tenant"""
        # Create dedicated project for tenant
        project_id = f"ai-analyst-{tenant.id[:8]}"
        
        try:
            # Create BigQuery dataset with tenant isolation
            dataset_id = f"tenant_{tenant.id.replace('-', '_')}"
            dataset = bigquery.Dataset(f"{self.project_id}.{dataset_id}")
            dataset.location = tenant.data_residency
            
            # Set dataset-level access control
            dataset.access_entries = [
                bigquery.AccessEntry(
                    role="OWNER",
                    entity_type="userByEmail",
                    entity_id=f"tenant-admin@{tenant.domain}"
                )
            ]
            
            self.bigquery_client.create_dataset(dataset, exists_ok=True)
            
            # Create Cloud Storage bucket for tenant
            bucket_name = f"ai-analyst-{tenant.id}"
            bucket = self.storage_client.bucket(bucket_name)
            bucket.location = tenant.data_residency
            bucket.create(exist_ok=True)
            
            tenant.project_ids.append(project_id)
            
        except Exception as e:
            logger.error(f"Failed to create tenant resources: {e}")
            raise
    
    def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new user with role assignments"""
        user_id = str(uuid.uuid4())
        
        # Parse roles
        roles = [Role(role) for role in user_data.get("roles", ["viewer"])]
        
        # Calculate permissions from roles
        permissions = set()
        for role in roles:
            permissions.update(self.role_permissions.get(role, set()))
        
        user = User(
            id=user_id,
            email=user_data["email"],
            tenant_id=user_data["tenant_id"],
            roles=roles,
            permissions=permissions,
            created_at=datetime.utcnow(),
            last_login=None,
            status="active",
            mfa_enabled=user_data.get("mfa_enabled", False),
            dataset_access=user_data.get("dataset_access", {}),
            session_timeout=user_data.get("session_timeout", 3600)
        )
        
        logger.info(f"Created user: {user.email} ({user.id})")
        return user
    
    def generate_access_token(self, user: User, tenant: Tenant) -> str:
        """Generate JWT access token with tenant context"""
        now = datetime.utcnow()
        exp = now + timedelta(seconds=user.session_timeout)
        
        payload = {
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "email": user.email,
            "roles": [role.value for role in user.roles],
            "permissions": [perm.value for perm in user.permissions],
            "dataset_access": user.dataset_access,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "aud": "ai-data-analyst",
            "iss": f"tenant-{tenant.id}"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        logger.info(f"Generated access token for user: {user.email}")
        
        return token
    
    def verify_access_token(self, token: str) -> AccessToken:
        """Verify and decode JWT access token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            return AccessToken(
                user_id=payload["user_id"],
                tenant_id=payload["tenant_id"],
                roles=payload["roles"],
                permissions=payload["permissions"],
                iat=payload["iat"],
                exp=payload["exp"],
                aud=payload["aud"],
                iss=payload["iss"],
                dataset_access=payload.get("dataset_access", {})
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")
    
    def check_permission(self, token: AccessToken, permission: Permission, 
                        resource_id: Optional[str] = None) -> bool:
        """Check if user has specific permission for resource"""
        # Check if permission is in user's permission set
        if permission.value not in token.permissions:
            return False
        
        # Check dataset-level permissions if resource_id provided
        if resource_id and permission in [Permission.DATASET_READ, 
                                        Permission.DATASET_WRITE,
                                        Permission.DATASET_DELETE]:
            dataset_perms = token.dataset_access.get(resource_id, [])
            return permission.value in dataset_perms
        
        return True
    
    def grant_dataset_access(self, user_id: str, dataset_id: str, 
                           permissions: List[Permission]) -> bool:
        """Grant user access to specific dataset"""
        try:
            # Update BigQuery dataset IAM policy
            dataset_ref = self.bigquery_client.dataset(dataset_id)
            policy = dataset_ref.get_iam_policy()
            
            # Add user to appropriate roles
            for permission in permissions:
                if permission == Permission.DATASET_READ:
                    role = "roles/bigquery.dataViewer"
                elif permission == Permission.DATASET_WRITE:
                    role = "roles/bigquery.dataEditor"
                elif permission == Permission.DATASET_ADMIN:
                    role = "roles/bigquery.dataOwner"
                else:
                    continue
                
                policy.bindings.append({
                    "role": role,
                    "members": [f"user:{user_id}"]
                })
            
            dataset_ref.set_iam_policy(policy)
            logger.info(f"Granted dataset access: {dataset_id} to user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to grant dataset access: {e}")
            return False
    
    def revoke_dataset_access(self, user_id: str, dataset_id: str) -> bool:
        """Revoke user access to specific dataset"""
        try:
            # Update BigQuery dataset IAM policy
            dataset_ref = self.bigquery_client.dataset(dataset_id)
            policy = dataset_ref.get_iam_policy()
            
            # Remove user from all roles
            for binding in policy.bindings:
                if f"user:{user_id}" in binding["members"]:
                    binding["members"].remove(f"user:{user_id}")
            
            dataset_ref.set_iam_policy(policy)
            logger.info(f"Revoked dataset access: {dataset_id} from user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke dataset access: {e}")
            return False
    
    def get_user_resources(self, token: AccessToken) -> Dict[str, List[str]]:
        """Get list of resources user has access to"""
        resources = {
            "datasets": [],
            "queries": [],
            "visualizations": [],
            "dashboards": []
        }
        
        # Get datasets user has access to
        for dataset_id, permissions in token.dataset_access.items():
            if Permission.DATASET_READ.value in permissions:
                resources["datasets"].append(dataset_id)
        
        return resources
    
    def audit_log_access(self, token: AccessToken, action: str, 
                        resource_type: str, resource_id: str, 
                        result: str, metadata: Dict[str, Any] = None):
        """Log access attempt for audit trail"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": token.user_id,
            "tenant_id": token.tenant_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "result": result,
            "ip_address": metadata.get("ip_address") if metadata else None,
            "user_agent": metadata.get("user_agent") if metadata else None,
            "session_id": metadata.get("session_id") if metadata else None
        }
        
        logger.info(f"Access audit: {json.dumps(log_entry)}")


def require_permission(permission: Permission, resource_id_param: str = None):
    """Decorator to enforce permission checking"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract token from kwargs or request context
            token = kwargs.get('token') or getattr(func, 'current_token', None)
            if not token:
                raise ValueError("Authentication token required")
            
            # Get resource ID if specified
            resource_id = None
            if resource_id_param:
                resource_id = kwargs.get(resource_id_param)
            
            # Check permission
            iam_manager = getattr(func, 'iam_manager', None)
            if not iam_manager or not iam_manager.check_permission(token, permission, resource_id):
                raise PermissionError(f"Insufficient permissions: {permission.value}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_tenant_isolation(func):
    """Decorator to enforce tenant isolation"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = kwargs.get('token') or getattr(func, 'current_token', None)
        if not token:
            raise ValueError("Authentication token required")
        
        # Ensure all resource access is scoped to user's tenant
        tenant_id = token.tenant_id
        
        # Add tenant filtering to queries/operations
        kwargs['tenant_filter'] = tenant_id
        
        return func(*args, **kwargs)
    return wrapper


# Example usage and testing
if __name__ == "__main__":
    # Initialize IAM manager
    iam_manager = IAMManager("ai-data-analyst-project", "your-secret-key")
    
    # Create tenant
    tenant = iam_manager.create_tenant({
        "name": "Acme Corp",
        "domain": "acme.com",
        "max_users": 500,
        "compliance_requirements": ["SOC2", "GDPR"]
    })
    
    # Create user
    user = iam_manager.create_user({
        "email": "analyst@acme.com",
        "tenant_id": tenant.id,
        "roles": ["analyst", "data_scientist"],
        "mfa_enabled": True
    })
    
    # Generate access token
    token_string = iam_manager.generate_access_token(user, tenant)
    token = iam_manager.verify_access_token(token_string)
    
    # Check permissions
    can_read = iam_manager.check_permission(token, Permission.DATASET_READ)
    can_admin = iam_manager.check_permission(token, Permission.SYSTEM_ADMIN)
    
    print(f"User can read datasets: {can_read}")
    print(f"User can admin system: {can_admin}")
    
    # Grant dataset access
    iam_manager.grant_dataset_access(
        user.id, 
        "sales_data", 
        [Permission.DATASET_READ, Permission.DATASET_WRITE]
    )
    
    # Get user resources
    resources = iam_manager.get_user_resources(token)
    print(f"User resources: {resources}")