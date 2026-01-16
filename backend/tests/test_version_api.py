"""
Tests for version API endpoint
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, mock_open
from pathlib import Path

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_get_version_from_file():
    """Test getting version from VERSION file"""
    mock_version_content = "1.3.4"
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value=mock_version_content):
        
        response = client().get("/api/version")
        
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.3.4"
        assert data["name"] == "PyJOAL"
        assert data["description"] == "Python BitTorrent Ratio Client"


def test_get_version_file_not_exists():
    """Test fallback when VERSION file doesn't exist"""
    with patch("pathlib.Path.exists", return_value=False), \
         patch("subprocess.run") as mock_subprocess:
        
        # Mock git command success
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "v2.0.0"
        
        response = client().get("/api/version")
        
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"  # Should strip 'v' prefix


def test_get_version_fallback_to_dev():
    """Test fallback to dev when all methods fail"""
    with patch("pathlib.Path.exists", return_value=False), \
         patch("subprocess.run") as mock_subprocess:
        
        # Mock git command failure
        mock_subprocess.return_value.returncode = 1
        
        response = client().get("/api/version")
        
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "dev"


def test_get_version_exception_handling():
    """Test exception handling returns dev"""
    with patch("pathlib.Path.exists", side_effect=Exception("File system error")):
        
        response = client().get("/api/version")
        
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "dev"


def test_get_version_response_structure():
    """Test the response has correct structure"""
    response = client().get("/api/version")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "version" in data
    assert "name" in data
    assert "description" in data
    
    # Check types
    assert isinstance(data["version"], str)
    assert isinstance(data["name"], str)
    assert isinstance(data["description"], str)
    
    # Check values
    assert data["name"] == "PyJOAL"
    assert data["description"] == "Python BitTorrent Ratio Client"