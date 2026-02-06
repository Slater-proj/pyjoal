"""
Tests for API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import tempfile
from pathlib import Path

from app.main import app
from app.services.seeder_service import seeder_service
from app.core.config import settings
from tests.conftest import TEST_SECRET_TOKEN


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authentication headers for testing"""
    return {"X-API-Token": TEST_SECRET_TOKEN}


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    with patch.object(settings, 'SECRET_TOKEN', TEST_SECRET_TOKEN):
        yield


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "PyJOAL"


def test_get_torrents_unauthorized(client):
    """Test torrents endpoint without authentication"""
    response = client.get("/api/torrents")
    assert response.status_code == 401


def test_get_torrents_authorized(client, auth_headers, mock_settings):
    """Test torrents endpoint with authentication"""
    with patch.object(seeder_service, 'get_torrents', return_value=[]):
        response = client.get("/api/torrents", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []


def test_get_config_unauthorized(client):
    """Test config endpoint without authentication"""
    response = client.get("/api/config")
    assert response.status_code == 401


def test_get_config_authorized(client, auth_headers, mock_settings):
    """Test config endpoint with authentication"""
    with patch.object(seeder_service, 'get_config', return_value={
        'minUploadRate': 30,
        'maxUploadRate': 160,
        'simultaneousSeed': 20,
        'client': 'test-client',
        'keepTorrentWithZeroLeechers': True,
        'uploadRatioTarget': -1.0,
        'seedingDurationLimit': -1.0
    }):
        response = client.get("/api/config", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['minUploadRate'] == 30


def test_start_seeding_unauthorized(client):
    """Test start endpoint without authentication"""
    response = client.post("/api/start")
    assert response.status_code == 401


def test_start_seeding_authorized(client, auth_headers, mock_settings):
    """Test start endpoint with authentication"""
    with patch.object(seeder_service, 'start', new_callable=AsyncMock):
        response = client.post("/api/start", headers=auth_headers)
        assert response.status_code == 200


def test_stop_seeding_authorized(client, auth_headers, mock_settings):
    """Test stop endpoint with authentication"""
    with patch.object(seeder_service, 'stop', new_callable=AsyncMock):
        response = client.post("/api/stop", headers=auth_headers)
        assert response.status_code == 200


def test_upload_torrent_unauthorized(client):
    """Test torrent upload without authentication"""
    with tempfile.NamedTemporaryFile(suffix='.torrent') as tmp:
        response = client.post(
            "/api/torrents",
            files={"file": ("test.torrent", tmp, "application/x-bittorrent")}
        )
        assert response.status_code == 401


def test_upload_invalid_file(client, auth_headers, mock_settings):
    """Test uploading non-torrent file"""
    with tempfile.NamedTemporaryFile(suffix='.txt') as tmp:
        tmp.write(b"not a torrent")
        tmp.seek(0)
        response = client.post(
            "/api/torrents",
            files={"file": ("test.txt", tmp, "text/plain")},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "must be a .torrent file" in response.json()["detail"]


def test_get_history_unauthorized(client):
    """Test history endpoint without authentication"""
    response = client.get("/api/history")
    assert response.status_code == 401


def test_get_history_authorized(client, auth_headers, mock_settings):
    """Test history endpoint with authentication"""
    response = client.get("/api/history", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert 'entries' in data
    assert isinstance(data['entries'], list)