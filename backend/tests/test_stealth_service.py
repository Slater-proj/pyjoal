"""
Tests for StealthService - Advanced anti-detection
"""
import random
import hashlib
from datetime import datetime, timezone, timedelta
from app.services.stealth_service import StealthService


def _make_service():
    return StealthService()


class TestSessionProfile:
    def test_generates_consistent_profile(self):
        """Same torrent hash → same profile values"""
        svc = _make_service()
        p1 = svc.get_session_profile("abc123")
        # Second call returns cached profile
        p2 = svc.get_session_profile("abc123")
        assert p1 is p2
        assert p1['user_agent'] is not None
        assert p1['session_port'] >= 49152

    def test_different_hashes_different_profiles(self):
        svc = _make_service()
        p1 = svc.get_session_profile("hash1")
        p2 = svc.get_session_profile("hash2")
        # Different hashes should produce different ports (with high probability)
        assert p1 is not p2

    def test_profile_has_required_keys(self):
        svc = _make_service()
        profile = svc.get_session_profile("test")
        required_keys = [
            'user_agent', 'client_name', 'session_port',
            'announce_variance', 'activity_pattern',
            'session_start', 'connection_stability'
        ]
        for key in required_keys:
            assert key in profile, f"Missing key: {key}"

    def test_does_not_corrupt_global_random(self):
        """H1 fix: _generate_session_profile should NOT call random.seed() globally"""
        svc = _make_service()
        # Set a known seed
        random.seed(42)
        val_before = random.random()
        # Reset to same seed
        random.seed(42)
        # Generate a profile (should use local RNG)
        svc._generate_session_profile("test_hash_xyz")
        # If global PRNG was NOT corrupted, random.random() should be same
        val_after = random.random()
        assert val_before == val_after, "Global PRNG was corrupted by _generate_session_profile"

    def test_activity_patterns_valid(self):
        svc = _make_service()
        valid_patterns = {'steady', 'burst', 'declining', 'growing'}
        for i in range(20):
            p = svc._generate_session_profile(f"hash_{i}")
            assert p['activity_pattern'] in valid_patterns


class TestNaturalAnnounceInterval:
    def test_returns_integer(self):
        svc = _make_service()
        interval = svc.get_natural_announce_interval("hash", 1800)
        assert isinstance(interval, int)
        assert interval >= 90  # Minimum bound

    def test_minimum_bound(self):
        svc = _make_service()
        # Even with a very short base, should respect 90s minimum
        interval = svc.get_natural_announce_interval("hash", 10)
        assert interval >= 90

    def test_variance_applied(self):
        svc = _make_service()
        intervals = set()
        for i in range(50):
            intervals.add(svc.get_natural_announce_interval(f"h{i}", 1800))
        # Should have some variation
        assert len(intervals) > 1


class TestTimeFactor:
    def test_time_factor_ranges(self):
        svc = _make_service()
        for hour in range(24):
            factor = svc._get_time_factor(hour)
            assert 0.5 <= factor <= 2.0, f"Factor {factor} out of range for hour {hour}"

    def test_time_factor_caching(self):
        svc = _make_service()
        f1 = svc._get_time_factor(12)
        f2 = svc._get_time_factor(12)
        assert f1 == f2  # Cached


class TestDisconnectSimulation:
    def test_should_simulate_returns_bool(self):
        svc = _make_service()
        result = svc.should_simulate_temporary_disconnect("hash")
        assert isinstance(result, bool)

    def test_disconnect_duration_range(self):
        svc = _make_service()
        for _ in range(20):
            duration = svc.get_disconnect_duration()
            assert 120 <= duration <= 900


class TestSpeedVariation:
    def test_zero_speed(self):
        svc = _make_service()
        assert svc.get_natural_speed_variation(0, "hash") == 0

    def test_positive_speed_returns_positive(self):
        svc = _make_service()
        speed = svc.get_natural_speed_variation(100000, "hash")
        assert speed >= 0

    def test_speed_caching(self):
        svc = _make_service()
        s1 = svc.get_natural_speed_variation(50000, "hash")
        s2 = svc.get_natural_speed_variation(50000, "hash")
        # Same input within 30s → cached
        assert s1 == s2


class TestGaussianInterval:
    def test_returns_integer(self):
        svc = _make_service()
        interval = svc.get_gaussian_interval(1800)
        assert isinstance(interval, int)

    def test_bounds(self):
        svc = _make_service()
        for _ in range(100):
            interval = svc.get_gaussian_interval(1800)
            assert interval >= 60  # Min bound
            assert interval <= 3600  # 200% of base


class TestDownloadToSeedTransition:
    def test_returns_dict_with_required_keys(self):
        svc = _make_service()
        result = svc.simulate_download_to_seed_transition("hash", 1024 * 1024 * 100)
        assert "downloaded" in result
        assert "uploaded" in result
        assert "left" in result
        assert result["left"] == 0

    def test_consistent_for_same_hash(self):
        svc = _make_service()
        r1 = svc.simulate_download_to_seed_transition("hash", 1000000)
        r2 = svc.simulate_download_to_seed_transition("hash", 1000000)
        assert r1["downloaded"] == r2["downloaded"]


class TestPortRotation:
    def test_port_in_ephemeral_range(self):
        svc = _make_service()
        port = svc.get_rotated_port("hash")
        assert 49152 <= port <= 65535

    def test_consistent_within_period(self):
        svc = _make_service()
        p1 = svc.get_rotated_port("hash", rotation_interval_hours=24)
        p2 = svc.get_rotated_port("hash", rotation_interval_hours=24)
        assert p1 == p2


class TestCorruptField:
    def test_returns_non_negative(self):
        svc = _make_service()
        for i in range(20):
            corrupt = svc.get_corrupt_field_value(f"hash_{i}", 1000000)
            assert corrupt >= 0


class TestCryptoFlags:
    def test_known_client(self):
        svc = _make_service()
        flags = svc.get_crypto_support_flags("qBittorrent 5.1.4")
        assert flags["supportcrypto"] is True

    def test_unknown_client_default(self):
        svc = _make_service()
        flags = svc.get_crypto_support_flags("UnknownClient")
        assert "supportcrypto" in flags
