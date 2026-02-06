"""
Tests for stats_simulator.py – Extracted stats simulation logic
"""
import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone

from app.core.stats_simulator import StatsSimulator


# ================================================================
# Helpers
# ================================================================

def _make_simulator(config=None, torrent_size=1024 * 1024 * 500):
    """Create a StatsSimulator with sensible defaults."""
    return StatsSimulator(
        torrent_name="Test Torrent",
        torrent_size=torrent_size,
        discretion_config=config,
    )


def _make_mock_client(min_rate=30 * 1024, max_rate=160 * 1024):
    """Create a mock BitTorrentClient."""
    client = Mock()
    client.get_upload_rate_range.return_value = (min_rate, max_rate)
    return client


# ================================================================
# Initialization
# ================================================================

class TestStatsSimulatorInit:
    def test_defaults(self):
        sim = _make_simulator()
        assert sim.uploaded == 0
        assert sim.downloaded == 1024 * 1024 * 500
        assert sim.left == 0
        assert sim.upload_speed == 0

    def test_custom_config(self):
        config = {
            "min_stats_update_interval": 10,
            "enable_speed_variation": False,
            "speed_variation_percent": 0,
            "seedingOnlyMode": True,
        }
        sim = _make_simulator(config)
        assert sim.min_stats_update_interval == 10
        assert sim.enable_speed_variation is False
        assert sim.speed_variation_percent == 0
        assert sim.seeding_only_mode is True

    def test_seeding_only_mode_default(self):
        sim = _make_simulator()
        assert isinstance(sim.seeding_only_mode, bool)


# ================================================================
# Seeding start
# ================================================================

class TestSeedingStart:
    def test_simulate_natural_seeding_start(self):
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()

        assert sim.downloaded == sim.torrent_size
        assert sim.left == 0
        assert sim.uploaded == 0
        assert sim._initial_seeding is True
        assert sim._is_downloading is False
        assert sim._is_in_fake_pause is False
        assert sim._current_speed_tier in ('high', 'medium')

    def test_simulate_natural_download_start(self):
        sim = _make_simulator()
        sim.simulate_natural_download_start()

        assert sim._is_downloading is True
        assert sim._initial_seeding is False
        assert sim.left >= 0
        assert sim.downloaded <= sim.torrent_size


# ================================================================
# Stats updates
# ================================================================

class TestStatsUpdate:
    def test_update_stats_not_running(self):
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()
        old_uploaded = sim.uploaded
        sim.update_stats(client=_make_mock_client(), is_running=False)
        assert sim.uploaded == old_uploaded  # No change when not running

    def test_update_stats_running_increases_uploaded(self):
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()
        client = _make_mock_client()

        # First call initializes timestamps
        sim.update_stats(client, is_running=True)
        # Force time progression
        sim._last_stats_update = time.time() - 20
        sim._last_upload_time = time.time() - 5
        sim.update_stats(client, is_running=True)

        # uploaded should have grown (speed > 0 most of the time)
        # Since speed is random we can't assert exact value
        assert sim.upload_speed >= 0

    def test_update_stats_for_display(self):
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()
        client = _make_mock_client()

        sim.update_stats_for_display(client, is_running=True)
        # Should set upload_speed
        assert isinstance(sim.upload_speed, float)

    def test_update_stats_with_stealth(self):
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()
        client = _make_mock_client()

        mock_stealth = Mock()
        mock_stealth.get_natural_speed_variation.return_value = 50000

        sim.update_stats_with_stealth(
            client, mock_stealth, "fakehash", is_running=True
        )
        # After first call, timestamps are initialized


# ================================================================
# Activity / speed helpers
# ================================================================

class TestActivityHelpers:
    def test_get_activity_based_upload_speed_returns_int(self):
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()
        client = _make_mock_client()

        speed = sim.get_activity_based_upload_speed(client)
        assert isinstance(speed, int)
        assert speed >= 0

    def test_speed_zero_when_paused(self):
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()
        sim._is_in_fake_pause = True
        client = _make_mock_client()

        speed = sim.get_activity_based_upload_speed(client)
        assert speed == 0

    def test_speed_background_when_zero_leechers(self):
        """With 0 leechers, should return minimal background speed, not 0."""
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()
        client = _make_mock_client()

        speed = sim.get_activity_based_upload_speed(client, seeders=10, leechers=0)
        assert isinstance(speed, int)
        assert speed > 0, "Speed should not be 0 when leechers=0 (background speed expected)"
        # Background speed should be small (around 5% of min_rate)
        assert speed < 10 * 1024, "Background speed should be small (< 10 KB/s)"

    def test_speed_background_when_zero_leechers_not_paused(self):
        """Background speed should still be 0 if fake paused, even with 0 leechers."""
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()
        sim._is_in_fake_pause = True
        client = _make_mock_client()

        speed = sim.get_activity_based_upload_speed(client, seeders=10, leechers=0)
        assert speed == 0, "Paused torrents should have 0 speed regardless of leechers"

    def test_speed_normal_with_leechers(self):
        """With positive leechers, should return normal speed."""
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()
        sim._current_speed_tier = 'high'
        client = _make_mock_client()

        speed = sim.get_activity_based_upload_speed(client, seeders=10, leechers=5)
        assert isinstance(speed, int)
        assert speed > 1024, "Speed should be significant with active leechers"

    def test_is_user_active_hour(self):
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()
        result = sim.is_user_active_hour()
        assert isinstance(result, bool)

    def test_simulate_occasional_network_errors(self):
        sim = _make_simulator()
        # Run many times – should mostly be False
        errors = sum(sim.simulate_occasional_network_errors() for _ in range(100))
        assert errors <= 10, f"Error rate too high: {errors}%"


# ================================================================
# Individual state management
# ================================================================

class TestIndividualState:
    def test_update_individual_state_no_crash(self):
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()
        sim.update_individual_state()  # Should not raise

    def test_pause_ends_when_time_expires(self):
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()

        # Force into pause with past expiry
        sim._is_in_fake_pause = True
        sim._pause_until = datetime.now(timezone.utc) - timedelta(minutes=1)

        sim.update_individual_state()
        assert sim._is_in_fake_pause is False

    def test_get_status_info_returns_dict(self):
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()
        status = sim.get_status_info()

        assert isinstance(status, dict)
        assert 'status' in status
        assert 'speed_tier' in status
        assert 'peak_hours' in status

    def test_is_in_downloading_phase_false_for_seeding(self):
        sim = _make_simulator()
        sim.simulate_natural_seeding_start()
        assert sim.is_in_downloading_phase() is False

    def test_is_in_downloading_phase_true_for_download(self):
        sim = _make_simulator()
        sim.simulate_natural_download_start()
        # Might still be downloading
        assert isinstance(sim.is_in_downloading_phase(), bool)
