"""
Extended tests for tracker_announcer.py - init, properties, start/stop, error tracking
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
    t.size = size
    t.total_size = size
    t.tracker_url = "http://tracker.example.com/announce"
    t.tracker_urls = trackers or ["http://tracker.example.com/announce"]
    t.file_path = f"/tmp/{name}"
    t.primary_tracker = "http://tracker.example.com/announce"
    t.created_by = "test"
    t.added_at = datetime.now(timezone.utc)
    return t


def _mock_client():
    c = MagicMock()
    c.peer_id = b"-qB5140-" + b"0" * 12
    c.port = 6881
    c.key = "test_key"
    c.generate_peer_id = MagicMock(return_value=b"-qB5140-" + b"0" * 12)
    c.get_session_port = MagicMock(return_value=6881)
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

    def test_announcer_default_config(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        assert ann.announce_interval > 0
        assert ann.announce_jitter >= 0

    def test_announcer_custom_config(self):
        torrent = _mock_torrent()
        client = _mock_client()
        config = {"announce_interval": 60, "announce_jitter": 10}
        ann = TrackerAnnouncer(torrent, client, discretion_config=config)
        assert ann.announce_interval == 60
        assert ann.announce_jitter == 10


class TestAnnouncerStartStop:
    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)

        with patch.object(ann, "_send_announce_stealth", new_callable=AsyncMock), \
             patch.object(ann, "_announce_loop", new_callable=AsyncMock) as mock_loop, \
             patch("asyncio.create_task") as mock_task:
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
        assert ann.consecutive_failures == 0

    def test_max_retries(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        assert ann.max_retries == 5
        assert ann.base_retry_delay == 30


class TestAnnouncerProperties:
    def test_uploaded_property(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        assert ann.uploaded == 0
        ann.uploaded = 1000
        assert ann.uploaded == 1000

    def test_downloaded_property(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        assert ann.downloaded >= 0

    def test_left_property(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        left = ann.left
        assert left >= 0

    def test_upload_speed_property(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        assert ann.upload_speed >= 0
        ann.upload_speed = 5000
        assert ann.upload_speed == 5000

    def test_get_stats(self):
        torrent = _mock_torrent()
        client = _mock_client()
        ann = TrackerAnnouncer(torrent, client)
        stats = ann.get_stats()
        assert isinstance(stats, dict)
        assert "uploaded" in stats
        assert "seeders" in stats
