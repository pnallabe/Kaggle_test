"""
Authentication and authorization module
"""

from typing import Optional
from datetime import datetime
import logging

from fastapi import HTTPException, status, Header
from google.auth.transport import requests
from google.oauth2 import id_token

from app.config import settings
from app.database import get_user_role

logger = logging.getLogger(__name__)

async def verify_jwt(authorization: Optional[str] = Header(None)) -> dict:
    """
    Verify JWT token from Identity Platform
    
    Args:
        authorization: Bearer token from request header
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )
    
    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authorization scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    
    try:
        # Verify token with Google's public keys
        # In production, use: id_token.verify_oauth2_token()
        # For development, verify with Firebase Admin SDK
        
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.JWT_AUDIENCE,
        )
        
        # Token is valid, return claims
        return idinfo
        
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

async def get_current_user(token: dict = None) -> dict:
    """
    Get current authenticated user from token
    
    Args:
        token: Verified JWT token payload
        
    Returns:
        User info dict with user_id, email, etc.
    """
    if not token:
        token = {}
    
    user_id = token.get("sub")
    email = token.get("email")
    
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    return {
        "user_id": user_id,
        "email": email,
        "name": token.get("name", ""),
        "picture": token.get("picture", ""),
        "iat": token.get("iat"),
        "exp": token.get("exp"),
    }

async def check_project_access(
    user_id: str,
    project_id: str,
    required_role: str = "viewer"
) -> bool:
    """
    Check if user has access to project with required role
    
    Args:
        user_id: User identifier
        project_id: Project identifier
        required_role: Minimum required role (viewer, editor, admin)
        
    Returns:
        True if user has required access, False otherwise
    """
    try:
        user_role = await get_user_role(user_id, project_id)
        role_hierarchy = {"viewer": 0, "editor": 1, "admin": 2}
        return role_hierarchy.get(user_role, -1) >= role_hierarchy.get(required_role, 0)
    except Exception as e:
        logger.error(f"Failed to check project access: {str(e)}")
        return False

async def audit_log(
    user_id: str,
    action: str,
    target: str,
    details: dict = None,
    status_code: int = 200,
    ip_address: str = None,
) -> None:
    """
    Log user actions for audit trail
    
    Args:
        user_id: User identifier
        action: Action performed (e.g., "query_submitted", "job_created")
        target: Target resource (e.g., "job_123", "dataset_abc")
        details: Additional details dict
        status_code: HTTP status code
        ip_address: Client IP address
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "action": action,
        "target": target,
        "status_code": status_code,
        "ip_address": ip_address,
        "details": details or {},
    }
    
    logger.info(f"AUDIT: {log_entry}")
    # TODO: Write to Cloud Logging / BigQuery audit dataset
