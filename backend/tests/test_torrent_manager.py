"""
Tests for TorrentManager - load, add, remove, archive, ratio checking
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock, mock_open
from pathlib import Path
from datetime import datetime, timezone, timedelta

import os
os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.services.torrent_manager import TorrentManager


def _make_tm():
    """Create a TorrentManager with mocked dependencies."""
    tm = TorrentManager.__new__(TorrentManager)
    tm.announcers = {}
    tm.failed_torrents = {}
    tm._client = None
    return tm


def _mock_announcer(info_hash="abc123", name="test.torrent", uploaded=1024,
                     downloaded=0, left=0, is_running=True, ratio=1.0,
                     seeders=5, leechers=3, started_at=None):
    ann = MagicMock()
    ann.info_hash = info_hash
    ann.torrent = MagicMock()
    ann.torrent.name = name
    ann.torrent.size = 1024 * 1024
    ann.torrent.total_size = 1024 * 1024
    ann.torrent.info_hash = info_hash
    ann.torrent.file_path = Path(f"/tmp/{name}")
    ann.torrent.added_at = datetime.now(timezone.utc)
    ann.torrent.primary_tracker = "http://tracker.example.com/announce"
    ann.torrent.created_by = "test"
    ann.get_stats.return_value = {
        "uploaded": uploaded,
        "downloaded": downloaded,
        "left": left,
        "uploadSpeed": 50000,
        "downloadSpeed": 0,
        "seeders": seeders,
        "leechers": leechers,
        "ratio": ratio,
        "lastAnnounce": datetime.now(timezone.utc),
        "nextAnnounce": datetime.now(timezone.utc),
        "seedingTime": 3600,
        "lastError": None,
        "errorCount": 0,
        "lastErrorTime": None,
        "isHealthy": True,
        "status": {"status": "seeding", "speed_tier": "medium"},
    }
    ann.stats = MagicMock()
    ann.stats.uploaded = uploaded
    ann.stats.ratio = ratio
    ann.is_running = is_running
    ann.started_at = started_at or datetime.now(timezone.utc)
    ann.last_announce_time = datetime.now(timezone.utc)
    ann.error_count = 0
    ann.last_error = None
    ann.stop = AsyncMock()
    ann.start = AsyncMock()
    return ann


class TestTorrentManagerBasics:
    def test_has_torrents_empty(self):
        tm = _make_tm()
        assert tm.has_torrents() is False

    def test_has_torrents_with_data(self):
        tm = _make_tm()
        tm.announcers = {"abc": _mock_announcer()}
        assert tm.has_torrents() is True

    def test_get_torrents_empty(self):
        tm = _make_tm()
        result = tm.get_torrents()
        assert result == []

    def test_get_torrent_info_found(self):
        tm = _make_tm()
        ann = _mock_announcer()
        tm.announcers = {"abc123": ann}
        info = tm._get_torrent_info("abc123")
        assert isinstance(info, dict)
        assert info["id"] == "abc123"

    def test_get_torrent_info_not_found(self):
        tm = _make_tm()
        result = tm.get_torrent_info("nonexistent")
        assert result == {} or result is None


class TestTorrentManagerRemove:
    @pytest.mark.asyncio
    async def test_remove_torrent_success(self):
        tm = _make_tm()
        ann = _mock_announcer()
        tm.announcers = {"abc123": ann}

        with patch("app.services.torrent_manager.websocket_manager") as mock_ws, \
             patch("app.services.torrent_manager.settings") as mock_settings:
            mock_ws.broadcast = AsyncMock()
            mock_settings.TORRENTS_DIR = Path("/tmp/torrents")
            mock_settings.ARCHIVED_DIR = Path("/tmp/archived")

            with patch.object(Path, "exists", return_value=True), \
                 patch.object(Path, "rename"), \
                 patch.object(Path, "mkdir"):
                await tm.remove_torrent("abc123")

        assert "abc123" not in tm.announcers
        ann.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_torrent_not_found(self):
        tm = _make_tm()
        # Should not raise, just log warning
        await tm.remove_torrent("nonexistent")
        assert "nonexistent" not in tm.announcers


class TestCheckRatioTargets:
    @pytest.mark.asyncio
    async def test_check_ratio_no_targets(self):
        """When uploadRatioTarget is -1, no torrents should be archived."""
        tm = _make_tm()
        config = {"uploadRatioTarget": -1, "seedingDurationLimit": -1}
        ann = _mock_announcer(ratio=5.0)
        tm.announcers = {"abc123": ann}

        with patch.object(tm, "archive_torrent", new_callable=AsyncMock) as mock_archive:
            await tm.check_ratio_targets(config)
            mock_archive.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_ratio_target_reached(self):
        """Torrent exceeding ratio target should be archived."""
        tm = _make_tm()
        config = {"uploadRatioTarget": 2.0, "seedingDurationLimit": -1}
        ann = _mock_announcer(ratio=2.5)
        tm.announcers = {"abc123": ann}

        with patch.object(tm, "archive_torrent", new_callable=AsyncMock) as mock_archive:
            await tm.check_ratio_targets(config)
            mock_archive.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_duration_limit_reached(self):
        """Torrent exceeding seeding duration should be archived."""
        tm = _make_tm()
        config = {"uploadRatioTarget": -1, "seedingDurationLimit": 1.0}  # 1 hour
        ann = _mock_announcer(
            started_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        tm.announcers = {"abc123": ann}

        with patch.object(tm, "archive_torrent", new_callable=AsyncMock) as mock_archive:
            await tm.check_ratio_targets(config)
            mock_archive.assert_called_once()


class TestGetTorrentInfoDetailed:
    def test_torrent_info_active(self):
        tm = _make_tm()
        ann = _mock_announcer(is_running=True)
        tm.announcers = {"abc123": ann}
        info = tm._get_torrent_info("abc123")
        assert info["id"] == "abc123"
        assert info["uploaded"] == 1024

    def test_torrent_info_stopped(self):
        tm = _make_tm()
        ann = _mock_announcer(is_running=False)
        tm.announcers = {"abc123": ann}
        info = tm._get_torrent_info("abc123")
        assert info["id"] == "abc123"
        assert info["simpleStatus"] == "STOPPED"
