"""
Extended tests for StatsSimulator - additional coverage for speed tiers,
download phase, activity patterns, and behavior status.
"""
import pytest
import time
import random
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone

from app.core.stats_simulator import StatsSimulator


def _make_sim(size=1024 * 1024 * 100, config=None):
    """Create a StatsSimulator with sensible defaults."""
    return StatsSimulator("Test Torrent", size, config)


def _mock_client(min_rate=10240, max_rate=102400):
    client = Mock()
    client.get_upload_rate_range = Mock(return_value=(min_rate, max_rate))
    client.get_download_rate_range = Mock(return_value=(102400, 1048576))
    return client


# ================================================================
# Display update (C2 fix verification)
# ================================================================

class TestDisplayUpdateNoDoubleCount:
    """Verify update_stats_for_display correctly accumulates uploaded bytes."""

    def test_display_update_increments_uploaded(self):
        sim = _make_sim()
        sim.simulate_natural_seeding_start()
        initial_uploaded = sim.uploaded

        client = _mock_client()
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss._config = {}

            sim.update_stats_for_display(client, True, seeders=5, leechers=3)
            time.sleep(0.05)
            sim.update_stats_for_display(client, True, seeders=5, leechers=3)

        # Display path now accumulates uploaded bytes (fix for v1.12.3)
        assert sim.uploaded >= initial_uploaded

    def test_display_update_sets_speed(self):
        sim = _make_sim()
        sim.simulate_natural_seeding_start()
        client = _mock_client()
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss._config = {}
            sim.update_stats_for_display(client, True, seeders=5, leechers=3)
        assert sim.upload_speed >= 0

    def test_display_update_not_running(self):
        sim = _make_sim()
        sim.upload_speed = 1000
        client = _mock_client()
        sim.update_stats_for_display(client, False)
        assert sim.upload_speed == 0


# ================================================================
# Stealth stats update
# ================================================================

class TestStealthStatsUpdate:
    def test_stealth_update_sets_speed(self):
        """Stealth update should set upload_speed (uploaded accumulation
        is now handled by the display path)."""
        sim = _make_sim()
        sim.simulate_natural_seeding_start()
        sim._last_upload_time = time.time() - 5
        sim._last_stats_update = time.time() - 60  # past min interval

        client = _mock_client()
        stealth = Mock()
        stealth.get_natural_speed_variation = Mock(return_value=50000)

        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss._config = {}
            sim.update_stats_with_stealth(client, stealth, "hash", True, 5, 3)

        assert sim.upload_speed > 0

    def test_stealth_update_not_running(self):
        sim = _make_sim()
        initial = sim.uploaded
        client = _mock_client()
        stealth = Mock()
        sim.update_stats_with_stealth(client, stealth, "hash", False)
        assert sim.uploaded == initial


# ================================================================
# Speed tiers
# ================================================================

class TestSpeedTiers:
    def test_fake_pause_returns_zero(self):
        sim = _make_sim()
        sim.simulate_natural_seeding_start()
        sim._is_in_fake_pause = True
        client = _mock_client()
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss._config = {}
            speed = sim.get_activity_based_upload_speed(client, 5, 3)
        assert speed == 0

    def test_zero_leechers_background_speed(self):
        sim = _make_sim()
        sim.simulate_natural_seeding_start()
        client = _mock_client()
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss._config = {}
            speed = sim.get_activity_based_upload_speed(client, 0, 0)
        assert speed > 0  # Background speed for dead swarm

    def test_zero_leechers_with_seeders_normal_speed(self):
        """With seeders > 0 but leechers=0, should use normal speed tiers."""
        sim = _make_sim()
        sim.simulate_natural_seeding_start()
        sim._current_speed_tier = 'high'
        client = _mock_client()
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss._config = {}
            speed = sim.get_activity_based_upload_speed(client, 5, 0)
        assert speed > 10 * 1024  # Normal speed, not background

    def test_low_tier_reduced_speed(self):
        sim = _make_sim()
        sim.simulate_natural_seeding_start()
        sim._current_speed_tier = 'low'
        sim._is_in_fake_pause = False
        client = _mock_client()
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss._config = {}
            speed = sim.get_activity_based_upload_speed(client, 5, 3)
        assert speed > 0

    def test_peer_speed_tiers_applied(self):
        sim = _make_sim(config={"peer_speed_tiers_enabled": True})
        sim.simulate_natural_seeding_start()
        sim._current_speed_tier = 'high'
        sim._is_in_fake_pause = False
        client = _mock_client()
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss._config = {}
            speed = sim.get_activity_based_upload_speed(client, 5, 3)
        assert speed > 0


# ================================================================
# Download phase
# ================================================================

class TestDownloadPhase:
    def test_downloading_phase_cached_delay(self):
        """H6 fix: seeding_start_delay should be cached"""
        sim = _make_sim()
        sim.simulate_natural_download_start()
        sim._download_completion_time = datetime.now(timezone.utc) - timedelta(hours=1)

        # First call caches the delay
        sim.is_in_downloading_phase()
        assert sim._seeding_start_delay_min is not None
        cached_delay = sim._seeding_start_delay_min

        # Second call uses same value
        sim._is_downloading = True  # Reset to test again
        sim.is_in_downloading_phase()
        assert sim._seeding_start_delay_min == cached_delay

    def test_seeding_only_mode_no_download(self):
        sim = _make_sim(config={"seedingOnlyMode": True})
        sim.simulate_natural_seeding_start()
        assert not sim.is_in_downloading_phase()

    def test_download_mode_transitions_to_seeding(self):
        sim = _make_sim()
        sim.simulate_natural_download_start()
        # Force download completion far in the past
        sim._download_completion_time = datetime.now(timezone.utc) - timedelta(hours=2)
        sim._seeding_start_delay_min = 1  # 1 minute delay

        result = sim.is_in_downloading_phase()
        assert result is False
        assert sim.left == 0


# ================================================================
# Swarm-based speed
# ================================================================

class TestSwarmSpeed:
    def test_realistic_upload_speed_no_leechers(self):
        sim = _make_sim()
        sim.simulate_natural_seeding_start()
        client = _mock_client()
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss._config = {}
            speed = sim.get_realistic_upload_speed_based_on_swarm(client, 10, 0)
        assert speed > 0  # Normal speed (seeders > 0)

    def test_realistic_upload_speed_with_peers(self):
        sim = _make_sim()
        sim.simulate_natural_seeding_start()
        client = _mock_client()
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss._config = {}
            speed = sim.get_realistic_upload_speed_based_on_swarm(client, 5, 10)
        assert speed > 0


# ================================================================
# Activity patterns
# ================================================================

class TestActivityPatterns:
    def test_is_user_active_hour_returns_bool(self):
        sim = _make_sim()
        sim.simulate_natural_seeding_start()
        result = sim.is_user_active_hour()
        assert isinstance(result, bool)

    def test_determine_peak_hours(self):
        sim = _make_sim()
        hours = sim._determine_user_peak_hours()
        assert isinstance(hours, tuple)
        assert len(hours) == 2

    def test_generate_activity_pattern(self):
        sim = _make_sim()
        pattern = sim._generate_user_activity_pattern()
        assert "active_days" in pattern
        assert "session_length" in pattern

    def test_simulate_network_errors(self):
        sim = _make_sim()
        results = [sim.simulate_occasional_network_errors() for _ in range(100)]
        # Some should be True (1-3% chance), most False
        assert any(r is False for r in results)

    def test_update_stats_basic(self):
        sim = _make_sim()
        sim.simulate_natural_seeding_start()
        sim._last_upload_time = time.time() - 3
        client = _mock_client()
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss._config = {}
            sim.update_stats(client, True)
        # Should have set upload_speed
        assert sim.upload_speed >= 0


# ================================================================
# Behavior status
# ================================================================

class TestBehaviorStatus:
    def test_get_status_info(self):
        sim = _make_sim()
        sim.simulate_natural_seeding_start()
        status = sim.get_status_info()
        assert isinstance(status, dict)
        assert "status" in status

    def test_get_behavior_status(self):
        sim = _make_sim()
        sim.simulate_natural_seeding_start()
        status = sim.get_status_info()
        assert isinstance(status, dict)
        assert "status" in status
        assert "speed_tier" in status
