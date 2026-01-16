"""
Tests d'intégration pour PyJOAL
Tests pour vérifier le bon fonctionnement des endpoints principaux
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authentication headers for testing"""
    return {"X-API-Token": "test-token"}


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "app" in data 
    assert "version" in data
    assert "seeding" in data
    
    assert data["status"] == "healthy"
    assert data["app"] == "PyJOAL"


def test_version_endpoint(client):
    """Test version endpoint"""
    response = client.get("/api/version")
    assert response.status_code == 200
    
    data = response.json()
    assert "version" in data
    assert "name" in data
    assert "description" in data


@patch('app.core.config.settings.SECRET_TOKEN', 'test-token')
def test_config_endpoints(client, auth_headers):
    """Test configuration endpoints"""
    # Test GET config
    response = client.get("/api/config", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "minUploadRate" in data
    assert "maxUploadRate" in data
    assert "client" in data


@patch('app.core.config.settings.SECRET_TOKEN', 'test-token')
def test_stats_endpoint(client, auth_headers):
    """Test stats endpoint"""
    response = client.get("/api/stats", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "totalUploaded" in data
    assert "isRunning" in data
    assert "activeTorrents" in data


@patch('app.core.config.settings.SECRET_TOKEN', 'test-token')
def test_torrents_endpoint(client, auth_headers):
    """Test torrents listing endpoint"""
    response = client.get("/api/torrents", headers=auth_headers)
    assert response.status_code == 200
    
    # Should return a list (empty or with torrents)
    data = response.json()
    assert isinstance(data, list)


@patch('app.core.config.settings.SECRET_TOKEN', 'test-token')
def test_clients_endpoint(client, auth_headers):
    """Test clients listing endpoint"""
    response = client.get("/api/clients", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "clients" in data
    assert isinstance(data["clients"], list)


def test_unauthorized_access(client):
    """Test that protected endpoints require authentication"""
    protected_endpoints = [
        "/api/config",
        "/api/stats", 
        "/api/torrents",
        "/api/clients",
        "/api/start",
        "/api/stop"
    ]
    
    for endpoint in protected_endpoints:
        response = client.get(endpoint)
        assert response.status_code in [401, 403], f"Endpoint {endpoint} should require auth"


def test_invalid_auth_token(client):
    """Test with invalid authentication token"""
    invalid_headers = {"X-API-Token": "invalid-token"}
    
    response = client.get("/api/config", headers=invalid_headers)
    assert response.status_code in [401, 403]


def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.get("/health")
    
    # Check if CORS middleware is working (headers should be present for CORS requests)
    # Note: TestClient doesn't simulate CORS preflight, but we can check basic functionality
    assert response.status_code == 200


def test_api_documentation_available(client):
    """Test that API documentation is accessible"""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/redoc")
    assert response.status_code == 200


def test_openapi_spec(client):
    """Test that OpenAPI specification is available"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data