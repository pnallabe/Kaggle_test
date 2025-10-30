"""
Secret Manager Integration Module

This module provides comprehensive secret management including:
- Secure credential storage and retrieval
- Automatic secret rotation
- Access control and audit logging
- Multi-tenant secret isolation
- Integration with Google Cloud Secret Manager
"""

import json
import logging
import os
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import secrets
import string

from google.cloud import secretmanager
from google.cloud import kms
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecretType(Enum):
    """Types of secrets managed by the system"""
    DATABASE_CREDENTIALS = "database_credentials"
    API_KEYS = "api_keys"
    JWT_SIGNING_KEY = "jwt_signing_key"
    ENCRYPTION_KEY = "encryption_key"
    OAUTH_CREDENTIALS = "oauth_credentials"
    SERVICE_ACCOUNT_KEY = "service_account_key"
    WEBHOOK_SECRET = "webhook_secret"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"


class RotationFrequency(Enum):
    """Secret rotation frequencies"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    NEVER = "never"


@dataclass
class SecretMetadata:
    """Metadata for secret management"""
    secret_id: str
    name: str
    description: str
    secret_type: SecretType
    tenant_id: str
    created_at: datetime
    last_rotated: Optional[datetime]
    rotation_frequency: RotationFrequency
    auto_rotate: bool
    access_count: int
    last_accessed: Optional[datetime]
    tags: Dict[str, str]
    
    def __post_init__(self):
        if isinstance(self.secret_type, str):
            self.secret_type = SecretType(self.secret_type)
        if isinstance(self.rotation_frequency, str):
            self.rotation_frequency = RotationFrequency(self.rotation_frequency)


@dataclass
class SecretVersion:
    """Version information for secrets"""
    version_id: str
    secret_id: str
    created_at: datetime
    is_active: bool
    is_destroyed: bool
    checksum: str


@dataclass
class AccessPolicy:
    """Access policy for secrets"""
    secret_id: str
    principals: List[str]  # IAM principals (users, service accounts)
    roles: List[str]  # IAM roles
    conditions: Dict[str, Any]  # IAM conditions
    created_at: datetime
    expires_at: Optional[datetime]


class SecretManager:
    """Comprehensive secret management with Google Cloud Secret Manager"""
    
    def __init__(self, project_id: str, location: str = "global"):
        self.project_id = project_id
        self.location = location
        self.client = secretmanager.SecretManagerServiceClient()
        self.kms_client = kms.KeyManagementServiceClient()
        
        # KMS key for additional encryption layer
        self.kms_key_path = f"projects/{project_id}/locations/{location}/keyRings/ai-analyst-secrets/cryptoKeys/secret-encryption"
        
        # Initialize local encryption for sensitive operations
        self._init_local_encryption()
    
    def _init_local_encryption(self):
        """Initialize local encryption for sensitive data"""
        # Generate or load encryption key for local operations
        key_material = os.environ.get('LOCAL_ENCRYPTION_KEY')
        if not key_material:
            # Generate new key (in production, this should be stored securely)
            key_material = Fernet.generate_key()
            logger.warning("Generated new local encryption key. Store securely!")
        
        if isinstance(key_material, str):
            key_material = key_material.encode()
        
        self.local_cipher = Fernet(key_material)
    
    def create_secret(self, metadata: SecretMetadata, secret_value: Union[str, bytes, Dict[str, Any]]) -> str:
        """Create a new secret with metadata"""
        try:
            # Convert secret value to bytes if needed
            if isinstance(secret_value, dict):
                secret_data = json.dumps(secret_value).encode('utf-8')
            elif isinstance(secret_value, str):
                secret_data = secret_value.encode('utf-8')
            else:
                secret_data = secret_value
            
            # Create secret resource
            parent = f"projects/{self.project_id}"
            secret_id = f"tenant-{metadata.tenant_id}-{metadata.secret_id}"
            
            # Build secret configuration
            secret = secretmanager.Secret()
            secret.labels = {
                "tenant_id": metadata.tenant_id,
                "secret_type": metadata.secret_type.value,
                "auto_rotate": str(metadata.auto_rotate).lower(),
                "rotation_frequency": metadata.rotation_frequency.value
            }
            secret.labels.update(metadata.tags)
            
            # Set up automatic deletion if configured
            if metadata.rotation_frequency != RotationFrequency.NEVER:
                secret.ttl = self._get_ttl_for_frequency(metadata.rotation_frequency)
            
            # Create the secret
            secret_response = self.client.create_secret(
                parent=parent,
                secret_id=secret_id,
                secret=secret
            )
            
            # Add the secret version with the actual data
            version_response = self.client.add_secret_version(
                parent=secret_response.name,
                payload={'data': secret_data}
            )
            
            # Store metadata
            self._store_secret_metadata(metadata)
            
            # Set up access policies
            self._set_default_access_policy(secret_response.name, metadata.tenant_id)
            
            logger.info(f"Created secret: {secret_id} for tenant: {metadata.tenant_id}")
            return secret_response.name
            
        except Exception as e:
            logger.error(f"Failed to create secret {metadata.secret_id}: {e}")
            raise
    
    def get_secret(self, secret_id: str, tenant_id: str, version: str = "latest") -> Union[str, Dict[str, Any]]:
        """Retrieve secret value with access logging"""
        try:
            # Build secret version name
            full_secret_id = f"tenant-{tenant_id}-{secret_id}"
            secret_version_name = f"projects/{self.project_id}/secrets/{full_secret_id}/versions/{version}"
            
            # Access the secret version
            response = self.client.access_secret_version(name=secret_version_name)
            secret_data = response.payload.data
            
            # Update access metadata
            self._log_secret_access(secret_id, tenant_id)
            
            # Try to parse as JSON, otherwise return as string
            try:
                secret_str = secret_data.decode('utf-8')
                return json.loads(secret_str)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return secret_data.decode('utf-8') if isinstance(secret_data, bytes) else secret_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_id}: {e}")
            raise
    
    def rotate_secret(self, secret_id: str, tenant_id: str, new_value: Union[str, bytes, Dict[str, Any]]) -> str:
        """Rotate secret with new value"""
        try:
            # Convert new value to bytes
            if isinstance(new_value, dict):
                secret_data = json.dumps(new_value).encode('utf-8')
            elif isinstance(new_value, str):
                secret_data = new_value.encode('utf-8')
            else:
                secret_data = new_value
            
            # Build secret name
            full_secret_id = f"tenant-{tenant_id}-{secret_id}"
            secret_name = f"projects/{self.project_id}/secrets/{full_secret_id}"
            
            # Add new version
            version_response = self.client.add_secret_version(
                parent=secret_name,
                payload={'data': secret_data}
            )
            
            # Update metadata
            self._update_rotation_metadata(secret_id, tenant_id)
            
            logger.info(f"Rotated secret: {secret_id} for tenant: {tenant_id}")
            return version_response.name
            
        except Exception as e:
            logger.error(f"Failed to rotate secret {secret_id}: {e}")
            raise
    
    def delete_secret(self, secret_id: str, tenant_id: str) -> bool:
        """Delete secret and all versions"""
        try:
            full_secret_id = f"tenant-{tenant_id}-{secret_id}"
            secret_name = f"projects/{self.project_id}/secrets/{full_secret_id}"
            
            # Delete the secret
            self.client.delete_secret(name=secret_name)
            
            # Remove metadata
            self._remove_secret_metadata(secret_id, tenant_id)
            
            logger.info(f"Deleted secret: {secret_id} for tenant: {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete secret {secret_id}: {e}")
            return False
    
    def list_tenant_secrets(self, tenant_id: str) -> List[SecretMetadata]:
        """List all secrets for a tenant"""
        try:
            secrets = []
            parent = f"projects/{self.project_id}"
            
            # List secrets with tenant filter
            for secret in self.client.list_secrets(parent=parent):
                if secret.labels.get('tenant_id') == tenant_id:
                    # Extract secret ID (remove tenant prefix)
                    secret_parts = secret.name.split('/')[-1]
                    if secret_parts.startswith(f"tenant-{tenant_id}-"):
                        actual_secret_id = secret_parts[len(f"tenant-{tenant_id}-"):]
                        
                        metadata = SecretMetadata(
                            secret_id=actual_secret_id,
                            name=secret.labels.get('name', actual_secret_id),
                            description=secret.labels.get('description', ''),
                            secret_type=SecretType(secret.labels.get('secret_type', 'api_keys')),
                            tenant_id=tenant_id,
                            created_at=secret.create_time,
                            last_rotated=None,  # Would need to fetch from metadata store
                            rotation_frequency=RotationFrequency(secret.labels.get('rotation_frequency', 'never')),
                            auto_rotate=secret.labels.get('auto_rotate', 'false').lower() == 'true',
                            access_count=0,  # Would need to fetch from metadata store
                            last_accessed=None,  # Would need to fetch from metadata store
                            tags={k: v for k, v in secret.labels.items() if k not in ['tenant_id', 'secret_type', 'auto_rotate', 'rotation_frequency']}
                        )
                        secrets.append(metadata)
            
            return secrets
            
        except Exception as e:
            logger.error(f"Failed to list secrets for tenant {tenant_id}: {e}")
            raise
    
    def set_access_policy(self, secret_id: str, tenant_id: str, policy: AccessPolicy):
        """Set IAM access policy for secret"""
        try:
            full_secret_id = f"tenant-{tenant_id}-{secret_id}"
            secret_name = f"projects/{self.project_id}/secrets/{full_secret_id}"
            
            # Get current IAM policy
            current_policy = self.client.get_iam_policy(resource=secret_name)
            
            # Add new bindings
            for principal in policy.principals:
                for role in policy.roles:
                    binding = {
                        'role': role,
                        'members': [principal]
                    }
                    
                    # Add conditions if specified
                    if policy.conditions:
                        binding['condition'] = policy.conditions
                    
                    current_policy.bindings.append(binding)
            
            # Set the updated policy
            self.client.set_iam_policy(resource=secret_name, policy=current_policy)
            
            logger.info(f"Set access policy for secret: {secret_id}")
            
        except Exception as e:
            logger.error(f"Failed to set access policy for secret {secret_id}: {e}")
            raise
    
    def generate_strong_password(self, length: int = 32, include_symbols: bool = True) -> str:
        """Generate cryptographically strong password"""
        alphabet = string.ascii_letters + string.digits
        if include_symbols:
            alphabet += "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        # Ensure password has at least one character from each category
        password = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits)
        ]
        
        if include_symbols:
            password.append(secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?"))
        
        # Fill the rest with random characters
        for _ in range(length - len(password)):
            password.append(secrets.choice(alphabet))
        
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        return ''.join(password)
    
    def generate_api_key(self, prefix: str = "ai_analyst", length: int = 32) -> str:
        """Generate API key with prefix"""
        key_part = secrets.token_urlsafe(length)
        return f"{prefix}_{key_part}"
    
    def generate_jwt_signing_key(self) -> str:
        """Generate JWT signing key"""
        return secrets.token_urlsafe(64)
    
    def generate_database_credentials(self, username: str, host: str, database: str) -> Dict[str, str]:
        """Generate database credentials"""
        return {
            "username": username,
            "password": self.generate_strong_password(),
            "host": host,
            "database": database,
            "port": "5432",  # Default PostgreSQL port
            "ssl_mode": "require"
        }
    
    def encrypt_local_data(self, data: Union[str, bytes]) -> str:
        """Encrypt data locally for additional security"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted_data = self.local_cipher.encrypt(data)
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt_local_data(self, encrypted_data: str) -> str:
        """Decrypt locally encrypted data"""
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        decrypted_data = self.local_cipher.decrypt(encrypted_bytes)
        return decrypted_data.decode('utf-8')
    
    def schedule_rotation(self, secret_id: str, tenant_id: str, frequency: RotationFrequency):
        """Schedule automatic secret rotation"""
        # This would integrate with Cloud Scheduler or similar service
        # For now, we'll update the metadata to track rotation requirements
        
        try:
            metadata = self._get_secret_metadata(secret_id, tenant_id)
            if metadata:
                metadata.rotation_frequency = frequency
                metadata.auto_rotate = frequency != RotationFrequency.NEVER
                self._store_secret_metadata(metadata)
                
                logger.info(f"Scheduled rotation for secret {secret_id}: {frequency.value}")
            
        except Exception as e:
            logger.error(f"Failed to schedule rotation for secret {secret_id}: {e}")
            raise
    
    def check_rotation_needed(self, secret_id: str, tenant_id: str) -> bool:
        """Check if secret needs rotation based on policy"""
        try:
            metadata = self._get_secret_metadata(secret_id, tenant_id)
            if not metadata or not metadata.auto_rotate:
                return False
            
            if not metadata.last_rotated:
                return True
            
            # Calculate next rotation date
            rotation_interval = self._get_rotation_interval(metadata.rotation_frequency)
            next_rotation = metadata.last_rotated + rotation_interval
            
            return datetime.utcnow() >= next_rotation
            
        except Exception as e:
            logger.error(f"Failed to check rotation status for secret {secret_id}: {e}")
            return False
    
    def audit_secret_access(self, tenant_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get audit log of secret access for tenant"""
        # This would integrate with Cloud Audit Logs
        # For now, return mock data structure
        
        audit_logs = []
        
        # In a real implementation, this would query Cloud Logging
        # and return actual access logs
        
        return audit_logs
    
    def _store_secret_metadata(self, metadata: SecretMetadata):
        """Store secret metadata (would use database in production)"""
        # This would store metadata in a database
        # For now, we'll use local storage or labels
        pass
    
    def _get_secret_metadata(self, secret_id: str, tenant_id: str) -> Optional[SecretMetadata]:
        """Retrieve secret metadata"""
        # This would retrieve from database
        # For now, return None
        return None
    
    def _remove_secret_metadata(self, secret_id: str, tenant_id: str):
        """Remove secret metadata"""
        # This would remove from database
        pass
    
    def _update_rotation_metadata(self, secret_id: str, tenant_id: str):
        """Update rotation timestamp"""
        # This would update database record
        pass
    
    def _log_secret_access(self, secret_id: str, tenant_id: str):
        """Log secret access for audit"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "secret_id": secret_id,
            "tenant_id": tenant_id,
            "action": "access",
            "user_id": "system"  # Would get from context
        }
        
        logger.info(f"Secret access: {json.dumps(log_entry)}")
    
    def _set_default_access_policy(self, secret_name: str, tenant_id: str):
        """Set default access policy for secret"""
        # This would set appropriate IAM policies
        pass
    
    def _get_ttl_for_frequency(self, frequency: RotationFrequency) -> timedelta:
        """Get TTL based on rotation frequency"""
        frequency_map = {
            RotationFrequency.DAILY: timedelta(days=1),
            RotationFrequency.WEEKLY: timedelta(weeks=1),
            RotationFrequency.MONTHLY: timedelta(days=30),
            RotationFrequency.QUARTERLY: timedelta(days=90),
            RotationFrequency.YEARLY: timedelta(days=365)
        }
        
        return frequency_map.get(frequency, timedelta(days=365))
    
    def _get_rotation_interval(self, frequency: RotationFrequency) -> timedelta:
        """Get rotation interval for frequency"""
        return self._get_ttl_for_frequency(frequency)


class TenantSecretManager:
    """Tenant-specific secret manager with isolation"""
    
    def __init__(self, secret_manager: SecretManager, tenant_id: str):
        self.secret_manager = secret_manager
        self.tenant_id = tenant_id
    
    def create_database_secret(self, name: str, database_config: Dict[str, str]) -> str:
        """Create database credentials secret"""
        metadata = SecretMetadata(
            secret_id=f"db_{name}",
            name=f"Database credentials for {name}",
            description=f"Database connection credentials for {name}",
            secret_type=SecretType.DATABASE_CREDENTIALS,
            tenant_id=self.tenant_id,
            created_at=datetime.utcnow(),
            last_rotated=None,
            rotation_frequency=RotationFrequency.MONTHLY,
            auto_rotate=True,
            access_count=0,
            last_accessed=None,
            tags={"environment": "production", "service": name}
        )
        
        return self.secret_manager.create_secret(metadata, database_config)
    
    def create_api_key_secret(self, service_name: str) -> str:
        """Create API key secret"""
        api_key = self.secret_manager.generate_api_key(f"ai_analyst_{service_name}")
        
        metadata = SecretMetadata(
            secret_id=f"api_{service_name}",
            name=f"API key for {service_name}",
            description=f"API key for {service_name} service",
            secret_type=SecretType.API_KEYS,
            tenant_id=self.tenant_id,
            created_at=datetime.utcnow(),
            last_rotated=None,
            rotation_frequency=RotationFrequency.QUARTERLY,
            auto_rotate=True,
            access_count=0,
            last_accessed=None,
            tags={"service": service_name}
        )
        
        return self.secret_manager.create_secret(metadata, api_key)
    
    def get_database_credentials(self, name: str) -> Dict[str, str]:
        """Get database credentials"""
        return self.secret_manager.get_secret(f"db_{name}", self.tenant_id)
    
    def get_api_key(self, service_name: str) -> str:
        """Get API key"""
        return self.secret_manager.get_secret(f"api_{service_name}", self.tenant_id)


# Example usage
if __name__ == "__main__":
    # Initialize secret manager
    secret_manager = SecretManager("ai-data-analyst-project")
    
    # Create tenant-specific manager
    tenant_manager = TenantSecretManager(secret_manager, "tenant-123")
    
    # Create database secret
    db_secret = tenant_manager.create_database_secret("analytics_db", {
        "username": "analyst_user",
        "password": secret_manager.generate_strong_password(),
        "host": "analytics-db.internal",
        "database": "tenant_123_analytics",
        "port": "5432"
    })
    
    # Create API key secret
    api_secret = tenant_manager.create_api_key_secret("vertex_ai")
    
    # Retrieve secrets
    db_creds = tenant_manager.get_database_credentials("analytics_db")
    api_key = tenant_manager.get_api_key("vertex_ai")
    
    print(f"Database secret created: {db_secret}")
    print(f"API key secret created: {api_secret}")
    print(f"Retrieved API key: {api_key[:20]}...")