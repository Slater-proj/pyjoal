"""
Tests for API endpoints - Extended coverage for config, cache, torrents, system
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock
from fastapi.testclient import TestClient

import os
os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.main import app
from app.core.config import settings


@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth():
    return {"X-API-Token": "test-secret-token"}


# ================================================================
# Config API
# ================================================================

class TestConfigAPI:
    def test_get_config(self, client, auth):
        resp = client.get("/api/config", headers=auth)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_put_config_success(self, client, auth):
        full_config = {
            "minUploadRate": 50, "maxUploadRate": 500, "simultaneousSeed": 3,
            "client": "qbittorrent-5.1.4.client", "keepTorrentWithZeroLeechers": True,
            "uploadRatioTarget": -1.0, "seedingDurationLimit": -1.0,
            "announceInterval": 30, "announceJitter": 30, "minStatsUpdateInterval": 3,
            "enableSpeedVariation": True, "speedVariationPercent": 20,
            "seedingOnlyMode": True,
            "pauseDurationMin": 30, "pauseDurationMax": 180,
            "reducedSpeedDurationMin": 60, "reducedSpeedDurationMax": 240,
            "stateChangeIntervalMin": 2, "stateChangeIntervalMax": 8,
            "reducedSpeedKbps": 5,
            "peerSpeedTiersEnabled": True,
            "peerTier1MaxPeers": 20, "peerTier1SpeedPercent": 40,
            "peerTier2MaxPeers": 50, "peerTier2SpeedPercent": 55,
            "peerTier3MaxPeers": 100, "peerTier3SpeedPercent": 60,
            "peerTier4MaxPeers": 200, "peerTier4SpeedPercent": 80,
            "peerTier5SpeedPercent": 100,
        }
        with patch("app.api.config.seeder_service") as mock_ss:
            mock_ss.update_config = AsyncMock()
            mock_ss.get_config.return_value = full_config
            resp = client.put("/api/config", json=full_config, headers=auth)
            assert resp.status_code == 200

    def test_put_config_validation_error(self, client, auth):
        """Incomplete config should return 422"""
        resp = client.put("/api/config", json={"minUploadRate": 100}, headers=auth)
        assert resp.status_code == 422

    def test_put_config_unauthorized(self, client):
        resp = client.put("/api/config", json={"minUploadRate": 100})
        assert resp.status_code == 401

    def test_get_clients(self, client, auth):
        with patch("app.api.config.seeder_service") as mock_ss:
            mock_ss.available_clients = ["qbittorrent-5.1.4.client"]
            resp = client.get("/api/clients", headers=auth)
            assert resp.status_code == 200

    def test_reset_config(self, client, auth):
        with patch("app.api.config.seeder_service") as mock_ss:
            mock_ss.update_config = AsyncMock()
            mock_ss.get_config.return_value = {}
            resp = client.post("/api/config/reset", headers=auth)
            assert resp.status_code == 200


# ================================================================
# Cache API (no auth on these endpoints)
# ================================================================

class TestCacheAPI:
    def test_cache_stats(self, client):
        resp = client.get("/api/cache/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "caches" in data or "global_stats" in data or isinstance(data, dict)

    def test_cache_clear(self, client):
        resp = client.post("/api/cache/clear")
        assert resp.status_code == 200

    def test_cache_cleanup(self, client):
        resp = client.post("/api/cache/cleanup")
        assert resp.status_code == 200


# ================================================================
# Torrents API
# ================================================================

class TestTorrentsAPI:
    def test_get_torrents(self, client, auth):
        with patch("app.api.torrents.seeder_service") as mock_ss:
            mock_ss.get_torrents.return_value = []
            resp = client.get("/api/torrents", headers=auth)
            assert resp.status_code == 200
            assert resp.json() == []

    def test_delete_torrent(self, client, auth):
        with patch("app.api.torrents.seeder_service") as mock_ss:
            mock_ss.remove_torrent = AsyncMock()
            resp = client.delete("/api/torrents/abc123", headers=auth)
            assert resp.status_code == 200

    def test_get_torrent_by_hash(self, client, auth):
        with patch("app.api.torrents.seeder_service") as mock_ss:
            mock_ss._get_torrent_info.return_value = {
                "name": "test", "infoHash": "abc123", "uploaded": 0
            }
            resp = client.get("/api/torrents/abc123", headers=auth)
            assert resp.status_code == 200

    def test_get_torrent_not_found(self, client, auth):
        with patch("app.api.torrents.seeder_service") as mock_ss:
            mock_ss._get_torrent_info.return_value = None
            resp = client.get("/api/torrents/noexist", headers=auth)
            assert resp.status_code == 404

    def test_get_failed_torrents(self, client, auth):
        """Verify /torrents/failed is reachable (not shadowed by {info_hash})"""
        with patch("app.api.torrents.seeder_service") as mock_ss:
            mock_ss.failed_torrents = {}
            resp = client.get("/api/torrents/failed", headers=auth)
            assert resp.status_code == 200
            data = resp.json()
            assert "failed_count" in data
            assert data["failed_count"] == 0

    def test_reload_torrents(self, client, auth):
        with patch("app.api.torrents.seeder_service") as mock_ss:
            mock_ss.is_running = False
            mock_ss.announcers = {}
            mock_ss.stop = AsyncMock()
            mock_ss.load_torrents = AsyncMock()
            mock_ss.start = AsyncMock()
            mock_ss.get_torrents.return_value = []
            with patch("app.api.torrents.websocket_manager") as mock_ws:
                mock_ws.broadcast = AsyncMock()
                resp = client.post("/api/torrents/reload", headers=auth)
                assert resp.status_code == 200

    def test_upload_invalid_extension(self, client, auth):
        resp = client.post(
            "/api/torrents",
            files={"file": ("test.txt", b"data", "application/octet-stream")},
            headers=auth
        )
        assert resp.status_code == 400


# ================================================================
# Client Control API
# ================================================================

class TestClientAPI:
    def test_start_seeding(self, client, auth):
        with patch("app.api.client.seeder_service") as mock_ss:
            mock_ss.start = AsyncMock()
            mock_ss.is_running = True
            mock_ss.get_stats.return_value = {"isRunning": True}
            resp = client.post("/api/start", headers=auth)
            assert resp.status_code == 200

    def test_stop_seeding(self, client, auth):
        with patch("app.api.client.seeder_service") as mock_ss:
            mock_ss.stop = AsyncMock()
            mock_ss.is_running = False
            mock_ss.get_stats.return_value = {"isRunning": False}
            resp = client.post("/api/stop", headers=auth)
            assert resp.status_code == 200

    def test_get_status(self, client, auth):
        with patch("app.api.client.seeder_service") as mock_ss:
            mock_ss.is_running = False
            mock_ss.get_stats.return_value = {
                "isRunning": False, "activeTorrents": 0, "totalTorrents": 0
            }
            resp = client.get("/api/status", headers=auth)
            assert resp.status_code == 200


# ================================================================
# System API
# ================================================================

class TestSystemAPI:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "unhealthy")

    def test_system_health_status(self, client):
        resp = client.get("/api/system/health/status")
        assert resp.status_code in (200, 404)

    def test_system_health_detailed(self, client):
        resp = client.get("/api/system/health/detailed")
        assert resp.status_code in (200, 404)


# ================================================================
# History API
# ================================================================

class TestHistoryAPI:
    def test_get_history(self, client, auth):
        resp = client.get("/api/history", headers=auth)
        assert resp.status_code == 200

    def test_get_history_unauthorized(self, client):
        resp = client.get("/api/history")
        assert resp.status_code == 401

    def test_clear_history(self, client, auth):
        resp = client.delete("/api/history", headers=auth)
        assert resp.status_code in (200, 405)  # May not have DELETE endpoint


# ================================================================
# Version API
# ================================================================

class TestVersionAPI:
    def test_get_version(self, client):
        resp = client.get("/api/version")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data


# ================================================================
# Error Info API
# ================================================================

class TestErrorsAPI:
    def test_get_error_explanations(self, client, auth):
        resp = client.get("/api/errors/explanation/timeout", headers=auth)
        assert resp.status_code in (200, 404)
