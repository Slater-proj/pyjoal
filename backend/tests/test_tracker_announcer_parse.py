"""Tests for TrackerAnnouncer._parse_announce_response and get_stats."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
import os, struct

os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.core.tracker_announcer import TrackerAnnouncer


def _make_announcer():
    """Build a TrackerAnnouncer with mocked torrent + client."""
    torrent = MagicMock()
    torrent.info_hash = "abcdef1234567890abcd"
    torrent.name = "test.torrent"
    torrent.size = 1024 * 1024
    torrent.trackers = ["http://tracker.example.com/announce"]
    torrent.primary_tracker = "http://tracker.example.com/announce"
    torrent.path = MagicMock()
    torrent.added_at = datetime.now(timezone.utc)

    client = MagicMock()
    client.get_user_agent.return_value = "TestClient/1.0"
    client.get_request_headers.return_value = {"User-Agent": "TestClient/1.0"}
    client.get_upload_rate_range.return_value = (50000, 200000)
    client.get_session_port.return_value = 6881
    client.generate_peer_id.return_value = "-TC1000-AAAAAAAAAAAA"
    client.generate_key.return_value = "ABCD1234"
    client.build_announce_url.return_value = "http://tracker.example.com/announce?info_hash=abc"
    client.config = {"numwant": 200, "numwantOnStop": 0}

    ann = TrackerAnnouncer.__new__(TrackerAnnouncer)
    # stats must be set FIRST (properties delegate to it)
    ann.stats = MagicMock()
    ann.stats.uploaded = 0
    ann.stats.downloaded = 0
    ann.stats.upload_speed = 0
    ann.stats.get_status_info.return_value = {"status": "idle"}
    ann.torrent = torrent
    ann.client = client
    ann.announce_interval = 1800
    ann.seeders = 0
    ann.leechers = 0
    ann.last_announce = None
    ann.next_announce = None
    ann.last_error = None
    ann.last_error_time = None
    ann.error_count = 0
    ann.consecutive_failures = 0
    ann.is_running = False
    ann._in_backoff = False
    ann._seeding_started_at = None
    ann.seeding_time = 0
    ann._tracker_id = None
    ann._record_error = MagicMock()
    ann._get_activity_based_upload_speed = MagicMock(return_value=0)
    return ann


class TestParseAnnounceResponse:
    """Test _parse_announce_response with various bencode payloads."""

    def _bencode_dict(self, d):
        """Simple bencode dict encoder for testing."""
        import bencodepy
        return bencodepy.encode(d)

    def test_success_response(self):
        ann = _make_announcer()
        data = self._bencode_dict({
            b"interval": 1800,
            b"complete": 10,
            b"incomplete": 5,
            b"peers": b"\x7f\x00\x00\x01\x1a\xe1" * 3,  # 3 peers
        })
        ann._parse_announce_response(data)
        assert ann.seeders == 10
        assert ann.leechers == 5
        assert ann.announce_interval >= 60

    def test_failure_reason(self):
        ann = _make_announcer()
        data = self._bencode_dict({b"failure reason": b"Unregistered torrent"})
        ann._parse_announce_response(data)
        ann._record_error.assert_called_once()

    def test_warning_message(self):
        ann = _make_announcer()
        data = self._bencode_dict({
            b"warning message": b"Slow down",
            b"interval": 600,
            b"complete": 1,
            b"incomplete": 0,
        })
        ann._parse_announce_response(data)
        assert ann.seeders == 1

    def test_min_interval(self):
        ann = _make_announcer()
        ann.announce_interval = 300
        data = self._bencode_dict({
            b"min interval": 900,
            b"complete": 0,
            b"incomplete": 0,
        })
        ann._parse_announce_response(data)
        assert ann.announce_interval >= 300  # min_interval applies max()

    def test_interval_clamped(self):
        ann = _make_announcer()
        data = self._bencode_dict({
            b"interval": 30,  # too low, should be clamped to 60
            b"complete": 0,
            b"incomplete": 0,
        })
        ann._parse_announce_response(data)
        assert ann.announce_interval >= 60

    def test_interval_clamped_high(self):
        ann = _make_announcer()
        data = self._bencode_dict({
            b"interval": 99999,  # too high, should be clamped to 3600
            b"complete": 0,
            b"incomplete": 0,
        })
        ann._parse_announce_response(data)
        assert ann.announce_interval <= 3600

    def test_compact_peers(self):
        ann = _make_announcer()
        # 2 peers in compact format (6 bytes each)
        peers = struct.pack("!4sH", b"\x7f\x00\x00\x01", 6881) + struct.pack("!4sH", b"\x0a\x00\x00\x01", 6882)
        data = self._bencode_dict({
            b"interval": 1800,
            b"complete": 5,
            b"incomplete": 2,
            b"peers": peers,
        })
        ann._parse_announce_response(data)
        assert ann.seeders == 5
        assert ann.leechers == 2

    def test_dict_peers(self):
        ann = _make_announcer()
        data = self._bencode_dict({
            b"interval": 1800,
            b"complete": 3,
            b"incomplete": 1,
            b"peers": [{b"ip": b"127.0.0.1", b"port": 6881}],
        })
        ann._parse_announce_response(data)
        assert ann.seeders == 3

    def test_peers6(self):
        ann = _make_announcer()
        # 1 IPv6 peer = 18 bytes
        peers6 = b"\x00" * 18
        data = self._bencode_dict({
            b"interval": 1800,
            b"complete": 1,
            b"incomplete": 0,
            b"peers6": peers6,
        })
        ann._parse_announce_response(data)

    def test_external_ip(self):
        ann = _make_announcer()
        data = self._bencode_dict({
            b"interval": 1800,
            b"complete": 1,
            b"incomplete": 0,
            b"external ip": b"\xc0\xa8\x01\x01",  # 192.168.1.1
        })
        ann._parse_announce_response(data)

    def test_tracker_id(self):
        ann = _make_announcer()
        data = self._bencode_dict({
            b"interval": 1800,
            b"complete": 1,
            b"incomplete": 0,
            b"tracker id": b"TRACKER123",
        })
        ann._parse_announce_response(data)
        assert ann._tracker_id == b"TRACKER123"

    def test_non_int_seeders(self):
        ann = _make_announcer()
        data = self._bencode_dict({
            b"interval": 1800,
            b"complete": b"not_a_number",
            b"incomplete": b"also_not",
        })
        ann._parse_announce_response(data)
        assert ann.seeders == 0
        assert ann.leechers == 0

    def test_malformed_data(self):
        ann = _make_announcer()
        ann._parse_announce_response(b"this is not bencode at all")
        # Should not crash


class TestGetStats:
    def test_basic_stats(self):
        ann = _make_announcer()
        ann.uploaded = 5000
        ann.downloaded = 1000
        ann.upload_speed = 50000
        ann.seeders = 10
        ann.leechers = 5
        with patch("app.core.tracker_announcer.stealth_service") as mock_ss:
            mock_ss.get_session_stats.return_value = None
            stats = ann.get_stats()
        assert stats["uploaded"] == 5000
        assert stats["seeders"] == 10
        assert stats["leechers"] == 5
        assert "status" in stats

    def test_stats_with_stealth(self):
        ann = _make_announcer()
        ann.uploaded = 1024
        with patch("app.core.tracker_announcer.stealth_service") as mock_ss:
            mock_ss.get_session_stats.return_value = {
                "client": "qBittorrent 5.1.4",
                "session_duration_hours": 2.5,
                "activity_pattern": "steady",
                "connection_stability": 98.5,
            }
            stats = ann.get_stats()
        assert "stealth" in stats
        assert stats["stealth"]["client"] == "qBittorrent 5.1.4"

    def test_stats_running_seeding_time(self):
        ann = _make_announcer()
        ann.is_running = True
        ann.seeding_time = 3600
        ann._seeding_started_at = datetime.now(timezone.utc)
        with patch("app.core.tracker_announcer.stealth_service") as mock_ss:
            mock_ss.get_session_stats.return_value = None
            stats = ann.get_stats()
        assert stats["seedingTime"] >= 3600

    def test_stats_ratio(self):
        ann = _make_announcer()
        ann.uploaded = 2 * 1024 * 1024  # 2 MB
        ann.torrent.size = 1024 * 1024  # 1 MB
        with patch("app.core.tracker_announcer.stealth_service") as mock_ss:
            mock_ss.get_session_stats.return_value = None
            stats = ann.get_stats()
        assert abs(stats["ratio"] - 2.0) < 0.01

    def test_stats_healthy_after_successful_announce(self):
        ann = _make_announcer()
        ann.last_announce = datetime.now(timezone.utc)
        ann.last_error = "previous error"
        ann.last_error_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        with patch("app.core.tracker_announcer.stealth_service") as mock_ss:
            mock_ss.get_session_stats.return_value = None
            stats = ann.get_stats()
        assert stats["isHealthy"] is True

    def test_stats_zero_size_torrent(self):
        ann = _make_announcer()
        ann.torrent.size = 0
        ann.uploaded = 1024
        with patch("app.core.tracker_announcer.stealth_service") as mock_ss:
            mock_ss.get_session_stats.return_value = None
            stats = ann.get_stats()
        assert stats["ratio"] == 0.0


class TestGetStatusInfo:
    def test_status_info(self):
        ann = _make_announcer()
        ann._get_activity_based_upload_speed = MagicMock(return_value=50000)
        info = ann.get_status_info()
        assert "current_speed" in info
        assert info["current_speed"] == 50000
        assert "speed_formatted" in info
