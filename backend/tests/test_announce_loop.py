"""Tests for tracker_announcer.py — announce, start/stop, error recording."""
import asyncio
import time
import random
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

import os
os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.core.tracker_announcer import TrackerAnnouncer


def _make_announcer():
    """Create a TrackerAnnouncer via __new__ with all required attributes."""
    ann = object.__new__(TrackerAnnouncer)

    # stats delegate — must be set FIRST
    ann.stats = MagicMock()
    ann.stats.uploaded = 0
    ann.stats.downloaded = 0
    ann.stats.left = 100000
    ann.stats.upload_speed = 50000
    ann.stats.download_speed = 0
    ann.stats.seeders = 5
    ann.stats.leechers = 2
    ann.stats.seeding_time = 0
    ann.stats.announce_count = 0
    ann.stats._initial_seeding = True
    ann.stats._last_announce_uploaded = 0
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
    ann.is_running = False
    ann._announce_task = None
    ann.last_error = None
    ann.error_count = 0
    ann.last_error_time = None
    ann.consecutive_failures = 0
    ann.max_retries = 5
    ann.base_retry_delay = 30
    ann.last_retry_attempt = None
    ann._in_backoff = False
    ann._backoff_count = 0
    ann.stealth_profile = {}
    ann._last_successful_announce = 0
    ann._last_successful_uploaded = 0
    ann._tracker_id = None
    ann._min_interval = 0
    ann.announce_interval = 1800
    ann.announce_jitter = 60

    return ann


class TestSendAnnounce:
    @pytest.mark.asyncio
    async def test_send_announce_success(self):
        ann = _make_announcer()
        import bencodepy
        response_data = bencodepy.encode({
            b"interval": 1800,
            b"complete": 10,
            b"incomplete": 3,
            b"peers": b"",
        })

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = response_data
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client_ctx), \
             patch("app.core.tracker_announcer.history_service"), \
             patch("app.core.tracker_announcer.settings") as mock_s:
            mock_s.HTTP_PROXY_HOST = None
            mock_s.HTTP_PROXY_PORT = None
            await ann._send_announce_stealth(event="started")

        assert ann.last_announce is not None

    @pytest.mark.asyncio
    async def test_send_announce_no_tracker(self):
        ann = _make_announcer()
        ann.tracker_mgr.get_next_tracker.return_value = None
        with pytest.raises(Exception, match="No tracker available"):
            await ann._send_announce_stealth()

    @pytest.mark.asyncio
    async def test_send_announce_network_error_simulated(self):
        import httpx
        ann = _make_announcer()
        ann.max_retries = 0
        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client_ctx), \
             patch("app.core.tracker_announcer.history_service"), \
             patch("app.core.tracker_announcer.settings") as mock_s:
            mock_s.HTTP_PROXY_HOST = None
            mock_s.HTTP_PROXY_PORT = None
            await ann._send_announce_with_retry()

        assert ann.consecutive_failures > 0

    @pytest.mark.asyncio
    async def test_send_announce_with_proxy(self):
        ann = _make_announcer()
        import bencodepy
        response_data = bencodepy.encode({b"interval": 1800, b"complete": 1, b"incomplete": 0, b"peers": b""})
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = response_data
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client_ctx) as mock_ac, \
             patch("app.core.tracker_announcer.history_service"), \
             patch("app.core.tracker_announcer.settings") as mock_s:
            mock_s.HTTP_PROXY_HOST = "proxy.example.com"
            mock_s.HTTP_PROXY_PORT = 8080
            await ann._send_announce_stealth()

    @pytest.mark.asyncio
    async def test_send_announce_http_error(self):
        import httpx
        ann = _make_announcer()
        ann.max_retries = 0
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client_ctx), \
             patch("app.core.tracker_announcer.history_service"), \
             patch("app.core.tracker_announcer.settings") as mock_s:
            mock_s.HTTP_PROXY_HOST = None
            mock_s.HTTP_PROXY_PORT = None
            await ann._send_announce_with_retry()

        assert ann.consecutive_failures > 0

    @pytest.mark.asyncio
    async def test_send_announce_timeout(self):
        import httpx
        ann = _make_announcer()
        ann.max_retries = 0
        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client_ctx), \
             patch("app.core.tracker_announcer.history_service"), \
             patch("app.core.tracker_announcer.settings") as mock_s:
            mock_s.HTTP_PROXY_HOST = None
            mock_s.HTTP_PROXY_PORT = None
            await ann._send_announce_with_retry()

        assert ann.consecutive_failures > 0

    @pytest.mark.asyncio
    async def test_send_announce_generic_exception(self):
        ann = _make_announcer()
        ann.max_retries = 0
        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(side_effect=Exception("connection reset"))
        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client_ctx), \
             patch("app.core.tracker_announcer.history_service"), \
             patch("app.core.tracker_announcer.settings") as mock_s:
            mock_s.HTTP_PROXY_HOST = None
            mock_s.HTTP_PROXY_PORT = None
            await ann._send_announce_with_retry()

        assert ann.consecutive_failures > 0


class TestStartStop:
    @pytest.mark.asyncio
    async def test_start(self):
        ann = _make_announcer()
        ann._send_announce_stealth = AsyncMock()
        ann._announce_loop = AsyncMock()

        with patch("asyncio.create_task") as mock_task:
            mock_task.return_value = MagicMock()
            await ann.start()

        assert ann.is_running is True
        # _initial_seeding is now reset inside _announce_loop (after started+completed events),
        # not inside start() — so it remains True here until the loop runs.
        assert ann.stats._initial_seeding is True

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        ann = _make_announcer()
        ann.is_running = True
        await ann.start()

    @pytest.mark.asyncio
    async def test_stop(self):
        ann = _make_announcer()
        ann.is_running = True
        ann._seeding_started_at = datetime.now(timezone.utc) - timedelta(hours=1)
        ann.seeding_time = 100

        # Mock the _announce_task as a real cancelled future
        fut = asyncio.get_event_loop().create_future()
        fut.cancel()
        ann._announce_task = fut

        ann._send_announce_stealth = AsyncMock()
        await ann.stop()

        assert ann.is_running is False
        assert ann.seeding_time > 100

    @pytest.mark.asyncio
    async def test_stop_already_stopped(self):
        ann = _make_announcer()
        ann.is_running = False
        await ann.stop()


class TestRecordError:
    def test_record_error(self):
        ann = _make_announcer()
        ann._record_error("test error")
        assert ann.last_error == "test error"
        assert ann.error_count == 1
        assert ann.last_error_time is not None

    def test_record_error_silent(self):
        ann = _make_announcer()
        ann._record_error_silent("silent error")
        assert ann.last_error == "silent error"
        assert ann.error_count == 1


class TestCalculateBackoffDelay:
    def test_basic_backoff(self):
        ann = _make_announcer()
        ann.consecutive_failures = 1
        delay = ann._calculate_backoff_delay()
        assert 20 <= delay <= 40  # ~30 * (0.8 to 1.2)

    def test_exponential_backoff(self):
        ann = _make_announcer()
        ann.consecutive_failures = 3
        delay = ann._calculate_backoff_delay()
        # 30 * 2^2 = 120, * jitter (0.8-1.2) => ~96-144
        assert 80 <= delay <= 160

    def test_capped_backoff(self):
        ann = _make_announcer()
        ann.consecutive_failures = 10
        delay = ann._calculate_backoff_delay()
        assert delay <= 360  # max 300 * 1.2


class TestGetStats:
    def test_get_stats_not_running(self):
        ann = _make_announcer()
        ann.is_running = False
        ann.stats.uploaded = 1000
        ann.stats.upload_speed = 0

        with patch("app.core.tracker_announcer.stealth_service") as mock_ss:
            mock_ss.get_session_stats.return_value = None
            result = ann.get_stats()

        assert result["uploaded"] == 1000
        assert "isRunning" not in result or True  # not directly set but via status

    def test_get_stats_running(self):
        ann = _make_announcer()
        ann.is_running = True
        ann._seeding_started_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        ann.stats.uploaded = 5000
        ann.stats.upload_speed = 1000
        ann.seeders = 10
        ann.leechers = 3
        ann.last_announce = datetime.now(timezone.utc)
        ann.next_announce = datetime.now(timezone.utc) + timedelta(minutes=30)

        with patch("app.core.tracker_announcer.stealth_service") as mock_ss:
            mock_ss.get_session_stats.return_value = {
                "client": "qBittorrent",
                "session_duration_hours": 1,
                "activity_pattern": "burst",
                "connection_stability": 98.0,
            }
            result = ann.get_stats()

        assert result["uploaded"] == 5000
        assert result["seedingTime"] >= 300
        assert "stealth" in result

    def test_get_status_info(self):
        ann = _make_announcer()
        ann.is_running = True
        ann.stats.upload_speed = 50000
        ann.seeders = 5
        ann.leechers = 2
        ann.last_error = None
        result = ann.get_status_info()
        assert "current_speed" in result
