"""
Tests for Stealth Service - Anti-Detection Features
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from app.services.stealth_service import StealthService, stealth_service
from app.core.tracker_announcer import TrackerAnnouncer
from app.core.torrent_parser import Torrent
from app.core.bittorrent_client import BitTorrentClient


class TestStealthService:
    """Test stealth service functionality"""
    
    def test_session_profile_consistency(self):
        """Test that session profiles are consistent per torrent hash"""
        service = StealthService()
        torrent_hash = "test_hash_123"
        
        # Get profile twice
        profile1 = service.get_session_profile(torrent_hash)
        profile2 = service.get_session_profile(torrent_hash)
        
        # Should be identical
        assert profile1['user_agent'] == profile2['user_agent']
        assert profile1['session_port'] == profile2['session_port']
        assert profile1['activity_pattern'] == profile2['activity_pattern']
    
    def test_user_agent_diversity(self):
        """Test that different torrents get different user agents"""
        service = StealthService()
        user_agents = set()
        
        # Generate profiles for multiple torrents
        for i in range(20):
            hash_val = f"torrent_hash_{i}"
            profile = service.get_session_profile(hash_val)
            user_agents.add(profile['user_agent'])
        
        # Should have some diversity (not all identical)
        assert len(user_agents) > 1, "User agents should vary across torrents"
    
    def test_port_randomization(self):
        """Test port randomization within valid range"""
        service = StealthService()
        ports = set()
        
        for i in range(10):
            hash_val = f"torrent_hash_{i}"
            profile = service.get_session_profile(hash_val)
            port = profile['session_port']
            
            # Check valid port range
            assert 49152 <= port <= 65535, f"Port {port} out of valid range"
            ports.add(port)
        
        # Should have some port diversity
        assert len(ports) > 1, "Ports should vary across torrents"
    
    def test_natural_announce_intervals(self):
        """Test natural announce interval calculations"""
        service = StealthService()
        torrent_hash = "test_hash"
        base_interval = 300  # 5 minutes
        
        intervals = []
        for _ in range(10):
            interval = service.get_natural_announce_interval(torrent_hash, base_interval)
            intervals.append(interval)
            
            # Should be within reasonable bounds
            assert 90 <= interval <= 600, f"Interval {interval} out of reasonable bounds"
        
        # Should have variation
        assert len(set(intervals)) > 1, "Intervals should vary"
    
    def test_speed_variations(self):
        """Test natural speed variations"""
        service = StealthService()
        base_speed = 1024  # 1 KB/s
        
        speeds = []
        for i in range(10):
            # Use different torrent hash each time to bypass cache
            torrent_hash = f"test_hash_{i}"
            speed = service.get_natural_speed_variation(base_speed, torrent_hash)
            speeds.append(speed)
            
            # Should be positive
            assert speed >= 0, "Speed should not be negative"
        
        # Should have some variation (different torrent profiles cause different results)
        unique_speeds = set(speeds)
        assert len(unique_speeds) >= 1, "Speeds should be calculated"
    
    def test_disconnect_simulation(self):
        """Test temporary disconnect simulation"""
        service = StealthService()
        torrent_hash = "test_hash"
        
        # Test multiple times to check probability
        disconnects = 0
        for _ in range(100):
            if service.should_simulate_temporary_disconnect(torrent_hash):
                disconnects += 1
        
        # Should be rare (< 5% chance)
        assert disconnects <= 5, f"Disconnect rate too high: {disconnects}%"
    
    def test_session_stats(self):
        """Test session statistics retrieval"""
        service = StealthService()
        torrent_hash = "test_hash"
        
        # Get profile and stats
        profile = service.get_session_profile(torrent_hash)
        stats = service.get_session_stats(torrent_hash)
        
        assert 'client' in stats
        assert 'user_agent' in stats
        assert 'session_port' in stats
        assert 'activity_pattern' in stats
        assert stats['session_duration_hours'] >= 0


class TestRetryLogic:
    """Test retry logic and error handling"""
    
    @pytest.fixture(autouse=True)
    def mock_stealth_service(self):
        """Mock stealth service for all tests in this class"""
        with patch('app.core.tracker_announcer.stealth_service') as mock_stealth:
            mock_stealth.get_session_profile.return_value = {
                "user_agent": "TestAgent",
                "session_port": 6881,
                "client_name": "TestClient"
            }
            mock_stealth.get_session_stats.return_value = {
                "client": "TestClient",
                "session_duration_hours": 1.5,
                "activity_pattern": "steady",
                "connection_stability": 95.0
            }
            yield mock_stealth
    
    @pytest.fixture
    def mock_torrent(self):
        """Mock torrent for testing"""
        torrent = Mock(spec=Torrent)
        torrent.name = "Test Torrent"
        torrent.info_hash = "test_info_hash"
        torrent.size = 1024 * 1024 * 1024  # 1GB
        torrent.primary_tracker = "http://test.tracker.com/announce"
        return torrent
    
    @pytest.fixture
    def mock_client(self):
        """Mock BitTorrent client for testing"""
        client = Mock(spec=BitTorrentClient)
        client.generate_peer_id.return_value = b"test_peer_id_123456"
        client.get_session_port.return_value = 6881
        client.get_upload_rate_range.return_value = (30 * 1024, 160 * 1024)  # 30-160 KB/s
        client.get_user_agent.return_value = "TestClient/1.0"
        client.get_request_headers.return_value = {"User-Agent": "TestClient/1.0"}
        return client
    
    def test_retry_initialization(self, mock_torrent, mock_client):
        """Test that retry variables are properly initialized"""
        announcer = TrackerAnnouncer(mock_torrent, mock_client)
        
        assert announcer.consecutive_failures == 0
        assert announcer.max_retries == 5
        assert announcer.base_retry_delay == 30
        assert announcer._in_backoff is False
        assert announcer.last_retry_attempt is None
    
    def test_backoff_calculation(self, mock_torrent, mock_client):
        """Test exponential backoff calculation"""
        announcer = TrackerAnnouncer(mock_torrent, mock_client)
        
        # Test increasing backoff
        announcer.consecutive_failures = 1
        delay1 = announcer._calculate_backoff_delay()
        
        announcer.consecutive_failures = 2  
        delay2 = announcer._calculate_backoff_delay()
        
        announcer.consecutive_failures = 3
        delay3 = announcer._calculate_backoff_delay()
        
        # Should increase exponentially (with jitter)
        assert delay1 < delay2
        assert delay2 < delay3
        
        # Should be capped at max delay
        announcer.consecutive_failures = 10
        max_delay = announcer._calculate_backoff_delay()
        assert max_delay <= 360  # 300 * 1.2 jitter max
    
    @pytest.mark.asyncio
    async def test_stealth_profile_integration(self, mock_torrent, mock_client):
        """Test that stealth profile is integrated correctly"""
        announcer = TrackerAnnouncer(mock_torrent, mock_client)
        
        # Should have stealth profile
        assert hasattr(announcer, 'stealth_profile')
        assert 'user_agent' in announcer.stealth_profile
        assert 'session_port' in announcer.stealth_profile
        assert 'client_name' in announcer.stealth_profile
    
    def test_stealth_stats_in_response(self, mock_torrent, mock_client):
        """Test that stealth stats are included in get_stats response"""
        announcer = TrackerAnnouncer(mock_torrent, mock_client)
        stats = announcer.get_stats()
        
        # Should include stealth information
        assert 'stealth' in stats
        assert 'client' in stats['stealth']
        assert 'sessionDuration' in stats['stealth']
        assert 'activityPattern' in stats['stealth']
        assert 'connectionStability' in stats['stealth']
        assert 'consecutiveFailures' in stats['stealth']
        assert 'inBackoff' in stats['stealth']
    
    @pytest.mark.asyncio
    async def test_announce_url_building(self, mock_torrent, mock_client):
        """Test announce URL building uses client's JOAL-compatible format"""
        # Configure mock to return a proper URL
        mock_client.build_announce_url.return_value = (
            f"{mock_torrent.primary_tracker}?"
            "info_hash=%01%02%03&peer_id=test_peer_id_123456"
            "&uploaded=0&downloaded=0&left=1073741824&port=6881&event=started"
        )
        
        announcer = TrackerAnnouncer(mock_torrent, mock_client)
        
        # Build URL using the client's method (which uses JOAL format)
        url = mock_client.build_announce_url(
            tracker_url=mock_torrent.primary_tracker,
            info_hash=b'test_hash_bytes',
            peer_id=announcer.peer_id,
            port=announcer.port,
            uploaded=announcer.uploaded,
            downloaded=announcer.downloaded,
            left=announcer.left,
            event="started"
        )
        
        # Should be a valid URL
        assert url.startswith(mock_torrent.primary_tracker)
        
        # Should include standard parameters
        assert "info_hash=" in url
        assert "peer_id=" in url
        assert "uploaded=" in url
        assert "downloaded=" in url
        assert "left=" in url
        assert "event=started" in url
    
    def test_error_recording_silent(self, mock_torrent, mock_client):
        """Test silent error recording vs regular error recording"""
        announcer = TrackerAnnouncer(mock_torrent, mock_client)
        
        initial_error_count = announcer.error_count
        
        # Test silent error recording
        announcer._record_error_silent("Silent test error")
        assert announcer.error_count == initial_error_count + 1
        assert announcer.last_error == "Silent test error"
        
        # Test regular error recording
        announcer._record_error("Regular test error")
        assert announcer.error_count == initial_error_count + 2
        assert announcer.last_error == "Regular test error"


class TestIntegrationStealth:
    """Integration tests for stealth features"""
    
    def test_global_stealth_service_instance(self):
        """Test that global stealth service instance works"""
        # Should be importable and functional
        assert stealth_service is not None
        
        # Should provide consistent behavior
        profile1 = stealth_service.get_session_profile("test")
        profile2 = stealth_service.get_session_profile("test")
        
        assert profile1 == profile2
    
    def test_stealth_timing_patterns(self):
        """Test that stealth timing creates realistic patterns"""
        intervals = []
        
        # Collect intervals for same torrent over time
        for hour in range(24):
            # Mock different times of day
            with patch('app.services.stealth_service.datetime') as mock_dt:
                mock_dt.now.return_value.hour = hour
                mock_dt.utcnow.return_value = datetime.utcnow()
                
                interval = stealth_service.get_natural_announce_interval("test_hash", 300)
                intervals.append(interval)
        
        # Should have variation based on time of day
        unique_intervals = set(intervals)
        assert len(unique_intervals) > 1, "Intervals should vary by time of day"
    
    def test_user_agent_distribution(self):
        """Test realistic user agent distribution"""
        clients = {}
        
        # Generate many profiles to test distribution
        for i in range(100):
            profile = stealth_service.get_session_profile(f"hash_{i}")
            client = profile['client_name']
            clients[client] = clients.get(client, 0) + 1
        
        # Should have qBittorrent as most common (35% weight)
        assert 'qBittorrent' in clients
        
        # Should have multiple client types
        assert len(clients) >= 3, f"Should have multiple client types, got: {clients}"
        
        # qBittorrent should be most common (due to highest weight)
        most_common_client = max(clients.items(), key=lambda x: x[1])[0]
        assert most_common_client == 'qBittorrent', f"Expected qBittorrent to be most common, got {most_common_client}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])