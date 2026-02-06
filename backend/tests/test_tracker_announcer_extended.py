"""
Extended tests for TrackerAnnouncer - announce lifecycle, retry logic, stats delegation
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from app.core.tracker_announcer import TrackerAnnouncer


def _mock_torrent(name="Test", size=100*1024*1024, info_hash="abc123"):
    t = Mock()
    t.name = name
    t.size = size
    t.info_hash = info_hash
    t.info_hash_bytes = b'\xab\xc1\x23' + b'\x00' * 17
    t.primary_tracker = "http://tracker.example.com/announce"
    t.announce_list = [[t.primary_tracker]]
    return t


def _mock_client():
    c = Mock()
    c.generate_peer_id = Mock(return_value=b'-qB5140-xxxxxxxxxxxx')
    c.get_session_port = Mock(return_value=6881)
    c.get_upload_rate_range = Mock(return_value=(10240, 102400))
    c.get_download_rate_range = Mock(return_value=(102400, 1048576))
    c.name = "qBittorrent"
    c.version = "5.1.4"
    c.build_announce_url = Mock(return_value="http://tracker.example.com/announce?info_hash=abc")
    c.get_request_headers = Mock(return_value={"User-Agent": "qBittorrent/5.1.4"})
    c.generate_key = Mock(return_value="deadbeef")
    return c


@pytest.fixture
def announcer():
    with patch("app.core.tracker_announcer.stealth_service") as mock_stealth:
        mock_stealth.get_session_profile.return_value = {
            'user_agent': 'qBittorrent/5.1.4',
            'client_name': 'qBittorrent',
            'session_port': 50000,
            'announce_variance': 0.2,
            'activity_pattern': 'steady',
            'session_start': datetime.now(timezone.utc),
            'connection_stability': 0.95,
        }
        mock_stealth.get_natural_announce_interval.return_value = 1800
        a = TrackerAnnouncer(_mock_torrent(), _mock_client())
        yield a


class TestAnnouncerInit:
    def test_default_state(self, announcer):
        assert announcer.is_running is False
        assert announcer.uploaded == 0
        assert announcer.error_count == 0
        assert announcer.consecutive_failures == 0

    def test_properties_delegate_to_stats(self, announcer):
        announcer.uploaded = 1000
        assert announcer.stats.uploaded == 1000

    def test_custom_discretion_config(self):
        with patch("app.core.tracker_announcer.stealth_service") as mock_stealth:
            mock_stealth.get_session_profile.return_value = {
                'user_agent': 'test', 'client_name': 'test',
                'session_port': 50000, 'announce_variance': 0.2,
                'activity_pattern': 'steady',
                'session_start': datetime.now(timezone.utc),
                'connection_stability': 0.95,
            }
            config = {"announce_interval": 600, "announce_jitter": 10}
            a = TrackerAnnouncer(_mock_torrent(), _mock_client(), config)
            assert a.announce_interval == 600
            assert a.announce_jitter == 10


class TestAnnouncerLifecycle:
    @pytest.mark.asyncio
    async def test_start_sets_running(self, announcer):
        with patch.object(announcer, '_send_announce_stealth', new_callable=AsyncMock):
            with patch("app.services.seeder_service.seeder_service") as mock_ss:
                mock_ss._config = {}
                await announcer.start()
                assert announcer.is_running is True

                # Cleanup
                announcer.is_running = False
                if announcer._announce_task:
                    announcer._announce_task.cancel()
                    try:
                        await announcer._announce_task
                    except asyncio.CancelledError:
                        pass

    @pytest.mark.asyncio
    async def test_stop_sends_stopped_event(self, announcer):
        """C3 fix: stop should use _send_announce_stealth, not _send_announce"""
        announcer.is_running = True
        announcer._announce_task = None
        announcer._seeding_started_at = datetime.now(timezone.utc)

        with patch.object(announcer, '_send_announce_stealth', new_callable=AsyncMock) as mock_stealth:
            await announcer.stop()
            mock_stealth.assert_called_once_with(event="stopped")
            assert announcer.is_running is False

    @pytest.mark.asyncio
    async def test_start_already_running(self, announcer):
        announcer.is_running = True
        await announcer.start()  # Should be a no-op

    @pytest.mark.asyncio
    async def test_stop_already_stopped(self, announcer):
        announcer.is_running = False
        await announcer.stop()  # Should be a no-op


class TestStatsDelegation:
    def test_update_stats_for_display(self, announcer):
        announcer.is_running = True
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss._config = {}
            announcer._update_stats_for_display()

    def test_update_stats_with_stealth(self, announcer):
        announcer.is_running = True
        with patch("app.core.tracker_announcer.stealth_service") as mock_stealth:
            mock_stealth.get_natural_speed_variation.return_value = 50000
            with patch("app.services.seeder_service.seeder_service") as mock_ss:
                mock_ss._config = {}
                announcer._update_stats_with_stealth()

    def test_get_activity_based_speed(self, announcer):
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss._config = {}
            speed = announcer._get_activity_based_upload_speed()
            assert isinstance(speed, int)


class TestRetryLogic:
    def test_calculate_backoff_delay(self, announcer):
        announcer.consecutive_failures = 3
        delay = announcer._calculate_backoff_delay()
        assert isinstance(delay, (int, float))
        assert delay > 0

    @pytest.mark.asyncio
    async def test_send_announce_with_retry_success(self, announcer):
        with patch.object(announcer, '_send_announce_stealth', new_callable=AsyncMock):
            await announcer._send_announce_with_retry()
            assert announcer.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_send_announce_with_retry_all_fail(self, announcer):
        announcer.max_retries = 1

        with patch.object(announcer, '_send_announce_stealth', new_callable=AsyncMock,
                          side_effect=Exception("fail")):
            await announcer._send_announce_with_retry()
            assert announcer.consecutive_failures > 0


class TestErrorTracking:
    def test_record_error(self, announcer):
        announcer._record_error("Test error")
        assert announcer.last_error == "Test error"
        assert announcer.error_count == 1


class TestTrackerDelegation:
    def test_get_next_tracker(self, announcer):
        tracker = announcer._get_next_tracker()
        assert tracker is not None

    def test_mark_tracker_success(self, announcer):
        url = "http://tracker.example.com/announce"
        announcer._mark_tracker_success(url)

    def test_mark_tracker_failure(self, announcer):
        url = "http://tracker.example.com/announce"
        announcer._mark_tracker_failure(url)
