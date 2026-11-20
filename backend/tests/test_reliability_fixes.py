"""
Regression tests for the reliability / protocol fixes:

- BEP 3 session-relative uploaded/downloaded counters
- announce loop survives a failing 'started' announce
- tracker 'min interval' is honoured
- low upload speeds are not inflated by block rounding
- log queue drain never blocks the event loop
- Stop/Start keeps the file watcher and persistence alive
- switching client updates already-loaded torrents
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.core.stats_simulator import StatsSimulator
from app.core.tracker_announcer import TrackerAnnouncer


def _make_announcer(size=100 * 1024 * 1024):
    torrent = Mock()
    torrent.name = "regression_torrent"
    torrent.size = size
    torrent.info_hash = "c" * 40
    torrent.info_hash_bytes = bytes.fromhex("c" * 40)
    torrent.primary_tracker = "http://tracker.example.com/announce"
    torrent.announce_list = []

    client = Mock()
    client.generate_peer_id.return_value = "-qB4600-abcdefghijkl"
    client.get_session_port.return_value = 51000
    client.get_upload_rate_range.return_value = (30 * 1024, 160 * 1024)
    client.build_announce_url.return_value = "http://tracker.example.com/announce?x=1"
    client.get_request_headers.return_value = {"User-Agent": "qBittorrent/4.6.0"}
    client.name = "qBittorrent"
    client.version = "4.6.0"

    with patch("app.core.tracker_announcer.stealth_service") as ss:
        ss.get_session_profile.return_value = {}
        ann = TrackerAnnouncer(torrent, client, {"seedingOnlyMode": True})
    return ann


# ---------------------------------------------------------------- BEP 3 counters

class TestSessionCounters:
    def test_restored_upload_is_not_reported_on_new_session(self):
        """Persisted all-time upload must not be re-sent on 'started' (BEP 3)."""
        ann = _make_announcer()
        ann.stats.uploaded = 5 * 1024 ** 3  # restored from persistence
        ann._session_uploaded_base = ann.stats.uploaded
        ann._session_downloaded_base = ann.stats.downloaded

        assert ann.session_uploaded == 0
        assert ann.session_downloaded == 0  # seeding: nothing downloaded this session
        # all-time value still available for UI / ratio
        assert ann.uploaded == 5 * 1024 ** 3

    @pytest.mark.asyncio
    async def test_start_snapshots_base_and_counts_delta(self):
        ann = _make_announcer()
        ann.stats.uploaded = 1000
        with patch.object(ann, "_announce_loop", new=AsyncMock()):
            await ann.start()
        assert ann.session_uploaded == 0
        ann.stats.uploaded += 16384
        assert ann.session_uploaded == 16384
        ann.is_running = False

    @pytest.mark.asyncio
    async def test_http_announce_sends_session_values(self):
        ann = _make_announcer()
        ann.stats.uploaded = 10 * 1024 ** 2
        ann._session_uploaded_base = 4 * 1024 ** 2
        ann._session_downloaded_base = ann.stats.downloaded

        response = MagicMock(status_code=200, content=b"d8:intervali1800ee")
        http = AsyncMock()
        http.get.return_value = response
        http.__aenter__.return_value = http
        with patch("app.core.tracker_announcer.httpx.AsyncClient", return_value=http), \
             patch("app.core.tracker_announcer.history_service"):
            await ann._send_announce_http("http://tracker.example.com/announce")

        kwargs = ann.client.build_announce_url.call_args.kwargs
        assert kwargs["uploaded"] == 6 * 1024 ** 2
        assert kwargs["downloaded"] == 0


# ---------------------------------------------------------------- announce loop resilience

class TestAnnounceLoopResilience:
    @pytest.mark.asyncio
    async def test_failed_started_is_retried_not_fatal(self):
        ann = _make_announcer()
        ann.is_running = True
        ann._initial_seeding = False
        calls = []

        async def flaky(event=None):
            calls.append(event)
            if len(calls) == 1:
                raise Exception("tracker down")
            if event is None:  # first regular announce: stop the loop
                ann.is_running = False

        ann._send_announce_stealth = flaky
        ann._send_announce_with_retry = AsyncMock(side_effect=lambda: setattr(ann, "is_running", False))
        ann._calculate_backoff_delay = lambda: 0
        ann._compute_next_interval = lambda: 0
        ann._update_stats_with_stealth = lambda: None

        await asyncio.wait_for(ann._announce_loop(), timeout=5)

        assert calls[:2] == ["started", "started"]  # retried after failure
        ann._send_announce_with_retry.assert_awaited()  # loop kept going


# ---------------------------------------------------------------- min interval

class TestMinInterval:
    def test_parse_records_min_interval(self):
        ann = _make_announcer()
        ann._parse_announce_response(b"d8:intervali1800e12:min intervali1500ee")
        assert ann._tracker_min_interval == 1500

    def test_next_interval_never_below_min_interval(self):
        ann = _make_announcer()
        ann._tracker_min_interval = 1500
        with patch("app.core.tracker_announcer.stealth_service") as ss:
            ss.get_natural_announce_interval.return_value = 900  # jitter went low
            ss.should_simulate_temporary_disconnect.return_value = False
            assert ann._compute_next_interval() >= 1500


# ---------------------------------------------------------------- upload accounting

class TestUploadAccounting:
    def test_low_speed_not_inflated_by_block_rounding(self):
        sim = StatsSimulator("t", 10 * 1024 ** 3, {"seedingOnlyMode": True})
        total = 0
        for _ in range(100):  # 100 ticks of 3 s at 1 KiB/s = 300 KiB
            total += sim._piece_aligned_delta(1024, 3.0)
        expected = 1024 * 3 * 100
        assert total <= expected
        assert expected - total < 16384  # only the last partial block is pending
        assert total % 16384 == 0

    def test_carry_is_preserved(self):
        sim = StatsSimulator("t", 10 * 1024 ** 3, {"seedingOnlyMode": True})
        assert sim._piece_aligned_delta(1000, 3.0) == 0
        assert sim._upload_carry == 3000


# ---------------------------------------------------------------- event loop

class TestNonBlockingLogDrain:
    def test_get_new_logs_returns_immediately_when_empty(self):
        from app.services.log_stream_service import LogHandler
        handler = LogHandler()
        start = time.perf_counter()
        assert handler.get_new_logs(timeout=1.0) == []
        assert time.perf_counter() - start < 0.05


# ---------------------------------------------------------------- seeder service lifecycle

class TestSeederLifecycle:
    @pytest.mark.asyncio
    async def test_stop_keeps_file_watcher_and_autosave(self):
        from app.services.seeder_service import SeederService
        svc = SeederService()
        svc.is_running = True
        svc.started_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        svc.file_watcher = MagicMock()
        svc.file_watcher.stop = AsyncMock()
        with patch("app.services.seeder_service.persistence_service") as ps, \
             patch("app.services.seeder_service.websocket_manager.broadcast", new=AsyncMock()), \
             patch("app.services.seeder_service.notification_service") as ns, \
             patch("app.services.seeder_service.history_service"):
            ns.notify_system_stop = AsyncMock()
            ns.close = AsyncMock()
            ps.stop_autosave = AsyncMock()
            await svc.stop()
            svc.file_watcher.stop.assert_not_awaited()
            ps.stop_autosave.assert_not_awaited()
            ps.save.assert_called()  # stats still flushed to disk

    @pytest.mark.asyncio
    async def test_switch_client_updates_existing_announcers(self):
        from app.services.seeder_service import SeederService
        svc = SeederService()
        ann = _make_announcer()
        ann.is_running = False
        svc.announcers = {"c" * 40: ann}

        new_client = Mock()
        new_client.generate_peer_id.return_value = "-TR4050-xxxxxxxxxxxx"
        new_client.get_session_port.return_value = 52000
        new_client.name = "Transmission"
        new_client.version = "4.0.5"
        with patch("app.services.seeder_service.BitTorrentClient", return_value=new_client):
            await svc._switch_client("transmission-4.0.5.client")

        assert svc.client is new_client
        assert ann.client is new_client
        assert ann.tracker_mgr.client is new_client
        assert ann.peer_id == "-TR4050-xxxxxxxxxxxx"
        assert ann.port == 52000


# ---------------------------------------------------------------- 'completed' event (BEP 3)

class TestCompletedEvent:
    @pytest.mark.asyncio
    async def test_seed_does_not_send_completed_on_start(self):
        """BEP 3: no 'completed' if the file was complete when started."""
        ann = _make_announcer()
        ann.stats.simulate_natural_seeding_start()
        ann.is_running = True
        events = []

        async def record(event=None):
            events.append(event)

        ann._send_announce_stealth = record
        ann._send_announce_with_retry = AsyncMock(side_effect=lambda ev=None: setattr(ann, "is_running", False))
        ann._compute_next_interval = lambda: 0
        ann._update_stats_with_stealth = lambda: None
        await asyncio.wait_for(ann._announce_loop(), timeout=5)

        assert events == ["started"]
        ann._send_announce_with_retry.assert_awaited_once_with(None)

    def test_download_completion_sets_completed_once(self):
        from datetime import datetime, timedelta, timezone
        sim = StatsSimulator("t", 1000, {"seedingOnlyMode": False})
        sim.simulate_natural_download_start()
        sim._download_completion_time = datetime.now(timezone.utc) - timedelta(hours=2)
        assert sim.is_in_downloading_phase() is False
        assert sim.left == 0 and sim.downloaded == 1000
        assert sim.consume_completed_event() is True
        assert sim.consume_completed_event() is False
