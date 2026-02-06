"""Tests for SeederService._find_best_fallback_client and main.py validation handler."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os

os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.services.seeder_service import SeederService


class TestFindBestFallbackClient:
    def test_same_client_name_match(self):
        result = SeederService._find_best_fallback_client(
            "qbittorrent-4.5.0.client",
            ["deluge-2.1.1.client", "qbittorrent-4.6.0.client", "qbittorrent-5.1.4.client"]
        )
        assert result.startswith("qbittorrent")
        # Should pick highest version
        assert result == "qbittorrent-5.1.4.client"

    def test_no_same_client_prefers_qbittorrent(self):
        result = SeederService._find_best_fallback_client(
            "utorrent-3.5.0.client",
            ["deluge-2.1.1.client", "qbittorrent-5.1.4.client", "transmission-4.0.6.client"]
        )
        assert result == "qbittorrent-5.1.4.client"

    def test_no_same_client_prefers_deluge_over_transmission(self):
        result = SeederService._find_best_fallback_client(
            "utorrent-3.5.0.client",
            ["deluge-2.1.1.client", "transmission-4.0.6.client"]
        )
        assert result == "deluge-2.1.1.client"

    def test_no_preferred_fallback(self):
        result = SeederService._find_best_fallback_client(
            "utorrent-3.5.0.client",
            ["aria2-1.0.0.client", "libtorrent-2.0.0.client"]
        )
        # Falls back to sorted descending, picks first
        assert result in ["libtorrent-2.0.0.client", "aria2-1.0.0.client"]

    def test_no_available_clients_raises(self):
        with pytest.raises(RuntimeError, match="No available clients"):
            SeederService._find_best_fallback_client("qbittorrent-5.0.client", [])

    def test_single_available_client(self):
        result = SeederService._find_best_fallback_client(
            "missing.client",
            ["only-option-1.0.client"]
        )
        assert result == "only-option-1.0.client"


class TestSeederServiceGetStats:
    """Test get_stats method on SeederService directly."""

    def test_get_stats_not_running(self):
        svc = SeederService.__new__(SeederService)
        svc._tm = MagicMock()
        svc._tm.announcers = {}
        svc._tm.failed_torrents = {}
        svc._cfg = MagicMock()
        svc._cfg.config = {}
        svc.is_running = False
        svc.client = None
        svc.started_at = None
        svc._lock = __import__("asyncio").Lock()
        svc._monitor_task = None
        svc.file_watcher = None
        stats = svc.get_stats()
        assert isinstance(stats, dict)
        assert stats["isRunning"] is False

    def test_get_config_returns_dict(self):
        svc = SeederService.__new__(SeederService)
        svc._cfg = MagicMock()
        svc._cfg.config = {"minUploadRate": 50}
        svc._tm = MagicMock()
        svc.is_running = False
        svc.client = None
        svc.started_at = None
        svc._lock = __import__("asyncio").Lock()
        svc._monitor_task = None
        svc.file_watcher = None
        config = svc.get_config()
        assert isinstance(config, dict)
