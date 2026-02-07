"""
History Service
Tracks and stores history of announces, torrents, and system events.
Persists to disk so history survives container restarts.
"""
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from collections import deque
from enum import Enum
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events to track"""
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    TORRENT_ADDED = "torrent_added"
    TORRENT_REMOVED = "torrent_removed"
    TORRENT_LOAD_FAILED = "torrent_load_failed"
    TORRENT_ARCHIVED = "torrent_archived"  # Unified archived category
    ANNOUNCE_SUCCESS = "announce_success"
    ANNOUNCE_FAILED = "announce_failed"
    CONFIG_UPDATED = "config_updated"


class HistoryEntry:
    """Single history entry"""
    
    def __init__(self, event_type: EventType, message: str, data: Optional[Dict] = None):
        self.timestamp = datetime.now(timezone.utc)
        self.event_type = event_type
        self.message = message
        self.data = data or {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "eventType": self.event_type.value,
            "message": self.message,
            "data": self.data
        }


class HistoryService:
    """Service to manage history"""
    
    def __init__(self, max_entries: int = 1000):
        """Initialize history service"""
        self.max_entries = max_entries
        self.entries: deque = deque(maxlen=max_entries)
        self.stats_by_hour: Dict[str, Dict] = {}
        self._file_path: Path = settings.CONFIG_DIR / "history.json"
        self._dirty: bool = False
        self._save_counter: int = 0
        self._load()

    def _load(self):
        """Load persisted history from disk."""
        if not self._file_path.exists():
            return
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for raw in data.get("entries", []):
                entry = HistoryEntry(
                    EventType(raw["eventType"]),
                    raw["message"],
                    raw.get("data"),
                )
                entry.timestamp = datetime.fromisoformat(raw["timestamp"])
                self.entries.append(entry)
            self.stats_by_hour = data.get("stats_by_hour", {})
            logger.info(f"📂 Loaded {len(self.entries)} history entries from disk")
        except Exception as e:
            logger.error(f"❌ Failed to load history: {e}")

    def save(self):
        """Write current history to disk."""
        try:
            data = {
                "entries": [e.to_dict() for e in self.entries],
                "stats_by_hour": self.stats_by_hour,
            }
            tmp = self._file_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            tmp.replace(self._file_path)
            self._dirty = False
        except Exception as e:
            logger.error(f"❌ Failed to save history: {e}")
    
    def add_entry(self, event_type: EventType, message: str, data: Optional[Dict] = None):
        """Add an entry to history"""
        entry = HistoryEntry(event_type, message, data)
        self.entries.appendleft(entry)  # Most recent first
        
        # Update hourly stats
        hour_key = entry.timestamp.strftime("%Y-%m-%d %H:00")
        if hour_key not in self.stats_by_hour:
            self.stats_by_hour[hour_key] = {
                "announces": 0,
                "failed_announces": 0,
                "uploaded": 0
            }
        
        if event_type == EventType.ANNOUNCE_SUCCESS:
            self.stats_by_hour[hour_key]["announces"] += 1
            if data and "uploaded" in data:
                self.stats_by_hour[hour_key]["uploaded"] += data["uploaded"]
        elif event_type == EventType.ANNOUNCE_FAILED:
            self.stats_by_hour[hour_key]["failed_announces"] += 1

        # Auto-save every 10 entries
        self._save_counter += 1
        if self._save_counter >= 10:
            self._save_counter = 0
            self.save()
    
    def get_entries(
        self, 
        limit: int = 100, 
        event_type: Optional[EventType] = None,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """Get history entries"""
        entries = list(self.entries)
        
        # Filter by event type
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        
        # Filter by time
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        
        # Apply limit
        entries = entries[:limit]
        
        return [e.to_dict() for e in entries]
    
    def get_recent_entries(self, limit: int = 100) -> List[Dict]:
        """Get recent history entries (alias for get_entries)"""
        return self.get_entries(limit=limit)
    
    def get_entries_by_type(self, event_type: EventType, limit: int = 100) -> List[Dict]:
        """Get entries filtered by event type"""
        return self.get_entries(limit=limit, event_type=event_type)
    
    def get_entries_since(self, since: datetime, limit: int = 100) -> List[Dict]:
        """Get entries since a specific time"""
        return self.get_entries(limit=limit, since=since)
    
    def get_stats_by_hour(self, hours: int = 24) -> List[Dict]:
        """Get statistics grouped by hour"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        result = []
        for hour_key, stats in sorted(self.stats_by_hour.items(), reverse=True):
            hour_time = datetime.strptime(hour_key, "%Y-%m-%d %H:00")
            if hour_time >= cutoff:
                result.append({
                    "hour": hour_key,
                    **stats
                })
        
        return result
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        total_entries = len(self.entries)
        
        # Count by type
        counts_by_type = {}
        for entry in self.entries:
            event_type = entry.event_type.value
            counts_by_type[event_type] = counts_by_type.get(event_type, 0) + 1
        
        # Recent activity (last hour)
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent = [e for e in self.entries if e.timestamp >= one_hour_ago]
        
        return {
            "totalEntries": total_entries,
            "countsByType": counts_by_type,
            "recentActivity": len(recent),
            "oldestEntry": self.entries[-1].timestamp.isoformat() if self.entries else None,
            "newestEntry": self.entries[0].timestamp.isoformat() if self.entries else None
        }
    
    def clear(self):
        """Clear all history"""
        self.entries.clear()
        self.stats_by_hour.clear()
        self.save()


# Global history service instance
history_service = HistoryService()
