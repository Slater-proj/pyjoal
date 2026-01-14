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
