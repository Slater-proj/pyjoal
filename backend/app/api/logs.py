"""
Logs API Endpoints
"""
from fastapi import APIRouter
from typing import Dict
from app.services.log_stream_service import log_handler

router = APIRouter()


@router.get("/logs/recent")
async def get_recent_logs(count: int = 100) -> Dict:
    """Get recent logs"""
    logs = log_handler.get_recent_logs(count)
    return {
        "logs": logs,
        "count": len(logs)
    }
