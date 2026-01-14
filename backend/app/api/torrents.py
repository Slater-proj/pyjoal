"""
Torrents API Endpoints
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
from pathlib import Path
import shutil

from app.models.schemas import TorrentInfo, SuccessResponse
from app.services.seeder_service import seeder_service
from app.core.torrent_parser import Torrent
from app.core.config import settings

router = APIRouter()


@router.get("/torrents", response_model=List[TorrentInfo])
async def get_torrents():
    """Get all torrents"""
    torrents = seeder_service.get_torrents()
    return torrents


@router.post("/torrents")
async def add_torrent(file: UploadFile = File(...)):
    """Add a new torrent"""
    if not file.filename.endswith('.torrent'):
        raise HTTPException(status_code=400, detail="File must be a .torrent file")
    
    torrent_path = settings.TORRENTS_DIR / file.filename
    
    try:
        # Read file content in memory first
        content = await file.read()
        
        # Try to parse BEFORE saving to disk
        # Write to temporary location first
        temp_path = settings.TORRENTS_DIR / f"temp_{file.filename}"
        with open(temp_path, 'wb') as buffer:
            buffer.write(content)
        
        # Parse and validate
        try:
            torrent = Torrent(temp_path)
        except Exception as parse_error:
            # Parsing failed, remove temp file and raise error
            temp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid torrent file: {str(parse_error)}"
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
