"""Tests for tracker_manager.py — tier management, scraping, failures."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

import os
os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.core.tracker_manager import TrackerManager


def _make_torrent(primary="http://tracker.example.com/announce",
                  announce_list=None):
    t = MagicMock()
    t.primary_tracker = primary
    t.announce_list = announce_list or []
    t.info_hash_bytes = b"\x01" * 20
    t.name = "TestTorrent"
    return t


def _make_client():
    c = MagicMock()
    c.url_encode = lambda b: b.hex()
    c.get_request_headers = lambda: {"User-Agent": "test/1.0"}
    return c


class TestBuildTrackerTiers:
    def test_single_tracker_no_announce_list(self):
        tm = TrackerManager(_make_torrent(), _make_client())
        tiers = tm._tracker_tiers
        assert len(tiers) == 1
        assert tm._tracker_tiers[0] == [_make_torrent().primary_tracker]

    def test_announce_list_multiple_tiers(self):
        t = _make_torrent(announce_list=[
            ["http://t1.com/announce", "http://t2.com/announce"],
            ["http://t3.com/announce"],
        ])
        tm = TrackerManager(t, _make_client())
        assert len(tm._tracker_tiers) == 2

    def test_announce_list_with_strings(self):
        t = _make_torrent(announce_list=["http://t1.com/announce"])
        tm = TrackerManager(t, _make_client())
        assert len(tm._tracker_tiers) == 1

    def test_empty_announce_list_falls_back_to_primary(self):
        t = _make_torrent(announce_list=[])
        tm = TrackerManager(t, _make_client())
        assert len(tm._tracker_tiers) == 1

    def test_announce_list_with_empty_entries(self):
        t = _make_torrent(announce_list=[[""], [None, ""], []])
        tm = TrackerManager(t, _make_client())
        # empty entries filtered out, fallback to primary
        assert len(tm._tracker_tiers) >= 1


class TestGetNextTracker:
    def test_basic(self):
        tm = TrackerManager(_make_torrent(), _make_client())
        url = tm.get_next_tracker()
        assert "tracker.example.com" in url

    def test_skip_failed_tracker(self):
        t = _make_torrent(announce_list=[
            ["http://bad.com/announce", "http://good.com/announce"],
        ])
        tm = TrackerManager(t, _make_client())
        tm._tracker_failures["http://bad.com/announce"] = 3
        url = tm.get_next_tracker()
        assert url == "http://good.com/announce"

    def test_tier_exhaustion_resets(self):
        t = _make_torrent(announce_list=[
            ["http://t1.com/announce"],
        ])
        tm = TrackerManager(t, _make_client())
        # Exhaust the tier
        url1 = tm.get_next_tracker()
        # Now all trackers are visited, should reset
        url2 = tm.get_next_tracker()
        assert url2 is not None

    def test_no_tiers_returns_primary(self):
        t = _make_torrent(primary="http://x.com/announce")
        t.announce_list = None
        del t.announce_list  # remove attribute
        tm = TrackerManager(t, _make_client())
        tm._tracker_tiers = []
        assert tm.get_next_tracker() == "http://x.com/announce"


class TestTrackerSuccessFailure:
    def test_mark_success_resets_failures(self):
        t = _make_torrent(announce_list=[["http://t1.com/announce"]])
        tm = TrackerManager(t, _make_client())
        tm._tracker_failures["http://t1.com/announce"] = 2
        tm.mark_tracker_success("http://t1.com/announce")
        assert tm._tracker_failures["http://t1.com/announce"] == 0

    def test_mark_success_promotes_tracker(self):
        t = _make_torrent(announce_list=[["http://t1.com/announce", "http://t2.com/announce"]])
        tm = TrackerManager(t, _make_client())
        tm.mark_tracker_success("http://t2.com/announce")
        assert tm._tracker_tiers[0][0] == "http://t2.com/announce"

    def test_mark_failure_increments(self):
        tm = TrackerManager(_make_torrent(), _make_client())
        tm.mark_tracker_failure("http://t.com")
        tm.mark_tracker_failure("http://t.com")
        assert tm._tracker_failures["http://t.com"] == 2


class TestUdpTrackerCache:
    def test_get_or_create(self):
        tm = TrackerManager(_make_torrent(), _make_client())
        with patch("app.core.tracker_manager.UDPTracker") as MockUDP:
            MockUDP.return_value = MagicMock()
            udp1 = tm.get_or_create_udp_tracker("udp://tracker.com:6969")
            udp2 = tm.get_or_create_udp_tracker("udp://tracker.com:6969")
            assert udp1 is udp2
            MockUDP.assert_called_once()


class TestScraping:
    @pytest.mark.asyncio
    async def test_scrape_http_success(self):
        import bencodepy
        tm = TrackerManager(_make_torrent(primary="http://tracker.example.com/announce"), _make_client())
        info_hash = b"\x01" * 20
        scrape_data = bencodepy.encode({
            b"files": {
                info_hash: {
                    b"complete": 5,
                    b"incomplete": 3,
                    b"downloaded": 100,
                }
            }
        })
        with patch("httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = scrape_data
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_response)))
            MockClient.return_value = mock_ctx
            result = await tm._scrape_http("http://tracker.example.com/announce", info_hash)
        assert result is not None
        assert result["seeders"] == 5
        assert result["leechers"] == 3

    @pytest.mark.asyncio
    async def test_scrape_http_not_announce_url(self):
        tm = TrackerManager(_make_torrent(primary="http://tracker.example.com/something"), _make_client())
        result = await tm._scrape_http("http://tracker.example.com/something", b"\x01" * 20)
        assert result is None

    @pytest.mark.asyncio
    async def test_scrape_tracker_no_url(self):
        t = _make_torrent(primary=None)
        tm = TrackerManager(t, _make_client())
        tm._tracker_tiers = []
        result = await tm.scrape_tracker(b"\x01" * 20)
        assert result is None

    @pytest.mark.asyncio
    async def test_scrape_tracker_exception(self):
        tm = TrackerManager(_make_torrent(), _make_client())
        with patch.object(tm, "_scrape_http", side_effect=Exception("network")):
            result = await tm.scrape_tracker(b"\x01" * 20)
        assert result is None

    def test_parse_scrape_response_valid(self):
        import bencodepy
        data = bencodepy.encode({
            b"files": {
                b"\x01" * 20: {
                    b"complete": 10,
                    b"incomplete": 5,
                    b"downloaded": 50,
                }
            }
        })
        result = TrackerManager._parse_scrape_response(data)
        assert result["seeders"] == 10

    def test_parse_scrape_response_invalid(self):
        result = TrackerManager._parse_scrape_response(b"not-bencoded")
        assert result is None
