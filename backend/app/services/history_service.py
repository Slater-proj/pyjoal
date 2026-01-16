"""
History Service
Tracks and stores history of announces, torrents, and system events
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import deque
from enum import Enum


class EventType(str, Enum):
    """Types of events to track"""
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    TORRENT_ADDED = "torrent_added"
    TORRENT_REMOVED = "torrent_removed"
    TORRENT_LOAD_FAILED = "torrent_load_failed"
    TORRENT_ARCHIVED_RATIO = "torrent_archived_ratio"
    TORRENT_ARCHIVED_TIME = "torrent_archived_time"
    TORRENT_ARCHIVED_ERROR = "torrent_archived_error"
    ANNOUNCE_SUCCESS = "announce_success"
    ANNOUNCE_FAILED = "announce_failed"
    CONFIG_UPDATED = "config_updated"


class HistoryEntry:
    """Single history entry"""
    
    def __init__(self, event_type: EventType, message: str, data: Optional[Dict] = None):
        self.timestamp = datetime.utcnow()
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
    
    def get_stats_by_hour(self, hours: int = 24) -> List[Dict]:
        """Get statistics grouped by hour"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
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
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
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


# Global history service instance
history_service = HistoryService()
