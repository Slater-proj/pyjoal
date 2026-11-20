"""
Regression tests for the robustness pass:

- config min/max pairs validated (and tolerated at runtime for old configs)
- 'Announce Jitter' setting actually bounds the announce interval
- HTTP trackers preferred when a proxy is configured (UDP bypasses it)
- TLS verification configurable and used
- WebSocket throttling keeps the latest message (trailing edge)
- download simulation progresses continuously and ends with 'completed'
- 'stopped' announce bounded in time
- per-torrent stealth state released on removal
"""
import asyncio
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic import ValidationError

from app.core.stats_simulator import StatsSimulator, _randint_between
from app.core.tracker_announcer import TrackerAnnouncer
from app.core.tracker_manager import TrackerManager
from app.models.schemas import ConfigSchema
from app.services.config_manager import ConfigManager


def _valid_config(**overrides):
    base = dict(
        minUploadRate=30, maxUploadRate=160, simultaneousSeed=5,
        client="qbittorrent-4.6.0.client", keepTorrentWithZeroLeechers=True,
        uploadRatioTarget=-1.0,
    )
    base.update(overrides)
    return base


def _make_announcer(**discretion):
    torrent = Mock()
    torrent.name = "robust_torrent"
    torrent.size = 50 * 1024 ** 2
    torrent.info_hash = "d" * 40
    torrent.info_hash_bytes = bytes.fromhex("d" * 40)
    torrent.primary_tracker = "http://tracker.example.com/announce"
    torrent.announce_list = []
    client = Mock()
    client.generate_peer_id.return_value = "-qB4600-abcdefghijkl"
    client.get_session_port.return_value = 51000
    client.get_upload_rate_range.return_value = (30 * 1024, 160 * 1024)
    client.name = "qBittorrent"
    client.version = "4.6.0"
    with patch("app.core.tracker_announcer.stealth_service") as ss:
        ss.get_session_profile.return_value = {}
        return TrackerAnnouncer(torrent, client, {"seedingOnlyMode": True, **discretion})


# ---------------------------------------------------------------- config validation

class TestConfigValidation:
    def test_valid_config_accepted(self):
        ConfigSchema(**_valid_config())

    @pytest.mark.parametrize("lo,hi", [
        ("minUploadRate", "maxUploadRate"),
        ("pauseDurationMin", "pauseDurationMax"),
        ("reducedSpeedDurationMin", "reducedSpeedDurationMax"),
        ("stateChangeIntervalMin", "stateChangeIntervalMax"),
    ])
    def test_min_greater_than_max_rejected(self, lo, hi):
        with pytest.raises(ValidationError):
            ConfigSchema(**_valid_config(**{lo: 20, hi: 10}))

    def test_config_manager_rejects_merged_min_gt_max(self):
        cm = ConfigManager()
        cm._config = {"pauseDurationMin": 30, "pauseDurationMax": 180}
        with pytest.raises(ValueError):
            cm.validate({"pauseDurationMin": 200})

    def test_runtime_tolerates_swapped_bounds(self):
        for _ in range(50):
            assert 3 <= _randint_between(8, 3) <= 8

    def test_simulator_with_swapped_config_does_not_crash(self):
        sim = StatsSimulator("t", 1000, {
            "seedingOnlyMode": True,
            "stateChangeIntervalMin": 8, "stateChangeIntervalMax": 2,
            "pauseDurationMin": 180, "pauseDurationMax": 30,
        })
        sim.simulate_natural_seeding_start()
        sim._next_pause_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        sim.update_individual_state()  # used to raise ValueError

    def test_discretion_builder_maps_keys(self):
        d = ConfigManager.build_discretion_config({"announceInterval": 900, "peerTier1MaxPeers": 7})
        assert d["announce_interval"] == 900
        assert d["peer_tier1_max_peers"] == 7
        assert "seedingOnlyMode" in d


# ---------------------------------------------------------------- announce jitter

class TestAnnounceJitter:
    def test_interval_bounded_by_jitter_setting(self):
        ann = _make_announcer(announce_interval=1800, announce_jitter=120)
        with patch("app.core.tracker_announcer.stealth_service") as ss:
            ss.get_natural_announce_interval.return_value = 1800 + 700  # natural spread too wide
            for _ in range(50):
                assert 1680 <= ann._bounded_natural_interval() <= 1920

    def test_natural_value_kept_when_inside_bounds(self):
        ann = _make_announcer(announce_interval=1800, announce_jitter=600)
        with patch("app.core.tracker_announcer.stealth_service") as ss:
            ss.get_natural_announce_interval.return_value = 2000
            assert ann._bounded_natural_interval() == 2000

    def test_zero_jitter_means_exact_interval(self):
        ann = _make_announcer(announce_interval=1800, announce_jitter=0)
        with patch("app.core.tracker_announcer.stealth_service") as ss:
            ss.get_natural_announce_interval.return_value = 1500
            assert ann._bounded_natural_interval() == 1800


# ---------------------------------------------------------------- proxy / UDP / TLS

class TestProxyAndTls:
    def _mgr(self):
        torrent = Mock()
        torrent.name = "t"
        torrent.primary_tracker = "udp://u.example.com:6969/announce"
        torrent.announce_list = [["udp://u.example.com:6969/announce"], ["https://h.example.com/announce"]]
        return TrackerManager(torrent, Mock())

    def test_prefers_http_tracker_when_proxy_configured(self):
        mgr = self._mgr()
        with patch("app.core.tracker_manager.settings") as st:
            st.HTTP_PROXY_HOST, st.HTTP_PROXY_PORT = "10.0.0.1", 8888
            assert mgr.get_next_tracker() == "https://h.example.com/announce"

    def test_tier_order_without_proxy(self):
        mgr = self._mgr()
        with patch("app.core.tracker_manager.settings") as st:
            st.HTTP_PROXY_HOST, st.HTTP_PROXY_PORT = None, None
            assert mgr.get_next_tracker() == "udp://u.example.com:6969/announce"

    @pytest.mark.asyncio
    async def test_http_announce_uses_tls_setting(self):
        ann = _make_announcer()
        ann.client.build_announce_url.return_value = "https://t.example.com/announce?x"
        ann.client.get_request_headers.return_value = {}
        http = AsyncMock()
        http.get.return_value = MagicMock(status_code=200, content=b"d8:intervali1800ee")
        http.__aenter__.return_value = http
        with patch("app.core.tracker_announcer.httpx.AsyncClient", return_value=http) as ac, \
             patch("app.core.tracker_announcer.history_service"), \
             patch("app.core.tracker_announcer.settings") as st:
            st.TRACKER_VERIFY_SSL = True
            st.HTTP_PROXY_HOST = st.HTTP_PROXY_PORT = None
            await ann._send_announce_http("https://t.example.com/announce")
        assert ac.call_args.kwargs["verify"] is True


# ---------------------------------------------------------------- stop announce bounded

class TestStopAnnounceTimeout:
    @pytest.mark.asyncio
    async def test_stopped_announce_is_bounded(self):
        ann = _make_announcer()
        ann.is_running = True

        async def hang(event=None):
            await asyncio.sleep(30)

        ann._send_announce_stealth = hang
        with patch("app.core.tracker_announcer.settings") as st:
            st.STOP_ANNOUNCE_TIMEOUT = 0.1
            start = time.perf_counter()
            await ann.stop()
        assert time.perf_counter() - start < 2


# ---------------------------------------------------------------- websocket trailing edge

class TestWebSocketTrailingThrottle:
    @pytest.mark.asyncio
    async def test_latest_throttled_message_is_delivered(self):
        from app.services.websocket_manager import WebSocketManager
        mgr = WebSocketManager()
        mgr._batch_interval = 0.01
        mgr._throttle_intervals["torrents_update"] = 0.2
        sent = []
        mgr._send_immediate = AsyncMock(side_effect=lambda m: sent.append(m["data"]))

        await mgr.broadcast({"type": "torrents_update", "data": 1})
        await asyncio.sleep(0.05)
        await mgr.broadcast({"type": "torrents_update", "data": 2})
        await mgr.broadcast({"type": "torrents_update", "data": 3})
        await asyncio.wait_for(mgr._batch_task, timeout=2)

        assert sent == [1, 3]  # first immediately, the latest after the throttle window


# ---------------------------------------------------------------- download simulation

class TestDownloadSimulation:
    def test_download_progresses_on_display_ticks_and_completes(self):
        client = Mock()
        client.get_upload_rate_range.return_value = (30 * 1024, 160 * 1024)
        del client.get_download_rate_range  # use defaults
        sim = StatsSimulator("t", 10 * 1024 ** 2, {"seedingOnlyMode": False})
        sim.simulate_natural_download_start()
        sim.downloaded = 0
        sim.left = sim.torrent_size
        sim._download_completion_time = datetime.now(timezone.utc) + timedelta(minutes=1)

        sim.update_stats_for_display(client, True)  # first tick initialises timing
        before = sim.downloaded
        sim._display_update_time -= 3
        sim._last_download_time = time.time() - 3
        sim.update_stats_for_display(client, True)
        assert sim.downloaded > before
        assert sim.left == sim.torrent_size - sim.downloaded

        sim.left = 0
        assert sim.is_in_downloading_phase() is False
        assert sim.consume_completed_event() is True


# ---------------------------------------------------------------- stealth state cleanup

class TestStealthForget:
    def test_forget_releases_profile(self):
        from app.services.stealth_service import StealthService
        ss = StealthService()
        ss.get_session_profile("e" * 40)
        ss.get_natural_speed_variation(1000, "e" * 40)
        ss.forget("e" * 40)
        assert "e" * 40 not in ss.session_profiles
        assert not any(k.startswith("e" * 40) for k in ss._speed_cache)
