"""
Authentication tests
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.auth import verify_jwt, get_current_user, check_project_access

@pytest.mark.asyncio
async def test_verify_jwt_missing_header():
    """Test JWT verification with missing header"""
    with pytest.raises(Exception) as exc_info:
        await verify_jwt(None)
    assert "missing" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_verify_jwt_invalid_scheme():
    """Test JWT verification with invalid scheme"""
    with pytest.raises(Exception) as exc_info:
        await verify_jwt("Basic token123")
    assert "invalid" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_get_current_user_valid():
    """Test getting current user from valid token"""
    token = {
        "sub": "user_123",
        "email": "user@example.com",
        "name": "Test User",
        "picture": "https://example.com/pic.jpg",
    }
    
    user = await get_current_user(token)
    
    assert user["user_id"] == "user_123"
    assert user["email"] == "user@example.com"
    assert user["name"] == "Test User"

@pytest.mark.asyncio
async def test_get_current_user_missing_required_fields():
    """Test getting current user with missing required fields"""
    token = {"sub": "user_123"}  # Missing email
    
    with pytest.raises(Exception):
        await get_current_user(token)

@pytest.mark.asyncio
async def test_check_project_access_valid():
    """Test project access check"""
    with patch('app.auth.get_user_role', new_callable=AsyncMock) as mock_role:
        mock_role.return_value = "editor"
        
        has_access = await check_project_access(
            "user_123",
            "project_456",
            "viewer"
        )
        
        assert has_access is True

@pytest.mark.asyncio
async def test_check_project_access_insufficient_role():
    """Test project access with insufficient role"""
    with patch('app.auth.get_user_role', new_callable=AsyncMock) as mock_role:
        mock_role.return_value = "viewer"
        
        has_access = await check_project_access(
            "user_123",
            "project_456",
            "admin"
        )
        
        assert has_access is False
