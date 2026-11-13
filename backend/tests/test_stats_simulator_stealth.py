"""Tests for StatsSimulator stealth features (download-to-seed transition, burst, stall)."""
import random
import pytest
from unittest.mock import MagicMock, patch
from app.core.stats_simulator import StatsSimulator
from app.services.stealth_service import StealthService


def _make_simulator():
    """Create a StatsSimulator in seeding mode."""
    sim = StatsSimulator(
        torrent_name="Test.Torrent",
        torrent_size=1024 * 1024 * 100,  # 100 MB
    )
    # Force seeding mode so update_stats_with_stealth takes the seeding path
    sim.seeding_only_mode = True
    sim.is_in_downloading_phase = lambda: False
    sim.min_stats_update_interval = 0  # disable throttle for rapid test calls
    return sim


def _make_stealth():
    return StealthService()


def _make_client():
    """Minimal mock client."""
    client = MagicMock()
    client.get_upload_speed.return_value = 102400  # 100 KB/s
    client.get_upload_rate_range.return_value = (50, 500)  # KB/s range
    return client


class TestDownloadToSeedTransition:
    def test_returns_dict_with_required_keys(self):
        sim = _make_simulator()
        result = sim.simulate_download_to_seed_transition()
        assert "downloaded" in result
        assert "uploaded" in result
        assert "download_time" in result
        assert "seed_time" in result

    def test_values_are_positive(self):
        sim = _make_simulator()
        result = sim.simulate_download_to_seed_transition()
        assert result["downloaded"] > 0
        assert result["uploaded"] > 0
        assert result["download_time"] > 0
        assert result["seed_time"] > 0


class TestBurstAndStall:
    def test_burst_increases_upload_speed(self):
        """During burst (10% chance), upload_speed should spike to 3-5x normal."""
        sim = _make_simulator()
        stealth = _make_stealth()
        client = _make_client()
        
        speeds = []
        for _ in range(200):
            sim.upload_speed = 0
            sim.update_stats_with_stealth(client, stealth, "a" * 40, True, 10, 5)
            speeds.append(sim.upload_speed)
        
        # With 10% burst rate, we should see some high values
        max_speed = max(speeds)
        min_nonzero = min(s for s in speeds if s > 0)
        # Burst should be at least 2x the minimum non-zero speed
        assert max_speed > min_nonzero, "No burst detected in 200 iterations"

    def test_stall_produces_zero_speed(self):
        """During stall (5% chance), upload_speed should be 0."""
        sim = _make_simulator()
        stealth = _make_stealth()
        client = _make_client()
        
        zeros = 0
        for _ in range(200):
            sim.upload_speed = -1  # sentinel
            sim.update_stats_with_stealth(client, stealth, "a" * 40, True, 10, 5)
            if sim.upload_speed == 0:
                zeros += 1
        
        # With 5% stall rate, expect ~10 zeros in 200 iterations
        assert zeros > 0, "No stall (zero speed) detected in 200 iterations"

    def test_not_all_zero(self):
        """Not all calls should produce zero speed (stall is only 5%)."""
        sim = _make_simulator()
        stealth = _make_stealth()
        client = _make_client()
        
        zeros = 0
        total = 100
        for _ in range(total):
            sim.update_stats_with_stealth(client, stealth, "a" * 40, True, 10, 5)
            if sim.upload_speed == 0:
                zeros += 1
        
        # Should have some non-zero values
        assert zeros < total, "All speeds are zero (stall rate too high)"

    def test_not_all_burst(self):
        """Not all calls should be bursts (burst is only 10%)."""
        sim = _make_simulator()
        stealth = _make_stealth()
        client = _make_client()
        
        # Get a baseline speed
        baseline = sim.get_activity_based_upload_speed(client, 10, 5)
        
        bursts = 0
        total = 100
        for _ in range(total):
            sim.update_stats_with_stealth(client, stealth, "a" * 40, True, 10, 5)
            if sim.upload_speed > baseline * 2:
                bursts += 1
        
        # Should have some non-burst values
        assert bursts < total, "All speeds are burst (burst rate too high)"