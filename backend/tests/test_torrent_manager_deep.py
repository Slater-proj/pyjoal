"""Deep tests for TorrentManager - load_torrents, add_torrent, archive, check_ratio_targets."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from datetime import datetime, timezone
from pathlib import Path
import os

os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.services.torrent_manager import TorrentManager


def _make_tm():
    """Build TorrentManager with empty state."""
    tm = TorrentManager()
    tm.announcers = {}
    tm.failed_torrents = {}
    return tm


def _mock_torrent(name="test.torrent", info_hash="abc123", size=1024*1024):
    t = MagicMock()
    t.name = name
    t.info_hash = info_hash
    t.size = size
    t.path = MagicMock()
    t.path.name = name
    t.path.exists.return_value = True
    t.trackers = ["http://tracker.example.com/announce"]
    t.primary_tracker = "http://tracker.example.com/announce"
    t.added_at = datetime.now(timezone.utc)
    t.created_by = "test"
    return t


def _mock_announcer(info_hash="abc123", uploaded=1024, running=True,
                     ratio=1.0, seeding_time=3600, seeders=5, leechers=3):
    ann = MagicMock()
    ann.info_hash = info_hash
    ann.is_running = running
    ann.torrent = _mock_torrent(info_hash=info_hash)
    ann.stop = AsyncMock()
    ann.start = AsyncMock()
    ann.get_stats.return_value = {
        "uploaded": uploaded,
        "uploadSpeed": 50000,
        "ratio": ratio,
        "seeders": seeders,
        "leechers": leechers,
        "seedingTime": seeding_time,
        "lastAnnounce": datetime.now(timezone.utc),
        "nextAnnounce": datetime.now(timezone.utc),
        "lastError": None,
        "errorCount": 0,
        "lastErrorTime": None,
        "isHealthy": True,
    }
    ann.stats = MagicMock()
    ann.stats.uploaded = uploaded
    return ann


# ── check_ratio_targets ────────────────────────────────────────────────

class TestCheckRatioTargets:
    @pytest.mark.asyncio
    async def test_no_targets(self):
        tm = _make_tm()
        tm.announcers = {"abc": _mock_announcer()}
        config = {"uploadRatioTarget": -1.0, "seedingDurationLimit": -1.0}
        with patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())):
            await tm.check_ratio_targets(config)
        assert "abc" in tm.announcers  # not removed

    @pytest.mark.asyncio
    async def test_ratio_target_reached(self):
        tm = _make_tm()
        tm.announcers = {"abc": _mock_announcer(ratio=2.5)}
        config = {"uploadRatioTarget": 2.0, "seedingDurationLimit": -1.0}
        with patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())), \
             patch("app.services.torrent_manager.persistence_service") as mock_ps, \
             patch("app.services.torrent_manager.notification_service", MagicMock(notify_torrent_archived=AsyncMock())), \
             patch("app.services.torrent_manager.history_service"):
            await tm.check_ratio_targets(config)
        assert "abc" not in tm.announcers  # should be archived

    @pytest.mark.asyncio
    async def test_duration_limit_reached(self):
        tm = _make_tm()
        # seeding_time = 7200s = 2h, limit = 1h
        tm.announcers = {"abc": _mock_announcer(seeding_time=7200, ratio=0.5)}
        config = {"uploadRatioTarget": -1.0, "seedingDurationLimit": 1.0}
        with patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())), \
             patch("app.services.torrent_manager.persistence_service") as mock_ps, \
             patch("app.services.torrent_manager.notification_service", MagicMock(notify_torrent_archived=AsyncMock())), \
             patch("app.services.torrent_manager.history_service"):
            await tm.check_ratio_targets(config)
        assert "abc" not in tm.announcers

    @pytest.mark.asyncio
    async def test_no_peers_removal(self):
        tm = _make_tm()
        # seeders=0, leechers=0, seeding_time > grace period
        tm.announcers = {"abc": _mock_announcer(seeders=0, leechers=0, seeding_time=600)}
        config = {"uploadRatioTarget": -1.0, "seedingDurationLimit": -1.0, "keepTorrentWithZeroLeechers": False}
        with patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())), \
             patch("app.services.torrent_manager.persistence_service") as mock_ps, \
             patch("app.services.torrent_manager.notification_service", MagicMock(notify_torrent_archived=AsyncMock())), \
             patch("app.services.torrent_manager.history_service"):
            await tm.check_ratio_targets(config)
        assert "abc" not in tm.announcers

    @pytest.mark.asyncio
    async def test_no_peers_grace_period(self):
        tm = _make_tm()
        # seeders=0, leechers=0, but seeding_time < grace period
        tm.announcers = {"abc": _mock_announcer(seeders=0, leechers=0, seeding_time=60)}
        config = {"uploadRatioTarget": -1.0, "seedingDurationLimit": -1.0, "keepTorrentWithZeroLeechers": False}
        with patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())):
            await tm.check_ratio_targets(config)
        assert "abc" in tm.announcers  # grace period, not removed


# ── archive_torrent ─────────────────────────────────────────────────────

class TestArchiveTorrent:
    @pytest.mark.asyncio
    async def test_archive_basic(self):
        tm = _make_tm()
        ann = _mock_announcer(running=True)
        tm.announcers = {"abc123": ann}
        with patch("app.services.torrent_manager.persistence_service") as mock_ps, \
             patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())), \
             patch("app.services.torrent_manager.notification_service", MagicMock(notify_torrent_archived=AsyncMock())), \
             patch("app.services.torrent_manager.history_service"):
            await tm.archive_torrent("abc123")
        assert "abc123" not in tm.announcers
        ann.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_archive_nonexistent(self):
        tm = _make_tm()
        with patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())):
            await tm.archive_torrent("nonexistent")
        # Should not raise

    @pytest.mark.asyncio
    async def test_archive_with_history(self):
        tm = _make_tm()
        ann = _mock_announcer(running=False)
        tm.announcers = {"abc123": ann}
        with patch("app.services.torrent_manager.persistence_service"), \
             patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())), \
             patch("app.services.torrent_manager.notification_service", MagicMock(notify_torrent_archived=AsyncMock())), \
             patch("app.services.torrent_manager.history_service") as mock_hs:
            await tm.archive_torrent("abc123", skip_history=False)
        mock_hs.add_entry.assert_called()


# ── add_torrent ─────────────────────────────────────────────────────────

class TestAddTorrent:
    @pytest.mark.asyncio
    async def test_add_new_torrent(self):
        tm = _make_tm()
        torrent = _mock_torrent()
        client = MagicMock()
        config = {"announceInterval": 1800}
        with patch("app.services.torrent_manager.TrackerAnnouncer") as MockAnn, \
             patch("app.services.torrent_manager.persistence_service") as mock_ps, \
             patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())), \
             patch("app.services.torrent_manager.history_service"):
            mock_ps.get.return_value = None
            MockAnn.return_value = MagicMock()
            MockAnn.return_value.stats = MagicMock()
            await tm.add_torrent(torrent, client, config, is_running=False)
        assert torrent.info_hash in tm.announcers

    @pytest.mark.asyncio
    async def test_add_duplicate_torrent(self):
        tm = _make_tm()
        torrent = _mock_torrent()
        tm.announcers[torrent.info_hash] = _mock_announcer()
        client = MagicMock()
        with patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())):
            await tm.add_torrent(torrent, client, {}, is_running=False)
        # Should be a no-op, no crash

    @pytest.mark.asyncio
    async def test_add_with_persisted_stats(self):
        tm = _make_tm()
        torrent = _mock_torrent()
        client = MagicMock()
        with patch("app.services.torrent_manager.TrackerAnnouncer") as MockAnn, \
             patch("app.services.torrent_manager.persistence_service") as mock_ps, \
             patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())), \
             patch("app.services.torrent_manager.history_service"):
            mock_ps.get.return_value = {"uploaded": 5000, "seeding_time": 1800, "added_at": "2024-01-01T00:00:00+00:00"}
            mock_ann_inst = MagicMock()
            mock_ann_inst.stats = MagicMock()
            mock_ann_inst.seeding_time = 0
            MockAnn.return_value = mock_ann_inst
            await tm.add_torrent(torrent, client, {}, is_running=False)
        assert mock_ann_inst.stats.uploaded == 5000
        assert mock_ann_inst.seeding_time == 1800

    @pytest.mark.asyncio
    async def test_add_no_client_raises(self):
        tm = _make_tm()
        torrent = _mock_torrent()
        with pytest.raises(ValueError, match="Client not initialized"):
            await tm.add_torrent(torrent, None, {}, is_running=False)

    @pytest.mark.asyncio
    async def test_add_and_start(self):
        tm = _make_tm()
        torrent = _mock_torrent()
        client = MagicMock()
        callback = AsyncMock()
        with patch("app.services.torrent_manager.TrackerAnnouncer") as MockAnn, \
             patch("app.services.torrent_manager.persistence_service") as mock_ps, \
             patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())), \
             patch("app.services.torrent_manager.history_service"):
            mock_ps.get.return_value = None
            MockAnn.return_value = MagicMock()
            MockAnn.return_value.stats = MagicMock()
            await tm.add_torrent(torrent, client, {}, is_running=True, start_callback=callback)
        callback.assert_awaited_once()


# ── load_torrents ───────────────────────────────────────────────────────

class TestLoadTorrents:
    @pytest.mark.asyncio
    async def test_load_no_torrents(self, tmp_path):
        tm = _make_tm()
        with patch("app.services.torrent_manager.settings") as ms:
            ms.TORRENTS_DIR = tmp_path
            ms.ANNOUNCE_INTERVAL = 1800
            ms.ANNOUNCE_JITTER = 120
            ms.MIN_STATS_UPDATE_INTERVAL = 5
            ms.ENABLE_SPEED_VARIATION = True
            ms.SPEED_VARIATION_PERCENT = 10
            with patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())):
                await tm.load_torrents(MagicMock(), {}, is_running=False)
        assert len(tm.announcers) == 0

    @pytest.mark.asyncio
    async def test_load_invalid_torrent_archives(self, tmp_path):
        tm = _make_tm()
        # Create a fake invalid torrent file
        bad_file = tmp_path / "bad.torrent"
        bad_file.write_bytes(b"not-a-torrent")
        archived_dir = tmp_path / "archived"
        with patch("app.services.torrent_manager.settings") as ms, \
             patch("app.services.torrent_manager.validate_torrent_file", return_value=(False, "Invalid file")), \
             patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())), \
             patch("app.services.torrent_manager.history_service"):
            ms.TORRENTS_DIR = tmp_path
            await tm.load_torrents(MagicMock(), {}, is_running=False)
        # File should be archived
        assert archived_dir.exists()

    @pytest.mark.asyncio
    async def test_load_valid_torrent(self, tmp_path):
        tm = _make_tm()
        torrent_file = tmp_path / "good.torrent"
        torrent_file.write_bytes(b"d8:announce35:http://tracker.example.com/announce4:infod6:lengthi1024e4:name4:test12:piece lengthi262144e6:pieces20:AAAAAAAAAAAAAAAAAAAAee")
        mock_torrent = _mock_torrent()
        with patch("app.services.torrent_manager.settings") as ms, \
             patch("app.services.torrent_manager.validate_torrent_file", return_value=(True, "")), \
             patch("app.services.torrent_manager.Torrent", return_value=mock_torrent), \
             patch("app.services.torrent_manager.TrackerAnnouncer") as MockAnn, \
             patch("app.services.torrent_manager.persistence_service") as mock_ps, \
             patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())), \
             patch("app.services.torrent_manager.history_service"):
            ms.TORRENTS_DIR = tmp_path
            ms.ANNOUNCE_INTERVAL = 1800
            ms.ANNOUNCE_JITTER = 120
            ms.MIN_STATS_UPDATE_INTERVAL = 5
            ms.ENABLE_SPEED_VARIATION = True
            ms.SPEED_VARIATION_PERCENT = 10
            ms.PAUSE_DURATION_MIN = 5
            ms.PAUSE_DURATION_MAX = 30
            ms.REDUCED_SPEED_DURATION_MIN = 10
            ms.REDUCED_SPEED_DURATION_MAX = 60
            ms.STATE_CHANGE_INTERVAL_MIN = 30
            ms.STATE_CHANGE_INTERVAL_MAX = 120
            ms.REDUCED_SPEED_KBPS = 50
            ms.PEER_SPEED_TIERS_ENABLED = False
            mock_ps.get.return_value = None
            MockAnn.return_value = MagicMock()
            MockAnn.return_value.stats = MagicMock()
            client = MagicMock()
            await tm.load_torrents(client, {}, is_running=False)
        assert len(tm.announcers) == 1


# ── _get_torrent_info and get_torrents ──────────────────────────────────

class TestGetTorrents:
    def test_get_torrents_list(self):
        tm = _make_tm()
        ann = _mock_announcer()
        tm.announcers = {"abc123": ann}
        result = tm.get_torrents()
        assert isinstance(result, list)
        assert len(result) == 1

    def test_get_torrent_info(self):
        tm = _make_tm()
        ann = _mock_announcer()
        tm.announcers = {"abc123": ann}
        info = tm._get_torrent_info("abc123")
        assert isinstance(info, dict)

    def test_get_torrent_info_missing(self):
        tm = _make_tm()
        info = tm._get_torrent_info("nonexistent")
        assert info == {}


# ── remove_torrent ──────────────────────────────────────────────────────

class TestRemoveTorrent:
    @pytest.mark.asyncio
    async def test_remove_existing(self):
        tm = _make_tm()
        ann = _mock_announcer(running=True)
        tm.announcers = {"abc123": ann}
        with patch("app.services.torrent_manager.persistence_service"), \
             patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())), \
             patch("app.services.torrent_manager.history_service"):
            await tm.remove_torrent("abc123")
        assert "abc123" not in tm.announcers
        ann.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_remove_nonexistent(self):
        tm = _make_tm()
        with patch("app.services.torrent_manager.websocket_manager", MagicMock(broadcast=AsyncMock())):
            await tm.remove_torrent("nope")
        # no error
