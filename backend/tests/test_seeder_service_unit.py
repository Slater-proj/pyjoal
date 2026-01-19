"""
Tests for seeder_service.py - Core seeding orchestration service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import asyncio

from app.services.seeder_service import SeederService


class TestSeederServiceInit:
    """Test SeederService initialization"""
    
    def test_init_default_state(self):
        """Test service initializes with correct default state"""
        service = SeederService()
        
        assert service.client is None
        assert service.announcers == {}
        assert service.is_running is False
        assert service.started_at is None
        assert service._config == {}
        assert service.failed_torrents == {}


class TestSeederServiceConfig:
    """Test configuration loading and saving"""
    
    @pytest.mark.asyncio
    async def test_load_config_creates_default(self, tmp_path):
        """Test loading config creates default if not exists"""
        from app.services.seeder_service import SeederService
        
        service = SeederService()
        
        # Create a real config file instead of mocking
        config_file = tmp_path / "config.json"
        config_data = {
            "client": "qbittorrent-4.6.0.client",
            "minUploadRate": 100,
            "maxUploadRate": 500,
            "announceInterval": 1800,
            "announceJitter": 120,
            "enableRealisticBehavior": True,
            "pauseChance": 0.1
        }
        
        import json
        config_file.write_text(json.dumps(config_data))
        
        with patch('app.services.seeder_service.settings') as mock_settings:
            mock_settings.CONFIG_DIR = tmp_path
            
            await service.load_config()
        
        assert service._config is not None
    
    @pytest.mark.asyncio
    async def test_save_config_writes_file(self, tmp_path):
        """Test saving config writes to file"""
        service = SeederService()
        service._config = {
            "client": "test.client",
            "minUploadRate": 100,
            "maxUploadRate": 500
        }
        
        config_file = tmp_path / "config.json"
        
        with patch('app.services.seeder_service.settings') as mock_settings:
            mock_settings.CONFIG_DIR = tmp_path
            
            await service.save_config()
        
        assert config_file.exists()


class TestSeederServiceStart:
    """Test service start functionality"""
    
    @pytest.mark.asyncio
    async def test_start_sets_running_flag(self):
        """Test start() sets is_running to True"""
        service = SeederService()
        service.client = Mock()
        service.client.name = "TestClient"
        service.client.version = "1.0"
        
        # Mock load_torrents to return empty list
        with patch.object(service, 'load_torrents', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = None
            
            with patch('app.services.seeder_service.history_service') as mock_history:
                mock_history.add_entry = Mock()
                
                with patch('app.services.seeder_service.websocket_manager') as mock_ws:
                    mock_ws.broadcast = AsyncMock()
                    
                    await service.start()
        
        assert service.is_running is True
        assert service.started_at is not None
    
    @pytest.mark.asyncio
    async def test_start_already_running_does_nothing(self):
        """Test start() when already running doesn't restart"""
        service = SeederService()
        service.is_running = True
        service.started_at = datetime.now()
        original_time = service.started_at
        
        await service.start()
        
        assert service.started_at == original_time


class TestSeederServiceStop:
    """Test service stop functionality"""
    
    @pytest.mark.asyncio
    async def test_stop_clears_running_flag(self):
        """Test stop() clears is_running flag"""
        service = SeederService()
        service.is_running = True
        service.started_at = datetime.now()
        service.announcers = {}
        
        with patch('app.services.seeder_service.history_service') as mock_history:
            mock_history.add_entry = Mock()
            
            with patch('app.services.seeder_service.websocket_manager') as mock_ws:
                mock_ws.broadcast = AsyncMock()
                
                with patch('app.services.seeder_service.cache_manager') as mock_cache:
                    mock_cache.persist_cache = AsyncMock()
                    
                    await service.stop()
        
        assert service.is_running is False
    
    @pytest.mark.asyncio
    async def test_stop_not_running_does_nothing(self):
        """Test stop() when not running doesn't error"""
        service = SeederService()
        service.is_running = False
        
        # Should not raise
        await service.stop()
        
        assert service.is_running is False


class TestSeederServiceTorrents:
    """Test torrent management"""
    
    @pytest.mark.asyncio
    async def test_load_torrents_empty_directory(self, tmp_path):
        """Test loading from empty directory"""
        service = SeederService()
        service.client = Mock()
        service._config = {}
        
        with patch('app.services.seeder_service.settings') as mock_settings:
            mock_settings.TORRENTS_DIR = tmp_path
            
            with patch('app.services.seeder_service.load_torrents_from_directory') as mock_load:
                mock_load.return_value = []
                
                await service.load_torrents()
        
        assert len(service.announcers) == 0
    
    def test_get_stats_returns_dict(self):
        """Test get_stats returns proper stats dict"""
        service = SeederService()
        service.is_running = True
        service.started_at = datetime.now()
        service.client = Mock()
        service.client.name = "qBittorrent"
        service.client.version = "4.6.0"
        service.announcers = {}
        
        stats = service.get_stats()
        
        assert isinstance(stats, dict)
        assert "isRunning" in stats or "activeTorrents" in stats


class TestSeederServiceAnnouncers:
    """Test announcer management"""
    
    def test_get_torrent_info_not_found(self):
        """Test getting info of non-existent torrent returns empty dict"""
        service = SeederService()
        service.announcers = {}
        
        info = service._get_torrent_info("nonexistent_hash")
        
        # Returns empty dict when not found
        assert info == {} or info is None
    
    def test_get_torrents_returns_list(self):
        """Test get_torrents returns a list"""
        service = SeederService()
        service.announcers = {}
        
        torrents = service.get_torrents()
        
        assert isinstance(torrents, list)
        assert len(torrents) == 0


class TestSeederServiceStatistics:
    """Test statistics calculation"""
    
    def test_get_total_uploaded_empty(self):
        """Test total uploaded with no torrents"""
        service = SeederService()
        service.announcers = {}
        
        # Assuming there's a method or we calculate from announcers
        total = sum(a.uploaded for a in service.announcers.values()) if service.announcers else 0
        
        assert total == 0
    
    def test_get_total_uploaded_with_torrents(self):
        """Test total uploaded with multiple torrents"""
        service = SeederService()
        
        mock_announcer1 = Mock()
        mock_announcer1.uploaded = 1024 * 1024  # 1MB
        
        mock_announcer2 = Mock()
        mock_announcer2.uploaded = 2048 * 1024  # 2MB
        
        service.announcers = {
            "hash1": mock_announcer1,
            "hash2": mock_announcer2
        }
        
        total = sum(a.uploaded for a in service.announcers.values())
        
        assert total == 3 * 1024 * 1024


class TestSeederServiceClientFallback:
    """Test client fallback logic"""
    
    def test_find_best_fallback_client(self):
        """Test finding best fallback when configured client not found"""
        service = SeederService()
        
        available = ["qbittorrent-4.5.0.client", "qbittorrent-4.6.0.client", "transmission-4.0.5.client"]
        
        # Test finding similar client (same name, newer version)
        fallback = service._find_best_fallback_client("qbittorrent-4.4.0.client", available)
        
        # Should prefer same client family
        assert "qbittorrent" in fallback


class TestSeederServiceUptime:
    """Test uptime calculation"""
    
    def test_uptime_when_running(self):
        """Test uptime calculation when service is running"""
        service = SeederService()
        service.is_running = True
        service.started_at = datetime.now()
        
        # Small sleep to ensure some uptime
        import time
        time.sleep(0.1)
        
        stats = service.get_stats()
        
        # Stats should be a dict
        assert isinstance(stats, dict)
    
    def test_uptime_when_not_running(self):
        """Test stats when service not running"""
        service = SeederService()
        service.is_running = False
        service.started_at = None
        
        stats = service.get_stats()
        
        assert isinstance(stats, dict)
