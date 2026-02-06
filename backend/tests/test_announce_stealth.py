"""Tests for tracker_announcer.py — stealth announce, HTTP, retry."""
import asyncio
import time
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

import os
os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.core.tracker_announcer import TrackerAnnouncer


def _make_announcer():
    ann = object.__new__(TrackerAnnouncer)
    ann.stats = MagicMock()
    ann.stats.uploaded = 5000
    ann.stats.downloaded = 0
    ann.stats.left = 0
    ann.stats.upload_speed = 50000
    ann.stats.seeders = 5
    ann.stats.leechers = 2
    ann.stats.seeding_time = 0
    ann.stats.announce_count = 0
    ann.stats._initial_seeding = False
    ann.stats.simulate_occasional_network_errors = MagicMock(return_value=False)
    ann.stats.get_activity_based_upload_speed = MagicMock(return_value=50000)
    ann.stats.get_status_info = MagicMock(return_value={"state": "seeding"})

    ann.torrent = MagicMock()
    ann.torrent.name = "TestTorrent"
    ann.torrent.info_hash = "abcdef1234567890abcd"
    ann.torrent.info_hash_bytes = b"\x01" * 20
    ann.torrent.primary_tracker = "http://tracker.example.com/announce"
    ann.torrent.size = 1000000
    ann.torrent.added_at = datetime.now(timezone.utc)

    ann.client = MagicMock()
    ann.client.build_announce_url.return_value = "http://tracker.example.com/announce?info_hash=test"
    ann.client.get_request_headers.return_value = {"User-Agent": "test/1.0"}
    ann.client.get_user_agent.return_value = "test/1.0"
    ann.client.name = "qBittorrent"
    ann.client.version = "5.1.4"
    ann.client.generate_key.return_value = "ABCDEF01"

    ann.tracker_mgr = MagicMock()
    ann.tracker_mgr.get_next_tracker.return_value = "http://tracker.example.com/announce"

    ann.discretion_config = {}
    ann.peer_id = "-qB5140-abcdefghijkl"
    ann.port = 6881
    ann.seeders = 0
    ann.leechers = 0
    ann.last_announce = None
    ann.next_announce = None
    ann.seeding_time = 0
    ann._seeding_started_at = None
    ann.is_running = True
    ann._announce_task = None
    ann.last_error = None
    ann.error_count = 0
    ann.last_error_time = None
    ann.consecutive_failures = 0
    ann.max_retries = 2
    ann.base_retry_delay = 1
    ann.last_retry_attempt = None
    ann._in_backoff = False
    ann._backoff_count = 0
    ann.stealth_profile = {}
    ann._last_successful_announce = 0
    ann._last_successful_uploaded = 0
    ann.announce_interval = 1800
    ann.announce_jitter = 60
    return ann


class TestSendAnnounceStealth:
    @pytest.mark.asyncio
    async def test_stealth_http(self):
        ann = _make_announcer()
        ann._send_announce_http = AsyncMock()
        await ann._send_announce_stealth(event="started")
        ann._send_announce_http.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stealth_udp(self):
        ann = _make_announcer()
        ann.tracker_mgr.get_next_tracker.return_value = "udp://tracker.example.com:6969"
        ann._send_announce_udp = AsyncMock()
        with patch("app.core.tracker_announcer.is_udp_tracker", return_value=True):
            await ann._send_announce_stealth(event="started")
        ann._send_announce_udp.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stealth_no_tracker(self):
        ann = _make_announcer()
        ann.tracker_mgr.get_next_tracker.return_value = None
        with pytest.raises(Exception, match="No tracker available"):
            await ann._send_announce_stealth()


class TestSendAnnounceHttp:
    @pytest.mark.asyncio
    async def test_http_success(self):
        import bencodepy
        ann = _make_announcer()
        response_data = bencodepy.encode({
            b"interval": 900, b"complete": 10, b"incomplete": 3, b"peers": b""
        })
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = response_data

        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client_ctx), \
             patch("app.core.tracker_announcer.history_service"):
            await ann._send_announce_http("http://tracker.example.com/announce", event="started")

        assert ann.last_announce is not None

    @pytest.mark.asyncio
    async def test_http_non_200(self):
        ann = _make_announcer()
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client_ctx), \
             patch("app.core.tracker_announcer.history_service"):
            with pytest.raises(Exception, match="HTTP 503"):
                await ann._send_announce_http("http://tracker.example.com/announce")


class TestSendAnnounceUdp:
    @pytest.mark.asyncio
    async def test_udp_success(self):
        ann = _make_announcer()
        mock_response = MagicMock()
        mock_response.seeders = 15
        mock_response.leechers = 5
        mock_response.interval = 600
        mock_response.peers = []

        mock_udp = MagicMock()
        mock_udp.announce = AsyncMock(return_value=mock_response)
        ann.tracker_mgr.get_or_create_udp_tracker.return_value = mock_udp

        with patch("app.core.tracker_announcer.history_service"):
            await ann._send_announce_udp("udp://tracker.example.com:6969", event="started")

        assert ann.seeders == 15
        assert ann.leechers == 5
        assert ann.announce_interval == 600

    @pytest.mark.asyncio
    async def test_udp_error(self):
        from app.core.udp_tracker import UDPTrackerError
        ann = _make_announcer()
        mock_udp = MagicMock()
        mock_udp.announce = AsyncMock(side_effect=UDPTrackerError("timeout"))
        ann.tracker_mgr.get_or_create_udp_tracker.return_value = mock_udp

        with pytest.raises(Exception, match="UDP error"):
            await ann._send_announce_udp("udp://tracker.example.com:6969")


class TestSendAnnounceWithRetry:
    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        ann = _make_announcer()
        ann._send_announce_stealth = AsyncMock()
        await ann._send_announce_with_retry()
        assert ann.consecutive_failures == 0
        assert ann._in_backoff is False

    @pytest.mark.asyncio
    async def test_retry_fails_then_succeeds(self):
        ann = _make_announcer()
        ann.max_retries = 2
        ann.base_retry_delay = 0  # no sleep
        call_count = 0

        async def flaky_announce(event=None):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("temporary failure")

        ann._send_announce_stealth = flaky_announce
        await ann._send_announce_with_retry()
        assert ann.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_retry_all_attempts_fail(self):
        ann = _make_announcer()
        ann.max_retries = 1
        ann.base_retry_delay = 0

        ann._send_announce_stealth = AsyncMock(side_effect=Exception("permanent failure"))
        await ann._send_announce_with_retry()
        assert ann.consecutive_failures == 2  # max_retries + 1
        assert ann.last_error is not None
        assert "Final retry failed" in ann.last_error
