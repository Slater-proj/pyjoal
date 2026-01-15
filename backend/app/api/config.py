"""
Configuration API Endpoints
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import ConfigSchema, SuccessResponse
from app.services.seeder_service import seeder_service
from app.core.bittorrent_client import list_available_clients

router = APIRouter()


@router.get("/config")
async def get_config():
    """Get current configuration"""
    config = seeder_service.get_config()
    return config


@router.put("/config")
async def update_config(config: ConfigSchema):
    """Update configuration"""
    try:
        config_dict = config.model_dump()
        await seeder_service.update_config(config_dict)
        
        return SuccessResponse(
            message="Configuration updated successfully",
            data=config_dict
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/clients")
async def get_available_clients():
    """Get list of available client files"""
    clients = list_available_clients()
    return {"clients": clients}


@router.post("/config/reset")
async def reset_config():
    """Reset configuration to default values from environment"""
    try:
        from app.core.config import settings
        
        default_config = {
            "minUploadRate": settings.MIN_UPLOAD_RATE,
            "maxUploadRate": settings.MAX_UPLOAD_RATE,
            "simultaneousSeed": settings.SIMULTANEOUS_SEED,
            "client": settings.DEFAULT_CLIENT,
            "keepTorrentWithZeroLeechers": settings.KEEP_TORRENT_WITH_ZERO_LEECHERS,
            "uploadRatioTarget": settings.UPLOAD_RATIO_TARGET,
            "seedingDurationLimit": settings.SEEDING_DURATION_LIMIT
        }
        
        await seeder_service.update_config(default_config)
        
        return SuccessResponse(
            message="Configuration reset to defaults",
            data=default_config
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

