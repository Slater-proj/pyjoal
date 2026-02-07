"""
Targeted tests to increase code coverage for stats_simulator paths
that were previously uncovered.
"""
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.core.stats_simulator import StatsSimulator

# seeder_service is imported lazily inside StatsSimulator methods,
# so we must patch it at the module where it's defined.
_SVC = "app.services.seeder_service.seeder_service"


class TestUpdateConfig(unittest.TestCase):
    """Cover StatsSimulator.update_config() — previously uncovered."""

    def test_update_config_sets_all_fields(self):
        sim = StatsSimulator("Test Torrent", 1_000_000_000)
        cfg = {
            "min_stats_update_interval": 5,
            "enable_speed_variation": False,
            "speed_variation_percent": 10,
            "seedingOnlyMode": False,
            "pauseDurationMin": 15,
            "pauseDurationMax": 60,
            "reducedSpeedDurationMin": 30,
            "reducedSpeedDurationMax": 120,
            "stateChangeIntervalMin": 3,
            "stateChangeIntervalMax": 10,
            "reducedSpeedKbps": 8,
            "peer_speed_tiers_enabled": False,
            "peer_tier1_max_peers": 10,
            "peer_tier1_speed_percent": 30,
            "peer_tier2_max_peers": 40,
            "peer_tier2_speed_percent": 50,
            "peer_tier3_max_peers": 80,
            "peer_tier3_speed_percent": 65,
            "peer_tier4_max_peers": 150,
            "peer_tier4_speed_percent": 75,
            "peer_tier5_speed_percent": 90,
        }
        sim.update_config(cfg)
        self.assertEqual(sim.min_stats_update_interval, 5)
        self.assertFalse(sim.enable_speed_variation)
        self.assertEqual(sim.speed_variation_percent, 10)
        self.assertFalse(sim.seeding_only_mode)
        self.assertEqual(sim.pause_duration_min, 15)
        self.assertEqual(sim.pause_duration_max, 60)
        self.assertEqual(sim.reduced_speed_duration_min, 30)
        self.assertEqual(sim.reduced_speed_duration_max, 120)
        self.assertEqual(sim.state_change_interval_min, 3)
        self.assertEqual(sim.state_change_interval_max, 10)
        self.assertEqual(sim.reduced_speed_kbps, 8)
        self.assertFalse(sim.peer_speed_tiers_enabled)
        self.assertEqual(sim.peer_tier1_max_peers, 10)
        self.assertEqual(sim.peer_tier5_speed_percent, 90)
        self.assertIsNone(sim._previous_speed)

    def test_update_config_resets_previous_speed(self):
        sim = StatsSimulator("Reset Test", 1_000_000_000)
        sim._previous_speed = 50000
        sim.update_config({})
        self.assertIsNone(sim._previous_speed)


class TestPeerTierSpeeds(unittest.TestCase):
    """Cover peer tier branches in get_activity_based_upload_speed."""

    def _make_sim(self, tiers_enabled=True):
        sim = StatsSimulator("Peer Tier Test", 5_000_000_000)
        sim.peer_speed_tiers_enabled = tiers_enabled
        sim.peer_tier1_max_peers = 20
        sim.peer_tier1_speed_percent = 40
        sim.peer_tier2_max_peers = 50
        sim.peer_tier2_speed_percent = 55
        sim.peer_tier3_max_peers = 100
        sim.peer_tier3_speed_percent = 60
        sim.peer_tier4_max_peers = 200
        sim.peer_tier4_speed_percent = 80
        sim.peer_tier5_speed_percent = 100
        sim._is_in_fake_pause = False
        sim._current_speed_tier = "high"
        sim._previous_speed = None
        return sim

    def _client(self):
        c = MagicMock()
        c.get_upload_rate_range.return_value = (10240, 102400)
        return c

    @patch(_SVC, None)
    def test_tier1(self):
        speed = self._make_sim().get_activity_based_upload_speed(self._client(), 10, 5)
        self.assertGreater(speed, 0)

    @patch(_SVC, None)
    def test_tier2(self):
        speed = self._make_sim().get_activity_based_upload_speed(self._client(), 20, 10)
        self.assertIsInstance(speed, int)

    @patch(_SVC, None)
    def test_tier3(self):
        speed = self._make_sim().get_activity_based_upload_speed(self._client(), 50, 30)
        self.assertIsInstance(speed, int)

    @patch(_SVC, None)
    def test_tier4(self):
        speed = self._make_sim().get_activity_based_upload_speed(self._client(), 100, 50)
        self.assertIsInstance(speed, int)

    @patch(_SVC, None)
    def test_tier5(self):
        speed = self._make_sim().get_activity_based_upload_speed(self._client(), 300, 200)
        self.assertIsInstance(speed, int)

    @patch(_SVC, None)
    def test_tiers_disabled(self):
        speed = self._make_sim(False).get_activity_based_upload_speed(self._client(), 10, 5)
        self.assertGreater(speed, 0)


class TestDownloadStats(unittest.TestCase):
    """Cover _update_download_stats and _get_realistic_download_speed."""

    def test_download_stats_first_call(self):
        sim = StatsSimulator("DL1", 500_000_000, {"seedingOnlyMode": False})
        sim._is_downloading = True
        sim.downloaded = 0
        sim.left = sim.torrent_size
        sim._last_download_time = None
        c = MagicMock()
        c.get_download_rate_range.return_value = (102400, 1048576)
        sim._update_download_stats(c)
        self.assertGreater(sim.downloaded, 0)
        self.assertGreater(sim.download_speed, 0)

    def test_download_stats_with_prior(self):
        sim = StatsSimulator("DL2", 500_000_000, {"seedingOnlyMode": False})
        sim._is_downloading = True
        sim.downloaded = 100_000_000
        sim.left = 400_000_000
        sim._last_download_time = time.time() - 3
        c = MagicMock()
        c.get_download_rate_range.return_value = (102400, 1048576)
        sim._update_download_stats(c)
        self.assertGreater(sim.downloaded, 100_000_000)

    def test_download_speed_no_attr(self):
        sim = StatsSimulator("DL3", 500_000_000)
        c = MagicMock(spec=[])
        speed = sim._get_realistic_download_speed(c)
        self.assertGreaterEqual(speed, 10240)


class TestActivityState(unittest.TestCase):
    """Cover _manage_activity_state branches."""

    def test_resume_from_pause(self):
        sim = StatsSimulator("P1", 1_000_000_000)
        sim._is_in_fake_pause = True
        sim._pause_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        sim._current_speed_tier = "paused"
        sim.update_individual_state()
        self.assertFalse(sim._is_in_fake_pause)
        self.assertIn(sim._current_speed_tier, ["high", "medium"])

    def test_state_change_trigger(self):
        sim = StatsSimulator("P2", 1_000_000_000)
        sim._is_in_fake_pause = False
        sim._next_pause_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        sim._current_speed_tier = "high"
        sim.update_individual_state()
        self.assertIn(sim._current_speed_tier, ["paused", "low", "high", "medium"])

    def test_reduced_ends(self):
        sim = StatsSimulator("P3", 1_000_000_000)
        sim._is_in_fake_pause = False
        sim._current_speed_tier = "low"
        sim._next_speed_change = datetime.now(timezone.utc) - timedelta(minutes=1)
        sim._next_pause_time = datetime.now(timezone.utc) + timedelta(hours=5)
        sim.update_individual_state()
        self.assertIn(sim._current_speed_tier, ["high", "medium"])


class TestDetailedStatus(unittest.TestCase):
    """Cover get_detailed_status branches."""

    def _sim(self):
        s = StatsSimulator("S", 1_000_000_000)
        s.simulate_natural_seeding_start()
        return s

    @patch(_SVC, None)
    def test_paused(self):
        s = self._sim()
        s._is_in_fake_pause = True
        s._pause_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        status = s.get_status_info()
        self.assertEqual(status["status"], "pause_fake")

    @patch(_SVC, None)
    def test_high(self):
        s = self._sim()
        s._is_in_fake_pause = False
        s._current_speed_tier = "high"
        s._next_speed_change = datetime.now(timezone.utc) + timedelta(hours=2, minutes=30)
        st = s.get_status_info()
        self.assertEqual(st["status"], "seeding_active")
        self.assertIn("h", st["time_until_change_formatted"])

    @patch(_SVC, None)
    def test_low(self):
        s = self._sim()
        s._is_in_fake_pause = False
        s._current_speed_tier = "low"
        s._next_speed_change = datetime.now(timezone.utc) + timedelta(minutes=15)
        st = s.get_status_info()
        self.assertEqual(st["status"], "seeding_low")

    @patch(_SVC, None)
    def test_medium(self):
        s = self._sim()
        s._is_in_fake_pause = False
        s._current_speed_tier = "medium"
        s._next_speed_change = datetime.now(timezone.utc) + timedelta(seconds=30)
        st = s.get_status_info()
        self.assertEqual(st["status"], "seeding_active")

    @patch(_SVC, None)
    def test_soon(self):
        s = self._sim()
        s._is_in_fake_pause = False
        s._current_speed_tier = "high"
        s._next_speed_change = datetime.now(timezone.utc) - timedelta(seconds=5)
        st = s.get_status_info()
        self.assertEqual(st["time_until_change_formatted"], "Soon")


class TestDownloadPhase(unittest.TestCase):
    """Cover is_in_downloading_phase."""

    def test_not_downloading(self):
        sim = StatsSimulator("D1", 1_000_000_000)
        sim._is_downloading = False
        self.assertFalse(sim.is_in_downloading_phase())

    def test_no_completion_time(self):
        sim = StatsSimulator("D2", 1_000_000_000)
        sim._is_downloading = True
        sim._download_completion_time = None
        self.assertTrue(sim.is_in_downloading_phase())

    def test_within_delay(self):
        sim = StatsSimulator("D3", 1_000_000_000)
        sim._is_downloading = True
        sim._download_completion_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        sim._seeding_start_delay_min = 30
        self.assertTrue(sim.is_in_downloading_phase())

    def test_past_delay(self):
        sim = StatsSimulator("D4", 1_000_000_000)
        sim._is_downloading = True
        sim._download_completion_time = datetime.now(timezone.utc) - timedelta(hours=1)
        sim._seeding_start_delay_min = 5
        self.assertFalse(sim.is_in_downloading_phase())


class TestDisplayStats(unittest.TestCase):
    """Cover update_stats_for_display branches."""

    @patch(_SVC, None)
    def test_not_running(self):
        sim = StatsSimulator("U1", 1_000_000_000)
        sim.update_stats_for_display(MagicMock(), is_running=False)
        self.assertEqual(sim.upload_speed, 0)

    @patch(_SVC, None)
    def test_first_call(self):
        sim = StatsSimulator("U2", 1_000_000_000)
        sim.simulate_natural_seeding_start()
        sim._display_update_time = None
        c = MagicMock()
        c.get_upload_rate_range.return_value = (10240, 102400)
        sim.update_stats_for_display(c, is_running=True, seeders=5, leechers=3)
        self.assertIsNotNone(sim._display_update_time)

    @patch(_SVC, None)
    def test_accumulates_upload(self):
        sim = StatsSimulator("U3", 1_000_000_000)
        sim.simulate_natural_seeding_start()
        sim.uploaded = 0
        c = MagicMock()
        c.get_upload_rate_range.return_value = (10240, 102400)
        sim.update_stats_for_display(c, is_running=True, seeders=5, leechers=3)
        sim._display_update_time = time.time() - 5
        sim.update_stats_for_display(c, is_running=True, seeders=5, leechers=3)
        self.assertGreater(sim.uploaded, 0)
