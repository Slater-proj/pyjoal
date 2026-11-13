"""
Tests for anti-detection features:
1. Peer ID with client-specific prefix (qBittorrent, Transmission, Deluge)
2. Minimum stop→start delay (cooldown)
"""
import time
import asyncio
from unittest.mock import patch, AsyncMock

from app.core.bittorrent_client import BitTorrentClient
from app.services.seeder_service import SeederService


# ---------------------------------------------------------------------------
# Point 1: Peer ID prefix
# ---------------------------------------------------------------------------

class TestPeerIdPrefix:
    """The peer ID must start with a known client prefix, not random hex."""

    def test_peer_id_starts_with_prefix(self):
        """Peer ID should begin with the client's fixed prefix."""
        client = BitTorrentClient()
        peer_id = client.generate_peer_id()
        # Must be 20 chars (standard BT peer ID length)
        assert len(peer_id) == 20, f"Peer ID length {len(peer_id)} != 20"
        # Must start with a known prefix
        known_prefixes = ['-qB', '-TR', '-DE', '-lt', '-UT', '-XT', '-am', '-AX', '-qT', '-BT']
        assert any(peer_id.startswith(p) for p in known_prefixes), \
            f"Peer ID '{peer_id}' doesn't start with a known client prefix"

    def test_peer_id_is_20_chars(self):
        """Standard BitTorrent peer ID is exactly 20 characters."""
        client = BitTorrentClient()
        for _ in range(50):
            peer_id = client.generate_peer_id()
            assert len(peer_id) == 20

    def test_peer_id_not_all_random_hex(self):
        """The first 3-4 chars should be a recognizable prefix, not random hex."""
        client = BitTorrentClient()
        peer_id = client.generate_peer_id()
        # A random hex peer ID would start with 0-9a-fA-F
        # A client-specific one starts with a letter like 'q', 'T', 'D'
        first_char = peer_id[1]  # skip the dash
        assert first_char.isalpha(), f"Expected alpha prefix, got '{first_char}'"

    def test_peer_id_deterministic_per_client(self):
        """Same client config → same prefix (but different suffix)."""
        client = BitTorrentClient()
        ids = [client.generate_peer_id() for _ in range(10)]
        # All should have the same first 4 chars (prefix)
        prefixes = set(pid[:4] for pid in ids)
        assert len(prefixes) == 1, f"Expected consistent prefix, got {prefixes}"


# ---------------------------------------------------------------------------
# Point 2: Stop→start cooldown
# ---------------------------------------------------------------------------

class TestStopStartCooldown:
    """A real client doesn't restart instantly after a stop."""

    def test_min_delay_constant_exists(self):
        """SeederService should define a minimum stop→start delay."""
        assert hasattr(SeederService, 'MIN_STOP_START_DELAY')
        assert SeederService.MIN_STOP_START_DELAY >= 60, \
            "Cooldown should be at least 60 seconds"

    def test_last_stop_time_initialized(self):
        """_last_stop_time should start as None."""
        svc = SeederService()
        assert svc._last_stop_time is None

    def test_start_waits_after_recent_stop(self):
        """If stop was 30s ago and cooldown is 120s, start should wait ~90s."""
        svc = SeederService()
        svc._last_stop_time = time.time() - 30  # stopped 30s ago
        svc.MIN_STOP_START_DELAY = 120

        start_time = time.time()
        # Mock the heavy parts of start() so we only measure the wait
        with patch.object(svc, '_start_announcers', new_callable=AsyncMock):
            with patch.object(svc, '_start_monitor', new_callable=AsyncMock):
                asyncio.run(svc.start())

        elapsed = time.time() - start_time
        # Should have waited roughly 90s (120 - 30), allow some tolerance
        assert elapsed >= 80, f"Expected ~90s wait, got {elapsed:.1f}s"

    def test_start_no_wait_after_long_stop(self):
        """If stop was 5min ago and cooldown is 120s, start should be instant."""
        svc = SeederService()
        svc._last_stop_time = time.time() - 300  # stopped 5min ago
        svc.MIN_STOP_START_DELAY = 120

        start_time = time.time()
        with patch.object(svc, '_start_announcers', new_callable=AsyncMock):
            with patch.object(svc, '_start_monitor', new_callable=AsyncMock):
                asyncio.run(svc.start())

        elapsed = time.time() - start_time
        assert elapsed < 5, f"Expected instant start, took {elapsed:.1f}s"

    def test_start_no_wait_on_first_start(self):
        """First start (no previous stop) should not wait."""
        svc = SeederService()
        svc._last_stop_time = None  # never stopped

        start_time = time.time()
        with patch.object(svc, '_start_announcers', new_callable=AsyncMock):
            with patch.object(svc, '_start_monitor', new_callable=AsyncMock):
                asyncio.run(svc.start())

        elapsed = time.time() - start_time
        assert elapsed < 5, f"First start should be instant, took {elapsed:.1f}s"
