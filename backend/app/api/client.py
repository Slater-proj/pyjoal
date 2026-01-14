"""
Client Control API Endpoints
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import ClientStats, SuccessResponse
from app.services.seeder_service import seeder_service

router = APIRouter()


@router.post("/start")
async def start_seeding():
    """Start seeding torrents"""
    try:
        await seeder_service.start()
        return SuccessResponse(message="Seeding started")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop")
async def stop_seeding():
    """Stop seeding torrents"""
    try:
        await seeder_service.stop()
        return SuccessResponse(message="Seeding stopped")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats", response_model=ClientStats)
async def get_stats():
    """Get client statistics"""
    return seeder_service.get_stats()


@router.get("/status")
async def get_status():
    """Get current status"""
    stats = seeder_service.get_stats()
    return {
        "isRunning": stats["isRunning"],
        "activeTorrents": stats["activeTorrents"],
        "totalTorrents": stats["totalTorrents"]
    }
