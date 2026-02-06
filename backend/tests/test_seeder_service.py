"""
Tests for seeder service
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import tempfile
from pathlib import Path
import os

from app.services.seeder_service import SeederService
from app.core.config import settings


@pytest.fixture
def seeder_service_instance():
    """Create a seeder service instance for testing (not initialized)"""
    with patch.object(SeederService, 'load_config', new_callable=AsyncMock):
        with patch.object(SeederService, 'load_torrents', new_callable=AsyncMock):
            service = SeederService()
            service.is_running = False
            service.started_at = None
            service.announcers = {}
            service.torrents = {}
            service.client = MagicMock()
            return service


@pytest.mark.asyncio
async def test_seeder_service_initialization():
    """Test seeder service can be initialized"""
    mock_client = MagicMock()
    
    with patch.object(SeederService, 'load_config', new_callable=AsyncMock):
        with patch.object(SeederService, 'load_torrents', new_callable=AsyncMock):
            with patch('app.core.bittorrent_client.list_available_clients') as mock_clients:
                mock_clients.return_value = ['qbittorrent-5.1.4.client']
                
                # Patch in the seeder_service namespace where it's imported
                with patch('app.services.seeder_service.BitTorrentClient') as mock_client_class:
                    mock_client_class.return_value = mock_client
                    
                    service = SeederService()
                    await service.initialize()
                    
                    assert not service.is_running
                    assert service.started_at is None
                    assert service.client == mock_client


@pytest.mark.asyncio
async def test_seeder_service_start_stop(seeder_service_instance):
    """Test starting and stopping seeder service"""
    service = seeder_service_instance
    
    # Test start
    await service.start()
    assert service.is_running
    assert service.started_at is not None
    
    # Test stop
    await service.stop()
    assert not service.is_running


@pytest.mark.asyncio
async def test_get_stats_initial(seeder_service_instance):
    """Test getting stats from fresh service"""
    service = seeder_service_instance
    stats = service.get_stats()
    
    assert stats['activeTorrents'] == 0
    assert stats['totalTorrents'] == 0
    assert not stats['isRunning']


@pytest.mark.asyncio
async def test_get_torrents_empty(seeder_service_instance):
    """Test getting torrents from empty service"""
    service = seeder_service_instance
    torrents = service.get_torrents()
    assert len(torrents) == 0


@pytest.mark.asyncio
async def test_remove_nonexistent_torrent(seeder_service_instance):
    """Test removing a torrent that doesn't exist"""
    service = seeder_service_instance
    # Should not raise an error
    await service.remove_torrent('fake_hash')


@pytest.mark.asyncio
async def test_seeder_service_concurrent_start():
    """Test that starting an already running service doesn't break"""
    mock_client = MagicMock()
    
    with patch.object(SeederService, 'load_config', new_callable=AsyncMock):
        with patch.object(SeederService, 'load_torrents', new_callable=AsyncMock):
            with patch('app.core.bittorrent_client.list_available_clients') as mock_clients:
                mock_clients.return_value = ['qbittorrent-5.1.4.client']
                
                # Patch in the seeder_service namespace where it's imported
                with patch('app.services.seeder_service.BitTorrentClient') as mock_client_class:
                    mock_client_class.return_value = mock_client
                    
                    service = SeederService()
                    await service.initialize()
                    
                    await service.start()
                    assert service.is_running
                    
                    # Starting again should be safe
                    await service.start()
                    assert service.is_running
                    
                    await service.stop()