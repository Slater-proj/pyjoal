"""Tests for API endpoints — config, system, torrents, notifications."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import os
os.environ.setdefault("SECRET_TOKEN", "test-secret-token")


@pytest.fixture
def client():
    from app.main import app
    from starlette.testclient import TestClient
    return TestClient(app, headers={"X-API-Token": "test-secret-token"})


# ── Config API ──────────────────────────────────────────────────────

class TestConfigAPI:
    def test_update_config_success(self, client):
        with patch("app.api.config.seeder_service") as mock_ss:
            mock_ss.update_config = AsyncMock()
            mock_ss.get_config.return_value = {"minUploadRate": 10}
            resp = client.put("/api/config", json={
                "minUploadRate": 10, "maxUploadRate": 500,
                "simultaneousSeed": 3, "client": "test.client",
                "keepTorrentWithZeroLeechers": True,
                "uploadRatioTarget": -1, "seedingDurationLimit": -1,
            })
        assert resp.status_code == 200

    def test_update_config_value_error(self, client):
        with patch("app.api.config.seeder_service") as mock_ss:
            mock_ss.update_config = AsyncMock(side_effect=ValueError("bad value"))
            resp = client.put("/api/config", json={
                "minUploadRate": 10, "maxUploadRate": 500,
                "simultaneousSeed": 3, "client": "test.client",
                "keepTorrentWithZeroLeechers": True,
                "uploadRatioTarget": -1, "seedingDurationLimit": -1,
            })
        assert resp.status_code == 400

    def test_update_config_permission_error(self, client):
        with patch("app.api.config.seeder_service") as mock_ss:
            mock_ss.update_config = AsyncMock(side_effect=Exception("permission denied"))
            resp = client.put("/api/config", json={
                "minUploadRate": 10, "maxUploadRate": 500,
                "simultaneousSeed": 3, "client": "test.client",
                "keepTorrentWithZeroLeechers": True,
                "uploadRatioTarget": -1, "seedingDurationLimit": -1,
            })
        assert resp.status_code == 500
        assert "permission" in resp.json()["detail"].lower()

    def test_update_config_disk_error(self, client):
        with patch("app.api.config.seeder_service") as mock_ss:
            mock_ss.update_config = AsyncMock(side_effect=Exception("disk space full"))
            resp = client.put("/api/config", json={
                "minUploadRate": 10, "maxUploadRate": 500,
                "simultaneousSeed": 3, "client": "test.client",
                "keepTorrentWithZeroLeechers": True,
                "uploadRatioTarget": -1, "seedingDurationLimit": -1,
            })
        assert resp.status_code == 500
        assert "disk" in resp.json()["detail"].lower()

    def test_update_config_generic_error(self, client):
        with patch("app.api.config.seeder_service") as mock_ss:
            mock_ss.update_config = AsyncMock(side_effect=Exception("something broke"))
            resp = client.put("/api/config", json={
                "minUploadRate": 10, "maxUploadRate": 500,
                "simultaneousSeed": 3, "client": "test.client",
                "keepTorrentWithZeroLeechers": True,
                "uploadRatioTarget": -1, "seedingDurationLimit": -1,
            })
        assert resp.status_code == 500
        assert "Internal" in resp.json()["detail"]

    def test_reset_config(self, client):
        with patch("app.api.config.seeder_service") as mock_ss:
            mock_ss.update_config = AsyncMock()
            resp = client.post("/api/config/reset")
        assert resp.status_code == 200


# ── System API ──────────────────────────────────────────────────────

class TestSystemAPI:
    def test_detailed_health(self, client):
        with patch("app.services.simple_health.health_checker") as mock_hc:
            mock_hc.get_health_status.return_value = {
                "status": "healthy",
                "timestamp": "2025-01-01T00:00:00",
                "uptime_seconds": 300,
                "checks": {
                    "memory": {"value": "50%", "status": "healthy"},
                    "tracker_health": {"message": "OK", "status": "healthy"},
                    "torrent_health": {"message": "OK", "status": "healthy"},
                    "uptime": {"value": "5m", "status": "healthy"},
                },
                "issues": [],
                "suggestions": [],
            }
            resp = client.get("/api/system/health/detailed")
        assert resp.status_code == 200
        assert resp.json()["overall_status"] == "healthy"

    def test_detailed_health_error(self, client):
        with patch("app.services.simple_health.health_checker") as mock_hc:
            mock_hc.get_health_status.side_effect = RuntimeError("boom")
            resp = client.get("/api/system/health/detailed")
        assert resp.status_code == 500

    def test_simple_health_status(self, client):
        with patch("app.services.simple_health.health_checker") as mock_hc:
            mock_hc.get_health_status.return_value = {
                "status": "warning",
                "checks": {"uptime": {"value": "10m"}},
                "issues": ["Memory high"],
                "suggestions": [],
            }
            resp = client.get("/api/system/health/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "warning"

    def test_simple_health_status_no_issues(self, client):
        with patch("app.services.simple_health.health_checker") as mock_hc:
            mock_hc.get_health_status.return_value = {
                "status": "healthy",
                "checks": {"uptime": {"value": "1h"}},
                "issues": [],
                "suggestions": [],
            }
            resp = client.get("/api/system/health/status")
        assert resp.status_code == 200
        assert "fonctionnel" in resp.json()["message"]

    def test_simple_health_status_exception(self, client):
        with patch("app.services.simple_health.health_checker") as mock_hc:
            mock_hc.get_health_status.side_effect = RuntimeError("fail")
            resp = client.get("/api/system/health/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

    def test_version_check(self, client):
        with patch("app.services.version_checker.version_checker") as mock_vc:
            mock_vc.get_version_info = AsyncMock(return_value={
                "current_version": "1.12.1",
                "latest_version": "1.12.1",
                "update_available": False,
                "release_url": "",
                "release_notes": "",
                "published_at": "",
                "last_check": "2025-01-01T00:00:00",
            })
            resp = client.get("/api/system/version/check")
        assert resp.status_code == 200
        assert resp.json()["update_available"] is False
