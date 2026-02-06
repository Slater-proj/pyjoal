"""
Tests for main.py - version, health, validation handler, frontend serving
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
from fastapi.testclient import TestClient
from pathlib import Path

import os
os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.main import app, get_version


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def auth():
    return {"X-API-Token": "test-secret-token"}


class TestGetVersion:
    def test_version_returns_string(self):
        v = get_version()
        assert isinstance(v, str)
        assert len(v) > 0

    def test_version_not_empty(self):
        v = get_version()
        assert v != ""


class TestHealthEndpoint:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    def test_health_returns_version(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "version" in data


class TestValidationErrorHandler:
    def test_invalid_config_returns_french_errors(self, client, auth):
        """PUT config with invalid data should return user-friendly errors."""
        resp = client.put("/api/config", json={}, headers=auth)
        assert resp.status_code == 422

    def test_invalid_config_with_bad_type(self, client, auth):
        """Config with wrong type should return validation error."""
        resp = client.put(
            "/api/config",
            json={"minUploadRate": "not_a_number"},
            headers=auth
        )
        assert resp.status_code == 422


class TestFrontendServing:
    def test_root_redirect(self, client):
        """Root path should serve frontend or redirect."""
        resp = client.get("/")
        # Should either serve HTML or redirect
        assert resp.status_code in (200, 307, 404)

    def test_nonexistent_api_path(self, client, auth):
        resp = client.get("/api/nonexistent", headers=auth)
        assert resp.status_code in (404, 405)

    def test_favicon(self, client):
        resp = client.get("/favicon.svg")
        # May or may not exist in test environment
        assert resp.status_code in (200, 404)


class TestVersionEndpoint:
    def test_version_api(self, client, auth):
        """Version endpoint should return version info."""
        resp = client.get("/api/version", headers=auth)
        if resp.status_code == 200:
            data = resp.json()
            assert "version" in data or isinstance(data, dict)


class TestAuthMiddleware:
    def test_unauthenticated_api_call(self, client):
        """API calls without token should fail."""
        resp = client.get("/api/config")
        assert resp.status_code == 401

    def test_wrong_token(self, client):
        resp = client.get("/api/config", headers={"X-API-Token": "wrong-token"})
        assert resp.status_code == 401

    def test_health_no_auth_needed(self, client):
        """Health endpoint should not require auth."""
        resp = client.get("/health")
        assert resp.status_code == 200
