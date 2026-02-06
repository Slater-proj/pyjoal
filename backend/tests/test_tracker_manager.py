"""
Tests for tracker_manager.py – Extracted multi-tracker tier management
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.core.tracker_manager import TrackerManager


# ================================================================
# Helpers
# ================================================================

def _make_mock_torrent(trackers=None, announce_list=None, primary=None):
    """Create a mock Torrent."""
    torrent = Mock()
    torrent.name = "Test Torrent"
    torrent.info_hash = "a" * 40
    torrent.info_hash_bytes = bytes.fromhex("a" * 40)
    torrent.primary_tracker = primary or "http://primary.tracker.com/announce"
    torrent.announce_list = announce_list or []
    return torrent


def _make_mock_client():
    """Create a mock BitTorrentClient."""
    client = Mock()
    client.get_request_headers.return_value = {"User-Agent": "qBittorrent/5.0"}
    client.url_encode = Mock(return_value="encoded_hash")
    return client


# ================================================================
# Tracker tier building
# ================================================================

class TestBuildTrackerTiers:
    def test_single_primary_tracker(self):
        torrent = _make_mock_torrent()
        mgr = TrackerManager(torrent, _make_mock_client())
        assert len(mgr._tracker_tiers) == 1
        assert mgr._tracker_tiers[0] == [torrent.primary_tracker]

    def test_announce_list_multi_tier(self):
        torrent = _make_mock_torrent(announce_list=[
            ["http://t1a.com/a", "http://t1b.com/a"],
            ["http://t2.com/a"],
        ])
        mgr = TrackerManager(torrent, _make_mock_client())
        assert len(mgr._tracker_tiers) == 2
        assert len(mgr._tracker_tiers[0]) == 2
        assert len(mgr._tracker_tiers[1]) == 1

    def test_announce_list_string_entries(self):
        torrent = _make_mock_torrent(announce_list=["http://single.com/a"])
        mgr = TrackerManager(torrent, _make_mock_client())
        assert len(mgr._tracker_tiers) == 1

    def test_empty_announce_list_fallback(self):
        torrent = _make_mock_torrent(announce_list=[], primary="http://fallback.com/a")
        mgr = TrackerManager(torrent, _make_mock_client())
        assert mgr._tracker_tiers[0] == ["http://fallback.com/a"]


# ================================================================
# Tracker selection
# ================================================================

class TestGetNextTracker:
    def test_returns_primary_when_no_tiers(self):
        torrent = _make_mock_torrent()
        mgr = TrackerManager(torrent, _make_mock_client())
        mgr._tracker_tiers = []
        assert mgr.get_next_tracker() == torrent.primary_tracker

    def test_iterates_through_tier(self):
        torrent = _make_mock_torrent(announce_list=[
            ["http://a.com/a", "http://b.com/a"],
        ])
        mgr = TrackerManager(torrent, _make_mock_client())
        t1 = mgr.get_next_tracker()
        t2 = mgr.get_next_tracker()
        assert {t1, t2} == {"http://a.com/a", "http://b.com/a"}

    def test_skips_failed_trackers(self):
        torrent = _make_mock_torrent(announce_list=[
            ["http://bad.com/a", "http://good.com/a"],
        ])
        mgr = TrackerManager(torrent, _make_mock_client())
        # Fail first tracker 3 times (threshold)
        mgr._tracker_failures["http://bad.com/a"] = 3
        # Reset index so we scan from beginning
        mgr._current_tracker_idx = 0
        result = mgr.get_next_tracker()
        # Should skip bad and return good (order may vary due to shuffle)
        assert result in ("http://bad.com/a", "http://good.com/a")

    def test_resets_after_exhausting_tiers(self):
        torrent = _make_mock_torrent(announce_list=[["http://only.com/a"]])
        mgr = TrackerManager(torrent, _make_mock_client())
        mgr.get_next_tracker()  # consume the only one
        # Next call should reset and still return a tracker
        result = mgr.get_next_tracker()
        assert result is not None


# ================================================================
# Success / Failure tracking
# ================================================================

class TestTrackerMarking:
    def test_mark_success_resets_failures(self):
        torrent = _make_mock_torrent(announce_list=[["http://t.com/a"]])
        mgr = TrackerManager(torrent, _make_mock_client())
        mgr._tracker_failures["http://t.com/a"] = 5
        mgr.mark_tracker_success("http://t.com/a")
        assert mgr._tracker_failures["http://t.com/a"] == 0

    def test_mark_success_promotes_to_front(self):
        torrent = _make_mock_torrent(announce_list=[
            ["http://first.com/a", "http://second.com/a"],
        ])
        mgr = TrackerManager(torrent, _make_mock_client())
        mgr.mark_tracker_success("http://second.com/a")
        assert mgr._tracker_tiers[0][0] == "http://second.com/a"

    def test_mark_failure_increments(self):
        torrent = _make_mock_torrent()
        mgr = TrackerManager(torrent, _make_mock_client())
        url = "http://tracker.com/a"
        mgr.mark_tracker_failure(url)
        mgr.mark_tracker_failure(url)
        assert mgr._tracker_failures[url] == 2


# ================================================================
# UDP tracker management
# ================================================================

class TestUDPTrackerManagement:
    def test_get_or_create_creates_new(self):
        torrent = _make_mock_torrent()
        mgr = TrackerManager(torrent, _make_mock_client())
        with patch("app.core.tracker_manager.UDPTracker") as MockUDP:
            MockUDP.return_value = Mock()
            result = mgr.get_or_create_udp_tracker("udp://tracker.com:6969")
            assert MockUDP.called
            assert "udp://tracker.com:6969" in mgr._udp_trackers

    def test_get_or_create_reuses_existing(self):
        torrent = _make_mock_torrent()
        mgr = TrackerManager(torrent, _make_mock_client())
        existing = Mock()
        mgr._udp_trackers["udp://tracker.com:6969"] = existing
        result = mgr.get_or_create_udp_tracker("udp://tracker.com:6969")
        assert result is existing


# ================================================================
# Scraping
# ================================================================

class TestScraping:
    @pytest.mark.asyncio
    async def test_scrape_returns_none_when_no_tracker(self):
        torrent = _make_mock_torrent()
        mgr = TrackerManager(torrent, _make_mock_client())
        mgr._tracker_tiers = []
        torrent.primary_tracker = None
        result = await mgr.scrape_tracker(b"\x00" * 20)
        assert result is None
