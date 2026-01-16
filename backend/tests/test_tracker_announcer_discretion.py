"""
Tests for TrackerAnnouncer discretion features
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from pathlib import Path

from app.core.tracker_announcer import TrackerAnnouncer
from app.core.bittorrent_client import BitTorrentClient
from app.core.torrent_parser import Torrent


@pytest.fixture
def mock_torrent():
    """Create a mock torrent for testing"""
    torrent = Mock(spec=Torrent)
    torrent.info_hash = "test_hash_123"
    torrent.name = "Test Torrent"
    torrent.size = 1024 * 1024 * 1024  # 1GB
    torrent.primary_tracker = "http://tracker.test/announce"
    torrent.path = Path("/test/torrent.torrent")
    return torrent


@pytest.fixture
def mock_client():
    """Create a mock BitTorrent client"""
    client = Mock(spec=BitTorrentClient)
    client.name = "qBittorrent"
    client.version = "4.6.0"
    client.generate_peer_id.return_value = "test_peer_id"
    client.get_upload_rate_range.return_value = (30 * 1024, 160 * 1024)  # 30-160 KB/s
    client.get_user_agent.return_value = "qBittorrent/4.6.0"
    client.get_request_headers.return_value = {"User-Agent": "qBittorrent/4.6.0"}
    return client


def test_tracker_announcer_discretion_config(mock_torrent, mock_client):
    """Test that TrackerAnnouncer accepts and applies discretion configuration"""
    discretion_config = {
        "announce_interval": 45,
        "announce_jitter": 15,
        "min_stats_update_interval": 5,
        "enable_speed_variation": True,
        "speed_variation_percent": 25
    }
    
    announcer = TrackerAnnouncer(mock_torrent, mock_client, discretion_config)
    
    assert announcer.announce_interval == 45
    assert announcer.announce_jitter == 15
    assert announcer.min_stats_update_interval == 5
    assert announcer.enable_speed_variation == True
    assert announcer.speed_variation_percent == 25


def test_tracker_announcer_default_discretion_config(mock_torrent, mock_client):
    """Test that TrackerAnnouncer uses defaults when no discretion config provided"""
    announcer = TrackerAnnouncer(mock_torrent, mock_client)
    
    # Should use settings defaults (check that attributes exist)
    assert hasattr(announcer, 'announce_interval')
    assert hasattr(announcer, 'announce_jitter')
    assert hasattr(announcer, 'min_stats_update_interval')
    assert hasattr(announcer, 'enable_speed_variation')
    assert hasattr(announcer, 'speed_variation_percent')


def test_speed_variation_disabled(mock_torrent, mock_client):
    """Test that speed variation can be disabled"""
    discretion_config = {
        "enable_speed_variation": False,
        "speed_variation_percent": 0
    }
    
    announcer = TrackerAnnouncer(mock_torrent, mock_client, discretion_config)
    announcer.is_running = True
    
    # Mock the time functions
    import time
    original_time = time.time
    time_value = 1000.0
    
    def mock_time():
        nonlocal time_value
        time_value += 10  # Advance time by 10 seconds each call
        return time_value
    
    with patch('time.time', side_effect=mock_time):
        # Update stats multiple times and verify speed doesn't vary much
        speeds = []
        for _ in range(5):
            announcer._update_stats()
            speeds.append(announcer.upload_speed)
        
        # With variation disabled, speeds should be within the base range
        # (still some variation due to random.randint, but no additional variation)
        min_rate, max_rate = mock_client.get_upload_rate_range()
        for speed in speeds:
            assert min_rate <= speed <= max_rate


def test_min_stats_update_interval_enforcement(mock_torrent, mock_client):
    """Test that minimum stats update interval is enforced"""
    discretion_config = {
        "min_stats_update_interval": 5
    }
    
    announcer = TrackerAnnouncer(mock_torrent, mock_client, discretion_config)
    announcer.is_running = True
    
    import time
    original_time = time.time
    current_time = 1000.0
    
    def mock_time():
        return current_time
    
    with patch('time.time', side_effect=mock_time):
        # First update should work
        initial_uploaded = announcer.uploaded
        announcer._update_stats()
        first_update_uploaded = announcer.uploaded
        
        # Immediate second update should be ignored (time hasn't advanced)
        announcer._update_stats()
        second_update_uploaded = announcer.uploaded
        
        assert first_update_uploaded > initial_uploaded
        assert second_update_uploaded == first_update_uploaded  # No change
        
        # Advance time and try again
        current_time += 10
        announcer._update_stats()
        third_update_uploaded = announcer.uploaded
        
        assert third_update_uploaded > second_update_uploaded


if __name__ == "__main__":
    pytest.main([__file__])