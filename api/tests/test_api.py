"""
API endpoint tests
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data

def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_readiness_endpoint():
    """Test readiness endpoint"""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"

def test_submit_job():
    """Test job submission"""
    payload = {
        "project_id": "proj_123",
        "dataset_refs": [
            {"type": "bigquery", "location": "project.dataset.table"}
        ],
        "question": "What are the top 10 categories?",
        "model_tier": "preview"
    }
    
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"

def test_get_job():
    """Test get job status"""
    response = client.get("/api/v1/jobs/job_123")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["id"] == "job_123"

def test_list_artifacts():
    """Test list artifacts"""
    response = client.get("/api/v1/artifacts?job_id=job_123")
    assert response.status_code == 200
    data = response.json()
    assert "artifacts" in data

def test_list_connectors():
    """Test list connectors"""
    response = client.get("/api/v1/connectors?project_id=proj_123")
    assert response.status_code == 200
    data = response.json()
    assert "connectors" in data
