"""
Torrents API Endpoints
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import List

from app.models.schemas import TorrentInfo, SuccessResponse
from app.services.seeder_service import seeder_service
from app.services.websocket_manager import websocket_manager
from app.core.torrent_parser import Torrent
from app.core.torrent_validator import validate_torrent_file
from app.core.config import settings
from app.core.auth import verify_token

router = APIRouter(dependencies=[Depends(verify_token)])


@router.get("/torrents", response_model=List[TorrentInfo])
async def get_torrents():
    """Get all torrents"""
    torrents = seeder_service.get_torrents()
    return torrents


@router.post("/torrents")
async def add_torrent(file: UploadFile = File(...)):
    """Add a new torrent with comprehensive validation"""
    if not file.filename.endswith('.torrent'):
        raise HTTPException(status_code=400, detail="File must be a .torrent file")
    
    torrent_path = settings.TORRENTS_DIR / file.filename
    
    try:
        # Read file content in memory first
        content = await file.read()
        
        # Comprehensive validation BEFORE saving to disk
        is_valid, validation_error = validate_torrent_file(torrent_path, content)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid torrent file: {validation_error}"
            )
        
        # Write to temporary location for final parsing
        temp_path = settings.TORRENTS_DIR / f"temp_{file.filename}"
        with open(temp_path, 'wb') as buffer:
            buffer.write(content)
        
        # Parse validated file
        try:
            torrent = Torrent(temp_path)
        except Exception as parse_error:
            # This should rarely happen after validation, but just in case
            temp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=500, 
                detail=f"Parsing failed after validation: {str(parse_error)}"
            )
        
        # Parsing succeeded, move to final location
        temp_path.rename(torrent_path)
        
        # Add to seeder service
        await seeder_service.add_torrent(torrent)
        
        return SuccessResponse(
            message="Torrent added successfully",
            data={"info_hash": torrent.info_hash, "name": torrent.name}
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Clean up file if it exists
        torrent_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/torrents/failed")
async def get_failed_torrents():
    """Get list of failed torrents for debugging"""
    failed_torrents = seeder_service.failed_torrents
    return {
        "failed_count": len(failed_torrents),
        "failed_torrents": [
            {
                "filename": info["filename"],
                "error": info["error"],
                "timestamp": info["timestamp"].isoformat(),
                "size": info["size"]
            }
            for info in failed_torrents.values()
        ]
    }


@router.delete("/torrents/{info_hash}")
async def remove_torrent(info_hash: str):
    """Remove a torrent"""
    try:
        await seeder_service.remove_torrent(info_hash)
        return SuccessResponse(message="Torrent removed successfully")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/torrents/{info_hash}")
async def get_torrent(info_hash: str):
    """Get specific torrent info"""
    torrent_info = seeder_service._get_torrent_info(info_hash)
    
    if not torrent_info:
        raise HTTPException(status_code=404, detail="Torrent not found")
    
    return torrent_info


@router.post("/torrents/{info_hash}/pause")
async def pause_torrent(info_hash: str):
    """Pause a specific torrent (stop announcing without archiving)"""
    try:
        await seeder_service.pause_torrent(info_hash)
        return SuccessResponse(message="Torrent paused")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/torrents/{info_hash}/resume")
async def resume_torrent(info_hash: str):
    """Resume a paused torrent"""
    try:
        await seeder_service.resume_torrent(info_hash)
        return SuccessResponse(message="Torrent resumed")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/torrents/reload")
async def reload_torrents():
    """Reload torrents from folder - detects added/removed torrent files"""
    try:
        # Verify service is ready
        if seeder_service is None:
            raise HTTPException(status_code=500, detail="Seeder service not initialized")
        
        # Save current state
        was_running = seeder_service.is_running
        old_count = len(seeder_service.announcers)
        old_hashes = set(seeder_service.announcers.keys())
        
        # Optimization: Only stop if running (required for file reload)
        if was_running:
            await seeder_service.stop()
        
        # Clear existing torrents to detect removed files
        seeder_service.announcers.clear()
        
        # Reload torrents from disk
        await seeder_service.load_torrents()
        new_count = len(seeder_service.announcers)
        new_hashes = set(seeder_service.announcers.keys())
        
        # Calculate changes
        added = len(new_hashes - old_hashes)
        removed = len(old_hashes - new_hashes)
        
        # Restart only if was running AND there are torrents to seed
        if was_running and new_count > 0:
            await seeder_service.start()
        
        # Notify WebSocket clients
        await websocket_manager.broadcast({
            "type": "torrents_update", 
            "data": {
                "torrents": seeder_service.get_torrents()
            }
        })
        
        # Build detailed message
        change_info = []
        if added > 0:
            change_info.append(f"+{added} added")
        if removed > 0:
            change_info.append(f"-{removed} removed")
        changes = f" ({', '.join(change_info)})" if change_info else ""
        
        return SuccessResponse(
            message=f"Torrents reloaded: {old_count} → {new_count}{changes}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reload error: {str(e)}")
