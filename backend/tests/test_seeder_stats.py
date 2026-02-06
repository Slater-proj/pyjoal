"""Tests for SeederService.get_stats, get_stats_cached, update_config, backoff."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
import asyncio
import os

os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.services.seeder_service import SeederService


def _make_svc():
    svc = SeederService.__new__(SeederService)
    svc._tm = MagicMock()
    svc._tm.announcers = {}
    svc._tm.failed_torrents = {}
    svc._tm.get_torrents.return_value = []
    svc._tm.has_torrents.return_value = False
    svc._cfg = MagicMock()
    svc._cfg.config = {}
    svc._cfg._config = {}
    svc.is_running = False
    svc.client = None
    svc._monitor_task = None
    svc._lock = asyncio.Lock()
    svc.started_at = None
    svc.file_watcher = None
    return svc


def _mock_ann(uploaded=1024, speed=50000, running=True):
    ann = MagicMock()
    ann.uploaded = uploaded
    ann.upload_speed = speed
    ann.is_running = running
    ann.info_hash = "abc123"
    ann.torrent = MagicMock()
    ann.torrent.name = "test.torrent"
    ann.torrent.size = 1024 * 1024
    ann.torrent.info_hash = "abc123"
    ann.get_stats.return_value = {
        "uploaded": uploaded, "uploadSpeed": speed,
        "ratio": 1.0, "seeders": 5, "leechers": 3,
    }
    ann.stop = AsyncMock()
    return ann


class TestGetStats:
    def test_not_running(self):
        svc = _make_svc()
        stats = svc.get_stats()
        assert stats["isRunning"] is False
        assert stats["activeTorrents"] == 0
        assert stats["totalTorrents"] == 0
        assert stats["uploadSpeed"] == 0
        assert stats["startedAt"] is None

    def test_running_with_torrents(self):
        svc = _make_svc()
        svc.is_running = True
        svc.started_at = datetime.now(timezone.utc)
        svc._tm.announcers = {
            "a": _mock_ann(uploaded=1000, speed=50000, running=True),
            "b": _mock_ann(uploaded=2000, speed=25000, running=True),
            "c": _mock_ann(uploaded=500, speed=0, running=False),
        }
        stats = svc.get_stats()
        assert stats["isRunning"] is True
        assert stats["activeTorrents"] == 2
        assert stats["totalTorrents"] == 3
        assert stats["totalUploaded"] == 3500
        assert stats["uploadSpeed"] == 75000
        assert stats["uptime"] is not None
        assert stats["uptime"] >= 0

    def test_started_at_format(self):
        svc = _make_svc()
        svc.is_running = True
        svc.started_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        stats = svc.get_stats()
        assert "2024" in stats["startedAt"]


class TestGetStatsCached:
    def test_cache_miss(self):
        svc = _make_svc()
        with patch("app.services.seeder_service.cache_manager") as mock_cm:
            mock_cm.get_aggregated_stats.return_value = None
            stats = svc.get_stats_cached()
        assert isinstance(stats, dict)
        mock_cm.set_aggregated_stats.assert_called_once()

    def test_cache_hit(self):
        svc = _make_svc()
        cached = {"isRunning": True, "cached": True}
        with patch("app.services.seeder_service.cache_manager") as mock_cm:
            mock_cm.get_aggregated_stats.return_value = cached
            stats = svc.get_stats_cached()
        assert stats["cached"] is True


class TestGetTorrentsCached:
    def test_cache_miss(self):
        svc = _make_svc()
        with patch("app.services.seeder_service.cache_manager") as mock_cm:
            mock_cm.get_aggregated_stats.return_value = None
            result = svc.get_torrents_cached()
        assert isinstance(result, list)

    def test_cache_hit(self):
        svc = _make_svc()
        with patch("app.services.seeder_service.cache_manager") as mock_cm:
            mock_cm.get_aggregated_stats.return_value = [{"name": "cached"}]
            result = svc.get_torrents_cached()
        assert len(result) == 1


class TestUpdateConfig:
    @pytest.mark.asyncio
    async def test_update_config_basic(self):
        svc = _make_svc()
        svc._cfg.config = {"minUploadRate": 50}
        svc._cfg._config = {"minUploadRate": 50}
        svc._cfg.save = AsyncMock()
        new_config = {"minUploadRate": 100}
        with patch("app.services.seeder_service.history_service"), \
             patch("app.services.seeder_service.settings") as mock_settings:
            mock_settings.MIN_UPLOAD_RATE = 50
            await svc.update_config(new_config)
        svc._cfg.validate.assert_called_once_with(new_config)
        svc._cfg.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_config_save_failure_rollback(self):
        svc = _make_svc()
        svc._cfg.config = {"minUploadRate": 50}
        svc._cfg._config = {"minUploadRate": 50}
        svc._cfg.save = AsyncMock(side_effect=Exception("disk full"))
        with pytest.raises(Exception, match="disk full"):
            await svc.update_config({"minUploadRate": 200})


class TestBackoffDelay:
    def test_calculate_backoff_basic(self):
        from app.core.tracker_announcer import TrackerAnnouncer
        ann = TrackerAnnouncer.__new__(TrackerAnnouncer)
        ann.base_retry_delay = 30
        ann.consecutive_failures = 1
        delay = ann._calculate_backoff_delay()
        assert 20 <= delay <= 40  # 30 * 2^0 * jitter(0.8-1.2)

    def test_calculate_backoff_exponential(self):
        from app.core.tracker_announcer import TrackerAnnouncer
        ann = TrackerAnnouncer.__new__(TrackerAnnouncer)
        ann.base_retry_delay = 30
        ann.consecutive_failures = 3
        delay = ann._calculate_backoff_delay()
        # 30 * 2^2 = 120, * jitter => 96-144
        assert delay >= 80
        assert delay <= 200

    def test_calculate_backoff_capped(self):
        from app.core.tracker_announcer import TrackerAnnouncer
        ann = TrackerAnnouncer.__new__(TrackerAnnouncer)
        ann.base_retry_delay = 30
        ann.consecutive_failures = 10  # 30 * 2^9 = 15360, capped to 300
        delay = ann._calculate_backoff_delay()
        assert delay <= 360  # 300 * 1.2
