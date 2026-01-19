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
    
    with patch('app.core.tracker_announcer.stealth_service') as mock_stealth:
        mock_stealth.get_session_profile.return_value = {
            "user_agent": "TestAgent",
            "session_port": 6881,
            "client_name": "TestClient"
        }
        
        announcer = TrackerAnnouncer(mock_torrent, mock_client, discretion_config)
        
        assert announcer.announce_interval == 45
        assert announcer.announce_jitter == 15
        assert announcer.min_stats_update_interval == 5
        assert announcer.enable_speed_variation == True
        assert announcer.speed_variation_percent == 25


def test_tracker_announcer_default_discretion_config(mock_torrent, mock_client):
    """Test that TrackerAnnouncer uses defaults when no discretion config provided"""
    with patch('app.core.tracker_announcer.stealth_service') as mock_stealth:
        mock_stealth.get_session_profile.return_value = {
            "user_agent": "TestAgent",
            "session_port": 6881,
            "client_name": "TestClient"
        }
        
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
    
    with patch('app.core.tracker_announcer.stealth_service') as mock_stealth:
        mock_stealth.get_session_profile.return_value = {
            "user_agent": "TestAgent",
            "session_port": 6881,
            "client_name": "TestClient"
        }
        
        announcer = TrackerAnnouncer(mock_torrent, mock_client, discretion_config)
        
        # Verify the configuration was applied
        assert announcer.enable_speed_variation == False
        assert announcer.speed_variation_percent == 0


def test_min_stats_update_interval_enforcement(mock_torrent, mock_client):
    """Test that minimum stats update interval is correctly configured"""
    discretion_config = {
        "min_stats_update_interval": 5
    }
    
    with patch('app.core.tracker_announcer.stealth_service') as mock_stealth:
        mock_stealth.get_session_profile.return_value = {
            "user_agent": "TestAgent",
            "session_port": 6881,
            "client_name": "TestClient"
        }
        
        announcer = TrackerAnnouncer(mock_torrent, mock_client, discretion_config)
        
        # Verify the configuration was applied
        assert announcer.min_stats_update_interval == 5


if __name__ == "__main__":
    pytest.main([__file__])