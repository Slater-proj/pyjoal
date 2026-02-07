"""
Extended tests for seeder_service - config updates, caching, stats, persistence
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock
from datetime import datetime, timezone

import os
os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.services.seeder_service import SeederService


def _make_service():
    """Create a SeederService with mocked internals."""
    svc = SeederService.__new__(SeederService)
    svc.is_running = False
    # Mock the delegates that properties forward to
    svc._tm = MagicMock()
    svc._tm.announcers = {}
    svc._tm.failed_torrents = {}
    svc._cfg = MagicMock()
    svc._cfg.config = {}
    svc._cfg._config = {}
    svc.client = None
    svc._lock = asyncio.Lock()
    svc._monitor_task = None
    svc._stats_cache = None
    svc._stats_cache_time = 0
    svc._torrents_cache = None
    svc._torrents_cache_time = 0
    svc.started_at = None
    svc.available_clients = []
    return svc


def _mock_announcer(info_hash="abc123", uploaded=1024, speed=50000,
                     running=True, seeders=5, leechers=3):
    ann = MagicMock()
    ann.info_hash = info_hash
    ann.torrent = MagicMock()
    ann.torrent.name = "test.torrent"
    ann.torrent.size = 1024 * 1024
    ann.torrent.info_hash = info_hash
    ann.torrent.added_at = datetime.now(timezone.utc)
    ann.torrent.primary_tracker = "http://tracker.example.com"
    ann.torrent.created_by = "test"
    ann.is_running = running
    ann.uploaded = uploaded
    ann.upload_speed = speed
    ann.stats = MagicMock()
    ann.stats.uploaded = uploaded
    ann.stats.upload_speed = speed
    ann.stats.ratio = 1.0
    ann.stats.seeders = seeders
    ann.stats.leechers = leechers
    ann.seeders = seeders
    ann.leechers = leechers
    ann.get_stats = MagicMock(return_value={
        "uploaded": uploaded,
        "uploadSpeed": speed,
        "ratio": 1.0,
        "seeders": seeders,
        "leechers": leechers,
        "lastAnnounce": datetime.now(timezone.utc),
        "nextAnnounce": datetime.now(timezone.utc),
        "seedingTime": 3600,
        "lastError": None,
        "errorCount": 0,
        "lastErrorTime": None,
        "isHealthy": True,
        "status": {"status": "seeding"},
    })
    ann.stop = AsyncMock()
    ann.start = AsyncMock()
    return ann


class TestSeederServiceStats:
    def test_get_stats_empty(self):
        svc = _make_service()
        stats = svc.get_stats()
        assert isinstance(stats, dict)
        assert stats["isRunning"] is False

    def test_get_stats_with_announcers(self):
        svc = _make_service()
        svc.is_running = True
        svc.started_at = datetime.now(timezone.utc)
        svc.announcers = {
            "abc": _mock_announcer(uploaded=1024, speed=50000, running=True),
            "def": _mock_announcer(info_hash="def456", uploaded=2048, speed=25000, running=True),
        }
        stats = svc.get_stats()
        assert stats["isRunning"] is True
        assert stats["activeTorrents"] == 2

    def test_get_stats_mixed_running(self):
        svc = _make_service()
        svc.is_running = True
        svc.started_at = datetime.now(timezone.utc)
        svc.announcers = {
            "abc": _mock_announcer(running=True),
            "def": _mock_announcer(info_hash="def456", running=False),
        }
        stats = svc.get_stats()
        assert stats["activeTorrents"] >= 1


class TestSeederServiceConfig:
    def test_get_config(self):
        svc = _make_service()
        svc._config = {"minUploadRate": 50, "maxUploadRate": 500}
        config = svc.get_config()
        assert isinstance(config, dict)

    def test_has_torrents_empty(self):
        svc = _make_service()
        # Mock the TorrentManager
        svc._tm = MagicMock()
        svc._tm.has_torrents.return_value = False
        assert svc.has_torrents() is False

    def test_has_torrents_with_data(self):
        svc = _make_service()
        svc._tm = MagicMock()
        svc._tm.has_torrents.return_value = True
        assert svc.has_torrents() is True


class TestSeederServiceStartStop:
    @pytest.mark.asyncio
    async def test_start_already_running(self):
        svc = _make_service()
        svc.is_running = True
        # Should be a no-op
        await svc.start()
        assert svc.is_running is True

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        svc = _make_service()
        svc.is_running = False
        # Should be a no-op
        await svc.stop()
        assert svc.is_running is False


class TestPersistStats:
    def test_persist_all_stats(self):
        svc = _make_service()
        svc.announcers = {
            "abc": _mock_announcer(uploaded=1024),
        }
        with patch("app.services.seeder_service.persistence_service") as mock_ps:
            svc._persist_all_stats()
            mock_ps.update.assert_called()


class TestGetTorrents:
    def test_get_torrents_empty(self):
        svc = _make_service()
        svc._tm = MagicMock()
        svc._tm.get_torrents.return_value = []
        result = svc.get_torrents()
        assert result == []

    def test_get_torrents_with_data(self):
        svc = _make_service()
        svc._tm = MagicMock()
        svc._tm.get_torrents.return_value = [{"name": "test"}]
        result = svc.get_torrents()
        assert len(result) == 1
