"""
Logs API Endpoints
"""
from fastapi import APIRouter, Depends
from typing import Dict
from app.services.log_stream_service import log_handler
from app.core.auth import verify_token

router = APIRouter(dependencies=[Depends(verify_token)])


@router.get("/logs/recent")
async def get_recent_logs(count: int = 100) -> Dict:
    """Get recent logs"""
    logs = log_handler.get_recent_logs(count)
    return {
        "logs": logs,
        "count": len(logs)
    }
