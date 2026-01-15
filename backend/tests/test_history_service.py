"""
Tests for history service
"""
import pytest
from datetime import datetime, timedelta

from app.services.history_service import HistoryService, EventType


@pytest.fixture
def history_service():
    """Create fresh history service for each test"""
    return HistoryService()


def test_add_entry(history_service):
    """Test adding history entry"""
    history_service.add_entry(
        EventType.TORRENT_ADDED,
        "Test torrent added",
        {"torrent_name": "test.torrent"}
    )
    
    entries = history_service.get_recent_entries()
    assert len(entries) == 1
    assert entries[0]["event_type"] == EventType.TORRENT_ADDED
    assert entries[0]["message"] == "Test torrent added"
    assert entries[0]["data"]["torrent_name"] == "test.torrent"


def test_get_recent_entries_limit(history_service):
    """Test getting limited number of entries"""
    # Add multiple entries
    for i in range(10):
        history_service.add_entry(
            EventType.TORRENT_ADDED,
            f"Torrent {i}",
            {"index": i}
        )
    
    # Get only 5 recent entries
    entries = history_service.get_recent_entries(limit=5)
    assert len(entries) == 5
    
    # Should be most recent first
    assert entries[0]["data"]["index"] == 9
    assert entries[4]["data"]["index"] == 5


def test_get_entries_by_type(history_service):
    """Test filtering entries by event type"""
    history_service.add_entry(EventType.TORRENT_ADDED, "Added", {})
    history_service.add_entry(EventType.TORRENT_REMOVED, "Removed", {})
    history_service.add_entry(EventType.TORRENT_ADDED, "Added again", {})
    
    added_entries = history_service.get_entries_by_type(EventType.TORRENT_ADDED)
    assert len(added_entries) == 2
    
    removed_entries = history_service.get_entries_by_type(EventType.TORRENT_REMOVED)
    assert len(removed_entries) == 1


def test_get_entries_since(history_service):
    """Test getting entries since a specific time"""
    now = datetime.utcnow()
    
    # Add entry before cutoff
    history_service.add_entry(EventType.TORRENT_ADDED, "Old entry", {})
    
    # Wait a bit and add recent entry
    cutoff = now + timedelta(seconds=1)
    
    # Simulate time passing
    import time
    time.sleep(0.1)
    
    history_service.add_entry(EventType.TORRENT_ADDED, "New entry", {})
    
    recent_entries = history_service.get_entries_since(cutoff)
    assert len(recent_entries) == 1
    assert recent_entries[0]["message"] == "New entry"


def test_clear_old_entries(history_service):
    """Test clearing old entries"""
    # Add many entries
    for i in range(150):
        history_service.add_entry(
            EventType.TORRENT_ADDED,
            f"Entry {i}",
            {"index": i}
        )
    
    # Should have been trimmed to max_entries
    entries = history_service.get_recent_entries(limit=200)
    assert len(entries) <= 100  # Default max_entries


def test_entry_timestamp_format(history_service):
    """Test that timestamps are in correct format"""
    history_service.add_entry(EventType.TORRENT_ADDED, "Test", {})
    
    entries = history_service.get_recent_entries()
    timestamp = entries[0]["timestamp"]
    
    # Should be ISO format datetime string
    assert isinstance(timestamp, str)
    # Should be parseable back to datetime
    parsed = datetime.fromisoformat(timestamp)
    assert isinstance(parsed, datetime)