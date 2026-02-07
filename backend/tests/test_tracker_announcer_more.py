"""
Extended tests for tracker_announcer.py - announce logic, error handling, 
multi-tracker support, HTTP/UDP dispatch
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock
from datetime import datetime, timezone

import os
os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.core.tracker_announcer import TrackerAnnouncer


def _mock_torrent(info_hash="aabbccdd", name="test.torrent", size=1024*1024,
                   trackers=None):
    t = MagicMock()
    t.info_hash = info_hash
    t.name = name
    t.total_size = size
    t.size = size
    t.tracker_url = "http://tracker.example.com/announce"
    t.tracker_urls = trackers or ["http://tracker.example.com/announce"]
    t.file_path = f"/tmp/{name}"
    return t


def _mock_client():
    c = MagicMock()
    c.peer_id = b"-qB5140-" + b"0" * 12
    c.port = 6881
    c.key = "test_key"
    c.get_upload_rate_range = MagicMock(return_value=(10240, 102400))
    c.get_download_rate_range = MagicMock(return_value=(102400, 1048576))
    c.get_numwant = MagicMock(return_value=200)
    c.get_user_agent = MagicMock(return_value="qBittorrent/5.1.4")
    c.get_announce_headers = MagicMock(return_value={"User-Agent": "qBittorrent/5.1.4"})
    return c


class TestAnnouncerInit:
    def test_create_announcer(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        assert ann.torrent.info_hash == "aabbccdd"
        assert ann.is_running is False
        assert ann.error_count == 0

    def test_announcer_has_stats(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        assert ann.stats is not None
        assert ann.stats.uploaded == 0

    def test_announcer_tracker_urls(self):
        trackers = [
            "http://tracker1.example.com/announce",
            "udp://tracker2.example.com:6969/announce"
        ]
        torrent = _mock_torrent(trackers=trackers)
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        assert ann.tracker_mgr is not None


class TestAnnouncerStartStop:
    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)

        with patch.object(ann, "_announce_loop", new_callable=AsyncMock):
            await ann.start()
        assert ann.is_running is True

    @pytest.mark.asyncio
    async def test_stop_sets_not_running(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        ann.is_running = True
        ann._announce_task = None

        with patch.object(ann, "_send_announce_stealth", new_callable=AsyncMock):
            await ann.stop()
        assert ann.is_running is False

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        ann.is_running = True

        # Should be a no-op
        await ann.start()
        assert ann.is_running is True


class TestAnnouncerErrorTracking:
    def test_initial_error_count(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        assert ann.error_count == 0
        assert ann.last_error is None

    def test_error_tracking_attributes(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        # Verify error tracking fields exist
        assert hasattr(ann, "error_count")
        assert hasattr(ann, "last_error")
        assert hasattr(ann, "consecutive_failures")


class TestAnnouncerProperties:
    def test_torrent_property(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        assert ann.torrent == torrent

    def test_info_hash_property(self):
        torrent = _mock_torrent(info_hash="deadbeef")
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        assert ann.torrent.info_hash == "deadbeef"

    def test_stats_access(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        stats = ann.stats
        assert stats.uploaded == 0
        assert stats.left >= 0
