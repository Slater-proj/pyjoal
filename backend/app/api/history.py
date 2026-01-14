"""
History API Endpoints
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timedelta

from app.services.history_service import history_service, EventType

router = APIRouter()


@router.get("/history")
async def get_history(
    limit: int = Query(default=100, ge=1, le=1000),
    event_type: Optional[str] = None,
    hours: Optional[int] = Query(default=None, ge=1, le=168)  # Max 1 week
):
    """Get history entries"""
    # Parse event type
    event_type_enum = None
    if event_type:
        try:
            event_type_enum = EventType(event_type)
        except ValueError:
            pass
    
    # Calculate since timestamp
    since = None
    if hours:
        since = datetime.utcnow() - timedelta(hours=hours)
    
    entries = history_service.get_entries(
        limit=limit,
        event_type=event_type_enum,
        since=since
    )
    
    return {
        "entries": entries,
        "total": len(entries)
    }


@router.get("/history/stats")
async def get_history_stats(hours: int = Query(default=24, ge=1, le=168)):
    """Get statistics grouped by hour"""
    stats = history_service.get_stats_by_hour(hours=hours)
    return {
        "stats": stats,
        "hours": hours
    }


@router.get("/history/summary")
async def get_history_summary():
    """Get history summary"""
    return history_service.get_summary()


@router.delete("/history")
async def clear_history():
    """Clear all history"""
    history_service.clear()
    return {"success": True, "message": "History cleared"}


@router.get("/history/types")
async def get_event_types():
    """Get available event types"""
    return {
        "types": [e.value for e in EventType]
    }
