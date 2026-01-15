"""
Tests for seeder service
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import tempfile
from pathlib import Path

from app.services.seeder_service import SeederService
from app.core.config import settings


@pytest.fixture
async def seeder_service():
    """Create a seeder service instance for testing"""
    service = SeederService()
    await service.initialize()
    return service


@pytest.mark.asyncio
async def test_seeder_service_initialization():
    """Test seeder service can be initialized"""
    service = SeederService()
    await service.initialize()
    
    assert not service.is_running
    assert service.started_at is None
    assert len(service.announcers) == 0


@pytest.mark.asyncio
async def test_seeder_service_start_stop(seeder_service):
    """Test starting and stopping seeder service"""
    # Test start
    await seeder_service.start()
    assert seeder_service.is_running
    assert seeder_service.started_at is not None
    
    # Test stop
    await seeder_service.stop()
    assert not seeder_service.is_running


@pytest.mark.asyncio
async def test_get_stats_initial(seeder_service):
    """Test getting stats from fresh service"""
    stats = seeder_service.get_stats()
    
    assert stats['activeTorrents'] == 0
    assert stats['totalTorrents'] == 0
    assert stats['uploadSpeed'] == 0
    assert not stats['isRunning']


@pytest.mark.asyncio
async def test_get_torrents_empty(seeder_service):
    """Test getting torrents from empty service"""
    torrents = seeder_service.get_torrents()
    assert len(torrents) == 0


@pytest.mark.asyncio
async def test_remove_nonexistent_torrent(seeder_service):
    """Test removing a torrent that doesn't exist"""
    # Should not raise an error
    await seeder_service.remove_torrent('fake_hash')


@pytest.mark.asyncio
async def test_seeder_service_concurrent_start():
    """Test that starting an already running service doesn't break"""
    service = SeederService()
    await service.initialize()
    
    await service.start()
    assert service.is_running
    
    # Starting again should be safe
    await service.start()
    assert service.is_running
    
    await service.stop()