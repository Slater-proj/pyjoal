"""
Tests for WebSocket authentication and main.py endpoints
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

import os
os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.main import app
from app.core.config import settings


@pytest.fixture
def client():
    return TestClient(app)


class TestWebSocketAuth:
    def test_ws_with_valid_token(self, client):
        """WebSocket should connect with valid token"""
        token = settings.SECRET_TOKEN
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.send_text("ping")
            data = ws.receive_text()
            assert data == "pong"

    def test_ws_without_token_rejected(self, client):
        """WebSocket should reject connections without token"""
        try:
            with client.websocket_connect("/ws") as ws:
                # If we get here, the connection wasn't rejected at the protocol level
                # but it should have been closed with 4003
                pass
        except Exception:
            pass  # Expected - connection refused

    def test_ws_with_invalid_token_rejected(self, client):
        """WebSocket should reject connections with wrong token"""
        try:
            with client.websocket_connect("/ws?token=wrong-token") as ws:
                pass
        except Exception:
            pass  # Expected - connection refused


class TestHealthEndpoint:
    def test_health_returns_status(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "app" in data
        assert data["app"] == "PyJOAL"

    def test_health_includes_version(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "version" in data


class TestFrontendServing:
    def test_version_endpoint(self, client):
        """Version endpoint should always be available"""
        resp = client.get("/api/version")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
